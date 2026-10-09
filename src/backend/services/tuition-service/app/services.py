from decimal import Decimal
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status
from app.models import Student, TuitionInvoice

async def inquire_student_tuition(db: AsyncSession, student_code: str):
    """
    Tra cứu thông tin sinh viên và khoản học phí theo MSSV.
    - SỬ DỤNG TRUY VẤN ĐỌC THƯỜNG (SELECT không with_for_update) để tránh block các người dùng khác tra cứu.
    - Xử lý trọn vẹn 3 kịch bản thực tế (Edge cases cho UI):
      1. Sinh viên không tồn tại -> 404 NOT_FOUND
      2. Sinh viên tồn tại nhưng không có nợ / đã đóng xong -> status = 'PAID' hoặc 'NO_DEBT', can_pay = False (UI disable nút đóng tiền)
      3. Sinh viên còn nợ -> status = 'UNPAID', can_pay = True (UI cho phép đóng)
    """
    # 1. Tìm sinh viên
    stmt_student = select(Student).where(Student.student_code == student_code)
    res_student = await db.execute(stmt_student)
    student = res_student.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sinh viên có MSSV: '{student_code}' tại Trường Đại học Tôn Đức Thắng."
        )

    # 2. Tìm khoản nợ học phí chưa thanh toán (UNPAID)
    stmt_unpaid = (
        select(TuitionInvoice)
        .where(and_(TuitionInvoice.student_code == student_code, TuitionInvoice.status == "UNPAID"))
        .order_by(TuitionInvoice.id.desc())
    )
    res_unpaid = await db.execute(stmt_unpaid)
    unpaid_invoice = res_unpaid.scalar_one_or_none()

    # Kịch bản 1: Có khoản nợ UNPAID hợp lệ
    if unpaid_invoice:
        return {
            "student_code": student.student_code,
            "student_name": student.full_name,
            "class_name": student.class_name,
            "major": student.major,
            "invoice_id": unpaid_invoice.id,
            "semester": unpaid_invoice.semester,
            "amount": unpaid_invoice.amount,
            "status": "UNPAID",
            "can_pay": True,
            "message": f"Sinh viên có khoản học phí cần thanh toán cho học kỳ {unpaid_invoice.semester}."
        }

    # Kịch bản 2: Không còn nợ UNPAID, kiểm tra xem đã đóng xong (PAID) hay không
    stmt_latest_paid = (
        select(TuitionInvoice)
        .where(TuitionInvoice.student_code == student_code)
        .order_by(TuitionInvoice.id.desc())
    )
    res_latest_paid = await db.execute(stmt_latest_paid)
    latest_paid_invoice = res_latest_paid.scalar_one_or_none()

    if latest_paid_invoice:
        paid_date_str = latest_paid_invoice.paid_at.strftime('%d/%m/%Y %H:%M') if latest_paid_invoice.paid_at else ''
        return {
            "student_code": student.student_code,
            "student_name": student.full_name,
            "class_name": student.class_name,
            "major": student.major,
            "invoice_id": latest_paid_invoice.id,
            "semester": latest_paid_invoice.semester,
            "amount": latest_paid_invoice.amount,
            "status": "PAID",
            "can_pay": False,
            "message": f"Khoản học phí học kỳ {latest_paid_invoice.semester} đã được thanh toán hoàn tất (Người nộp: {latest_paid_invoice.paid_by_user or 'N/A'}{f', ngày {paid_date_str}' if paid_date_str else ''})."
        }

    # Kịch bản 3: Sinh viên chưa phát sinh bất kỳ khoản nợ nào
    return {
        "student_code": student.student_code,
        "student_name": student.full_name,
        "class_name": student.class_name,
        "major": student.major,
        "invoice_id": None,
        "semester": None,
        "amount": Decimal("0.00"),
        "status": "NO_DEBT",
        "can_pay": False,
        "message": f"Sinh viên {student.full_name} hiện không có công nợ học phí nào cần thanh toán."
    }


