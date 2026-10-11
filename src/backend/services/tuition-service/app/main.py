from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.schemas import (
    StudentInquiryResponse,
    PayInvoiceRequest, PayInvoiceResponse,
    CancelInvoicePaymentRequest, CancelInvoicePaymentResponse
)
from app.services import (
    inquire_student_tuition,
    pay_tuition_invoice,
    cancel_tuition_payment
)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Hệ thống mô phỏng Cổng Quản lý Đào tạo & Học phí Sinh viên Đại học Tôn Đức Thắng (TDTU).",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def verify_internal_secret(
    x_internal_secret: str = Header(..., alias="X-Internal-Secret", description="Mã xác thực giữa các service nội bộ")
):
    """Bảo vệ các API nội bộ: Chỉ cho phép Payment Service gọi."""
    if x_internal_secret != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Truy cập nội bộ bị từ chối. Mã xác thực Service không chính xác."
        )


@app.on_event("startup")
async def startup_event():
    """Tự động kiểm tra và seed danh sách sinh viên & học phí TDTU khi khởi động."""
    try:
        from app.database import engine, Base
        from app.seed import seed_data
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_data()
    except Exception as e:
        print(f"Tuition startup seed notice: {e}")


@app.get("/health", tags=["System"])
async def health_check():
    """Kiểm tra trạng thái hoạt động của TDTU Tuition Service."""
    return {"status": "ok", "service": settings.APP_NAME}


@app.get(
    "/tuition/students/{student_code}",
    response_model=StudentInquiryResponse,
    tags=["Student Tuition Inquiry"]
)
async def get_student_tuition(
    student_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Tra cứu thông tin sinh viên và học phí cần đóng theo MSSV.
    - Đáp ứng Mục 2.b của đề bài: Nhập MSSV -> Tự động hiển thị tên sinh viên, học kỳ, số tiền cần đóng.
    - Xử lý trọn vẹn 3 trường hợp:
      1. Không tìm thấy sinh viên -> 404
      2. Đã đóng học phí -> trả về status='PAID', can_pay=False (UI disable nút đóng tiền)
      3. Còn nợ học phí -> trả về status='UNPAID', can_pay=True kèm invoice_id
    """
    inquiry = await inquire_student_tuition(db=db, student_code=student_code.strip())
    return inquiry


# ========================================================
# CÁC API NỘI BỘ (INTERNAL APIS - YÊU CẦU X-Internal-Secret)
# ========================================================

@app.post(
    "/internal/tuition/pay",
    response_model=PayInvoiceResponse,
    tags=["Internal Tuition"],
    dependencies=[Depends(verify_internal_secret)]
)
async def pay_invoice(
    req: PayInvoiceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    API nội bộ: Gạch nợ học phí cho sinh viên TDTU (gọi từ Payment Service).
    - Khóa dòng Pessimistic (SELECT ... FOR UPDATE) trên khóa chính invoice_id hoặc student_code.
    - Đảm bảo tính Idempotency: Retry cùng transaction_id không bị lỗi.
    - Cập nhật trạng thái 'PAID', thời gian đóng, người đóng và mã giao dịch.
    """
    invoice = await pay_tuition_invoice(
        db=db,
        student_code=req.student_code,
        amount=req.amount,
        username=req.username,
        transaction_id=req.transaction_id,
        invoice_id=req.invoice_id,
        semester=req.semester
    )

    return {
        "success": True,
        "invoice_id": invoice.id,
        "student_code": invoice.student_code,
        "semester": invoice.semester,
        "amount": invoice.amount,
        "status": invoice.status,
        "paid_by_user": invoice.paid_by_user,
        "paid_at": invoice.paid_at,
        "transaction_ref": invoice.transaction_ref,
        "message": f"Gạch nợ thành công khoản học phí {invoice.amount:,.0f} VNĐ cho sinh viên {invoice.student_code}."
    }


@app.post(
    "/internal/tuition/cancel",
    response_model=CancelInvoicePaymentResponse,
    tags=["Internal Tuition"],
    dependencies=[Depends(verify_internal_secret)]
)
async def cancel_invoice(
    req: CancelInvoicePaymentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    API nội bộ: Hủy gạch nợ học phí (Saga Compensation) nếu giao dịch gặp lỗi bất khả kháng ở bước sau.
    - Khóa dòng với with_for_update().
    - Kiểm tra đúng transaction_id mới cho phép hoàn tác về trạng thái UNPAID.
    """
    success = await cancel_tuition_payment(
        db=db,
        student_code=req.student_code,
        transaction_id=req.transaction_id,
        invoice_id=req.invoice_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hóa đơn cần hủy gạch nợ hoặc mã giao dịch không khớp."
        )

    return {
        "success": True,
        "invoice_id": req.invoice_id,
        "message": f"Đã hoàn tác gạch nợ học phí cho sinh viên {req.student_code}."
    }


@app.post("/internal/tuition/reset-demo", tags=["Internal Tuition"], dependencies=[Depends(verify_internal_secret)])
async def reset_demo_tuition(db: AsyncSession = Depends(get_db)):
    """API nội bộ: Khôi phục trạng thái hóa đơn ban đầu cho sinh viên demo để chạy test tự động lặp lại."""
    from sqlalchemy import update
    await db.execute(
        update(TuitionInvoice)
        .where(TuitionInvoice.student_code == "524H0001")
        .values(status="UNPAID", paid_at=None, paid_by_user=None, transaction_ref=None)
    )
    await db.commit()
    return {"status": "ok", "message": "Đã khôi phục hóa đơn sinh viên 524H0001 về UNPAID."}

