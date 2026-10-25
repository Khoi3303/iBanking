import uuid
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models import Transaction, OtpToken
from app.redis_client import (
    generate_unique_otp,
    verify_otp,
    consume_otp,
    invalidate_otp,
    hash_otp,
    acquire_distributed_lock,
    release_distributed_lock
)
from app.clients import UserServiceClient, TuitionServiceClient, NotificationServiceClient


async def initiate_payment_saga(
    db: AsyncSession,
    user_id: int,
    username: str,
    user_email: str,
    student_code: str,
    amount: Decimal,
    invoice_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> dict:
    """
    Khởi tạo giao dịch đóng học phí (Bước 1):
    1. Kiểm tra tính hợp lệ của Idempotency-Key (nếu có, replay phiên đang PENDING_OTP/SUCCESS).
    2. Kiểm tra tính hợp lệ của khoản nợ học phí từ Tuition Service.
    3. Kiểm tra số dư tài khoản từ User Service (phải >= amount).
    4. Hủy bỏ các phiên giao dịch PENDING_OTP cũ của user này (nếu khởi tạo phiên mới).
    5. Tạo Transaction mới ở trạng thái PENDING_OTP.
    6. Sinh mã OTP ngẫu nhiên 6 số, TTL 300s, không trùng lặp (Redis + DB Audit).
    7. Gửi email mã OTP qua Notification Service.
    """
    # 0. Kiểm tra Idempotency-Key và chiếm khóa phân tán chống Race Condition
    lock_idemp_key = f"lock:idemp:{user_id}:{idempotency_key}" if idempotency_key else None
    lock_token = str(uuid.uuid4()) if idempotency_key else None

    if lock_idemp_key:
        for _ in range(25):
            if await acquire_distributed_lock(lock_idemp_key, lock_token, ttl_seconds=10):
                break
            await asyncio.sleep(0.05)

    try:
        if idempotency_key:
            stmt_idemp = select(Transaction).where(
                and_(Transaction.user_id == user_id, Transaction.idempotency_key == idempotency_key)
            )
            res_idemp = await db.execute(stmt_idemp)
            existing_tx = res_idemp.scalar_one_or_none()
            if existing_tx:
                if existing_tx.status == "PENDING_OTP":
                    return {
                        "transaction_id": existing_tx.id,
                        "status": existing_tx.status,
                        "student_code": existing_tx.student_code,
                        "student_name": existing_tx.student_name,
                        "semester": existing_tx.semester,
                        "amount": existing_tx.amount,
                        "expires_in_seconds": 300,
                        "user_email": existing_tx.user_email,
                        "message": f"Mã OTP đã được gửi đến email {existing_tx.user_email}. (Yêu cầu trùng lặp Idempotent)"
                    }
                elif existing_tx.status in ["PROCESSING", "SUCCESS"]:
                    return {
                        "transaction_id": existing_tx.id,
                        "status": existing_tx.status,
                        "student_code": existing_tx.student_code,
                        "student_name": existing_tx.student_name,
                        "semester": existing_tx.semester,
                        "amount": existing_tx.amount,
                        "expires_in_seconds": 0,
                        "user_email": existing_tx.user_email,
                        "message": "Giao dịch đã được ghi nhận và xử lý trước đó."
                    }

        # 1. Tra cứu học phí phía TDTU
        tuition_info = await TuitionServiceClient.get_student_tuition(student_code, correlation_id=correlation_id)
        if not tuition_info.get("can_pay"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=tuition_info.get("message", "Khoản học phí này không đủ điều kiện thanh toán.")
            )

        tuition_amount = Decimal(str(tuition_info.get("amount", 0)))
        if tuition_amount != amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số tiền yêu cầu thanh toán ({amount:,.0f} VNĐ) không khớp với học phí thực tế ({tuition_amount:,.0f} VNĐ)."
            )

        # 2. Kiểm tra số dư tài khoản người nộp tiền
        user_info = await UserServiceClient.get_user(user_id, correlation_id=correlation_id)
        user_balance = Decimal(str(user_info.get("balance", 0)))
        if user_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số dư khả dụng ({user_balance:,.0f} VNĐ) không đủ để thanh toán ({amount:,.0f} VNĐ)."
            )

        # 3. Dọn dẹp các phiên PENDING_OTP cũ của user (xử lý case người dùng tắt đi bật lại)
        stmt_old_pending = select(Transaction).where(
            and_(Transaction.user_id == user_id, Transaction.status == "PENDING_OTP")
        )
        old_res = await db.execute(stmt_old_pending)
        old_txs = old_res.scalars().all()
        for old_tx in old_txs:
            old_tx.status = "CANCELLED"
            old_tx.failure_reason = "Người dùng khởi tạo phiên giao dịch mới"
            await invalidate_otp(old_tx.id)

        # 4. Tạo giao dịch mới
        tx_id = str(uuid.uuid4())
        resolved_invoice_id = invoice_id or tuition_info.get("invoice_id")

        new_tx = Transaction(
            id=tx_id,
            user_id=user_id,
            username=username,
            user_email=user_email,
            student_code=student_code,
            student_name=tuition_info.get("student_name", ""),
            invoice_id=resolved_invoice_id,
            semester=tuition_info.get("semester", ""),
            amount=amount,
            idempotency_key=idempotency_key,
            status="PENDING_OTP"
        )
        db.add(new_tx)

        # 5. Sinh mã OTP bằng CSPRNG (Redis lưu hash SHA-256 có TTL 300s)
        otp_code = await generate_unique_otp(transaction_id=tx_id, length=6, expire_seconds=300)

        # Lưu Audit log trong DB (Lưu hash SHA-256, không lưu plaintext)
        otp_audit = OtpToken(
            transaction_id=tx_id,
            otp_code=hash_otp(otp_code),
            expires_at=datetime.utcnow() + timedelta(seconds=300)
        )
        db.add(otp_audit)

        await db.commit()
        await db.refresh(new_tx)

        # 6. Gửi email OTP ngầm qua Notification Service
        await NotificationServiceClient.send_otp(
            to_email=user_email,
            recipient_name=user_info.get("full_name", username),
            otp_code=otp_code,
            student_name=new_tx.student_name,
            amount=amount,
            correlation_id=correlation_id
        )

        return {
            "transaction_id": new_tx.id,
            "status": new_tx.status,
            "student_code": new_tx.student_code,
            "student_name": new_tx.student_name,
            "semester": new_tx.semester,
            "amount": new_tx.amount,
            "expires_in_seconds": 300,
            "user_email": user_email,
            "message": f"Mã OTP đã được gửi đến email {user_email}. Mã có hiệu lực trong 5 phút."
        }
    finally:
        if lock_idemp_key:
            await release_distributed_lock(lock_idemp_key, lock_token)