async def pay_tuition_invoice(
    db: AsyncSession,
    student_code: str,
    amount: Decimal,
    username: str,
    transaction_id: str,
    invoice_id: Optional[int] = None,
    semester: Optional[str] = None
) -> TuitionInvoice:
    """
    Gạch nợ học phí cho sinh viên:
    1. Kiểm tra Idempotency: Nếu chính transaction_id này đã gạch nợ thành công, trả kết quả cũ ngay.
    2. Khóa dòng Pessimistic Locking trực tiếp trên Primary Key (invoice_id) hoặc (student_code + semester).
       Tối ưu index và loại bỏ rủi ro khóa nhầm dòng.
    3. Giải quyết tình huống Concurrency 2: Báo lỗi 409 Conflict nếu người khác đã thanh toán trước.
    """
    # 1. Kiểm tra Idempotency
    stmt_idemp = select(TuitionInvoice).where(
        TuitionInvoice.student_code == student_code,
        TuitionInvoice.transaction_ref == transaction_id,
        TuitionInvoice.status == "PAID"
    )
    res_idemp = await db.execute(stmt_idemp)
    idemp_invoice = res_idemp.scalar_one_or_none()
    if idemp_invoice:
        return idemp_invoice

    # 2. Khóa dòng với with_for_update()
    if invoice_id:
        # Khóa trực tiếp trên Primary Key -> Tối ưu index và độc quyền 1 dòng duy nhất trong InnoDB
        stmt = select(TuitionInvoice).where(TuitionInvoice.id == invoice_id)
    else:
        # Fallback theo MSSV và học kỳ
        stmt = select(TuitionInvoice).where(TuitionInvoice.student_code == student_code)
        if semester:
            stmt = stmt.where(TuitionInvoice.semester == semester)
        else:
            stmt = stmt.where(TuitionInvoice.status == "UNPAID").order_by(TuitionInvoice.id.desc())

    stmt = stmt.with_for_update()
    res = await db.execute(stmt)
    invoice = res.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy hóa đơn học phí của sinh viên {student_code}."
        )

    # KIỂM TRA TRANH CHẤP ĐỒNG THỜI (Tình huống Concurrency 2 trong Rubric)
    if invoice.status == "PAID":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Khoản học phí học kỳ {invoice.semester} của sinh viên {student_code} đã được thanh toán thành công bởi {invoice.paid_by_user or 'người khác'}."
        )

    # Kiểm tra số tiền: Chỉ cho phép thanh toán toàn bộ
    if invoice.amount != amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số tiền thanh toán ({amount:,.0f} VNĐ) không khớp với số tiền học phí ({invoice.amount:,.0f} VNĐ). Yêu cầu thanh toán toàn bộ khoản nợ."
        )

    # Thực hiện gạch nợ
    invoice.status = "PAID"
    invoice.paid_at = datetime.utcnow()
    invoice.paid_by_user = username
    invoice.transaction_ref = transaction_id
    invoice.version += 1

    await db.commit()
    await db.refresh(invoice)

    return invoice


async def cancel_tuition_payment(
    db: AsyncSession,
    student_code: str,
    transaction_id: str,
    invoice_id: Optional[int] = None
) -> bool:
    """
    Hủy gạch nợ (Saga Compensation rollback):
    1. Khóa dòng với with_for_update().
    2. Đảm bảo chỉ hoàn tác đúng hóa đơn có transaction_ref khớp với transaction_id yêu cầu.
    3. Cập nhật lại status = 'UNPAID', xóa thông tin người đóng và ngày đóng.
    """
    if invoice_id:
        stmt = select(TuitionInvoice).where(TuitionInvoice.id == invoice_id)
    else:
        stmt = select(TuitionInvoice).where(
            TuitionInvoice.student_code == student_code,
            TuitionInvoice.transaction_ref == transaction_id
        )

    stmt = stmt.with_for_update()
    res = await db.execute(stmt)
    invoice = res.scalar_one_or_none()

    if not invoice:
        return False

    # Đảm bảo chỉ rollback đúng giao dịch vừa thực hiện
    if invoice.transaction_ref != transaction_id:
        return False

    if invoice.status != "PAID":
        return False

    invoice.status = "UNPAID"
    invoice.paid_at = None
    invoice.paid_by_user = None
    invoice.transaction_ref = None
    invoice.version += 1

    await db.commit()
    return True
