import uuid
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
    acquire_distributed_lock,
    release_distributed_lock
)
from app.clients import UserServiceClient, TuitionServiceClient, NotificationServiceClient

def mask_email(email: str) -> str:
    """Ẩn bớt ký tự email để bảo mật thông tin (vd: nguyenvana@gmail.com -> ngu***@gmail.com)."""
    if "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if len(name) <= 3:
        masked_name = name[0] + "***"
    else:
        masked_name = name[:3] + "***"
    return f"{masked_name}@{domain}"


async def initiate_payment_saga(
    db: AsyncSession,
    user_id: int,
    username: str,
    user_email: str,
    student_code: str,
    amount: Decimal,
    invoice_id: Optional[int] = None
) -> dict:
    """
    Khởi tạo giao dịch đóng học phí (Bước 1):
    1. Kiểm tra tính hợp lệ của khoản nợ học phí từ Tuition Service.
    2. Kiểm tra số dư tài khoản từ User Service (phải >= amount).
    3. Hủy bỏ các phiên giao dịch PENDING_OTP cũ của user này (giải quyết case bấm tắt đi bật lại).
    4. Tạo Transaction mới ở trạng thái PENDING_OTP.
    5. Sinh mã OTP ngẫu nhiên 6 số, TTL 300s, không trùng lặp (Redis + DB Audit).
    6. Gửi email mã OTP qua Notification Service.
    """
    # 1. Tra cứu học phí phía TDTU
    tuition_info = await TuitionServiceClient.get_student_tuition(student_code)
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
    user_info = await UserServiceClient.get_user(user_id)
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
        status="PENDING_OTP"
    )
    db.add(new_tx)

    # 5. Sinh mã OTP trong Redis (TTL 300s, không trùng lặp)
    otp_code = await generate_unique_otp(transaction_id=tx_id, length=6, expire_seconds=300)

    # Lưu Audit log trong DB
    otp_audit = OtpToken(
        transaction_id=tx_id,
        otp_code=otp_code,
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
        amount=amount
    )

    return {
        "transaction_id": new_tx.id,
        "status": new_tx.status,
        "student_code": new_tx.student_code,
        "student_name": new_tx.student_name,
        "semester": new_tx.semester,
        "amount": new_tx.amount,
        "expires_in_seconds": 300,
        "user_email": mask_email(user_email),
        "message": f"Mã OTP đã được gửi đến email {mask_email(user_email)}. Mã có hiệu lực trong 5 phút."
    }


async def confirm_payment_saga(
    db: AsyncSession,
    transaction_id: str,
    otp_code: str,
    user_id: int
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

    # 2. Bước A: Kiểm tra OTP hợp lệ (CHƯA XÓA để người dùng có thể retry nếu lock bận)
    is_otp_valid = await verify_otp(transaction_id=transaction_id, input_otp=otp_code)
    if not is_otp_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác hoặc đã hết hạn (quá 5 phút). Vui lòng kiểm tra lại email."
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

    # Đánh dấu trong DB
    stmt_otp_db = select(OtpToken).where(OtpToken.transaction_id == transaction_id)
    res_otp_db = await db.execute(stmt_otp_db)
    otp_db = res_otp_db.scalar_one_or_none()
    if otp_db:
        otp_db.is_used = True

    deducted_successfully = False

    try:
        # SAGA STEP 1: Trừ tiền người nộp tại User Service (Có Pessimistic Lock tại DB)
        try:
            await UserServiceClient.deduct_balance(
                user_id=tx.user_id,
                amount=tx.amount,
                transaction_id=tx.id,
                description=f"Thanh toán học phí MSSV {tx.student_code} ({tx.semester})"
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
                invoice_id=tx.invoice_id
            )
        except Exception as e:
            # SỰ CỐ BƯỚC 2: Bị 409 Conflict (người khác đã đóng) HOẶC Timeout / Lỗi mạng
            err_detail = e.detail if isinstance(e, HTTPException) else str(e)

            # KÍCH HOẠT CHUỖI SAGA COMPENSATING ROLLBACK:
            # 1. Hủy gạch nợ bên Tuition Service (phòng ngừa commit dở dang)
            await TuitionServiceClient.cancel_invoice(
                student_code=tx.student_code,
                transaction_id=tx.id,
                invoice_id=tx.invoice_id
            )

            # 2. Hoàn lại tiền cho tài khoản người dùng
            if deducted_successfully:
                await UserServiceClient.refund_balance(
                    user_id=tx.user_id,
                    amount=tx.amount,
                    transaction_id=tx.id,
                    reason=f"Hoàn tiền do sự cố gạch nợ học phí ({err_detail})"
                )

            # 3. Cập nhật trạng thái giao dịch
            tx.status = "FAILED"
            tx.failure_reason = f"Gạch nợ học phí không thành công ({err_detail}). Số tiền {tx.amount:,.0f} VNĐ đã được hoàn lại vào tài khoản của bạn."
            await db.commit()

            # 4. GỬI EMAIL THÔNG BÁO THẤT BẠI VÀ ĐÃ HOÀN TIỀN VỀ VÍ (Chuẩn mực ngân hàng)
            await NotificationServiceClient.send_failure_refund(
                to_email=tx.user_email,
                recipient_name=tx.username,
                transaction_id=tx.id,
                student_code=tx.student_code,
                amount=tx.amount,
                reason=tx.failure_reason
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
            completed_at=tx.completed_at.strftime("%d/%m/%Y %H:%M:%S")
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