async def confirm_payment_saga(
    db: AsyncSession,
    transaction_id: str,
    otp_code: str,
    user_id: int,
    correlation_id: Optional[str] = None
) -> dict:
    """
    Xác thực OTP và thực thi SAGA ORCHESTRATION hoàn tất thanh toán:
    1. Kiểm tra OTP hợp lệ (CHƯA XÓA để bảo vệ nếu chiếm Lock thất bại).
    2. Chiếm Distributed Lock (Redis Lock có TTL 10s chống Deadlock) trên user và sinh viên.
    3. Tiêu thụ & Xóa vĩnh viễn OTP (Single-use).
    4. Saga Step 1: Gọi User Service trừ tiền (Pessimistic Lock ở DB).
    5. Saga Step 2: Gọi Tuition Service gạch nợ học phí.
    6. Saga Compensate & Bồi hoàn:
       - Nếu Step 2 gặp lỗi (409 Conflict, Timeout, hoặc lỗi mạng):
       - Hủy gạch nợ bên Tuition Service (phòng ngừa commit dở dang).
       - Hoàn tiền ngay lập tức bên User Service (Compensating action).
       - Gửi email thông báo thất bại & xác nhận hoàn tiền về ví cho người dùng!
    7. Thành công: Cập nhật SUCCESS, gửi email biên nhận và giải phóng Lock trong finally.
    """
    # 1. Kiểm tra giao dịch tồn tại
    stmt_tx = select(Transaction).where(Transaction.id == transaction_id)
    res_tx = await db.execute(stmt_tx)
    tx = res_tx.scalar_one_or_none()

    if not tx or tx.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin giao dịch."
        )

    if tx.status != "PENDING_OTP":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Giao dịch đã ở trạng thái '{tx.status}', không thể xác thực lại."
        )

    # 2. Bước A: Kiểm tra OTP hợp lệ (CSPRNG + Hashed + Giới hạn 5 lần thử chống brute-force)
    is_otp_valid, otp_msg, is_expired_or_locked = await verify_otp(transaction_id=transaction_id, input_otp=otp_code)
    if not is_otp_valid:
        if is_expired_or_locked:
            if "hết hạn" in otp_msg:
                tx.status = "EXPIRED"
                tx.failure_reason = "Mã OTP đã hết hạn (quá 5 phút)"
            else:
                tx.status = "FAILED"
                tx.failure_reason = "Nhập sai mã OTP quá 5 lần. Giao dịch bị hủy."
            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=otp_msg
        )

    # 3. Bước B: Chiếm Distributed Lock (Redis Lock có TTL 10s chống Deadlock)
    lock_user_key = f"lock:user:{tx.user_id}"
    lock_student_key = f"lock:student:{tx.student_code}"
    lock_token = str(uuid.uuid4())

    user_locked = await acquire_distributed_lock(lock_user_key, lock_token, ttl_seconds=10)
    student_locked = await acquire_distributed_lock(lock_student_key, lock_token, ttl_seconds=10)

    if not user_locked or not student_locked:
        # Nếu chưa chiếm được Lock, nhả lock một phần nếu có và báo bận (OTP vẫn còn nguyên)
        if user_locked:
            await release_distributed_lock(lock_user_key, lock_token)
        if student_locked:
            await release_distributed_lock(lock_student_key, lock_token)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hệ thống đang xử lý một giao dịch khác trên tài khoản hoặc khoản học phí này. Vui lòng bấm xác nhận lại sau vài giây."
        )

    # 4. Bước C: Đã chiếm Lock an toàn -> Tiêu thụ và XÓA VĨNH VIỄN mã OTP (Single-use)
    await consume_otp(transaction_id)

    # Đánh dấu trong DB và chuyển trạng thái sang PROCESSING
    stmt_otp_db = select(OtpToken).where(OtpToken.transaction_id == transaction_id)
    res_otp_db = await db.execute(stmt_otp_db)
    otp_db = res_otp_db.scalar_one_or_none()
    if otp_db:
        otp_db.is_used = True

    tx.status = "PROCESSING"
    await db.commit()

    deducted_successfully = False

    try:
        # SAGA STEP 1: Trừ tiền người nộp tại User Service (Có Pessimistic Lock tại DB)
        try:
            await UserServiceClient.deduct_balance(
                user_id=tx.user_id,
                amount=tx.amount,
                transaction_id=tx.id,
                description=f"Thanh toán học phí MSSV {tx.student_code} ({tx.semester})",
                correlation_id=correlation_id
            )
            deducted_successfully = True
        except HTTPException as e:
            tx.status = "FAILED"
            tx.failure_reason = f"Trừ tiền thất bại: {e.detail}"
            await db.commit()
            raise e

        # SAGA STEP 2: Gạch nợ học phí tại Tuition Service (Có Pessimistic Lock tại DB)
        try:
            await TuitionServiceClient.pay_invoice(
                student_code=tx.student_code,
                amount=tx.amount,
                username=tx.username,
                transaction_id=tx.id,
                invoice_id=tx.invoice_id,
                correlation_id=correlation_id
            )
        except Exception as e:
            # SỰ CỐ BƯỚC 2: Bị 409 Conflict (người khác đã đóng) HOẶC Timeout / Lỗi mạng
            err_detail = e.detail if isinstance(e, HTTPException) else str(e)

            # KÍCH HOẠT CHUỖI SAGA COMPENSATING ROLLBACK:
            # 1. Hủy gạch nợ bên Tuition Service (phòng ngừa commit dở dang)
            await TuitionServiceClient.cancel_invoice(
                student_code=tx.student_code,
                transaction_id=tx.id,
                invoice_id=tx.invoice_id,
                correlation_id=correlation_id
            )

            # 2. Hoàn lại tiền cho tài khoản người dùng
            refund_success = False
            if deducted_successfully:
                try:
                    refund_res = await UserServiceClient.refund_balance(
                        user_id=tx.user_id,
                        amount=tx.amount,
                        transaction_id=tx.id,
                        reason=f"Hoàn tiền do sự cố gạch nợ học phí ({err_detail})",
                        correlation_id=correlation_id
                    )
                    refund_success = refund_res.get("success", False) if isinstance(refund_res, dict) else True
                except Exception as refund_err:
                    print(f"CRITICAL: Refund failed for tx {tx.id}: {refund_err}")
                    refund_success = False

            # 3. Cập nhật trạng thái giao dịch chuẩn xác (Không báo đã hoàn tiền nếu refund thất bại)
            if not deducted_successfully or refund_success:
                tx.status = "FAILED"
                tx.failure_reason = f"Gạch nợ học phí không thành công ({err_detail}). Số tiền {tx.amount:,.0f} VNĐ đã được hoàn lại vào tài khoản của bạn."
            else:
                tx.status = "COMPENSATION_PENDING"
                tx.failure_reason = f"Gạch nợ học phí thất bại và hệ thống gặp sự cố khi hoàn tiền tự động ({err_detail}). Giao dịch đang chờ đối soát bồi hoàn."
            await db.commit()

            # 4. GỬI EMAIL THÔNG BÁO THẤT BẠI (Chỉ báo đã hoàn tiền nếu hoàn tiền thực sự thành công)
            if deducted_successfully and refund_success:
                await NotificationServiceClient.send_failure_refund(
                    to_email=tx.user_email,
                    recipient_name=tx.username,
                    transaction_id=tx.id,
                    student_code=tx.student_code,
                    amount=tx.amount,
                    reason=tx.failure_reason,
                    correlation_id=correlation_id
                )

            status_code = e.status_code if isinstance(e, HTTPException) else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(
                status_code=status_code,
                detail=tx.failure_reason
            )

        # CẢ 2 BƯỚC ĐỀU THÀNH CÔNG -> HOÀN TẤT GIAO DỊCH
        tx.status = "SUCCESS"
        tx.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(tx)

        # Gửi email biên nhận thanh toán thành công
        await NotificationServiceClient.send_receipt(
            to_email=tx.user_email,
            recipient_name=tx.username,
            transaction_id=tx.id,
            student_code=tx.student_code,
            student_name=tx.student_name,
            amount=tx.amount,
            completed_at=tx.completed_at.strftime("%d/%m/%Y %H:%M:%S"),
            correlation_id=correlation_id
        )

        return {
            "success": True,
            "transaction_id": tx.id,
            "status": "SUCCESS",
            "student_code": tx.student_code,
            "student_name": tx.student_name,
            "semester": tx.semester,
            "amount": tx.amount,
            "completed_at": tx.completed_at,
            "message": "Thanh toán học phí thành công! Biên lai đã được gửi đến email của bạn."
        }

    finally:
        # LUÔN GIẢI PHÓNG DISTRIBUTED LOCK TRONG FINALLY
        await release_distributed_lock(lock_user_key, lock_token)
        await release_distributed_lock(lock_student_key, lock_token)


async def cancel_payment_saga(db: AsyncSession, transaction_id: str, user_id: int) -> dict:
    """Hủy phiên giao dịch PENDING_OTP và vô hiệu hóa mã OTP trong Redis ngay lập tức."""
    stmt = select(Transaction).where(
        and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    res = await db.execute(stmt)
    tx = res.scalar_one_or_none()

    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin giao dịch cần hủy."
        )

    if tx.status == "PENDING_OTP":
        tx.status = "CANCELLED"
        tx.failure_reason = "Người dùng chủ động hủy phiên giao dịch tại Modal OTP"
        await invalidate_otp(transaction_id)
        await db.commit()
        await db.refresh(tx)

    return {
        "success": True,
        "transaction_id": tx.id,
        "status": tx.status,
        "message": "Đã hủy phiên giao dịch và vô hiệu hóa mã OTP thành công."
    }

