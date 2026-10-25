from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, status, Header
from app.config import settings
from app.schemas import (
    SendOtpEmailRequest,
    SendReceiptEmailRequest,
    SendFailureRefundEmailRequest,
    EmailResponse
)
from app.email_sender import send_otp_email, send_receipt_email, send_refund_email

import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("notification_service")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Dịch vụ gửi thông báo và Email tự động cho phân hệ iBanking TDTU.",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = corr_id
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        process_time_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Correlation-ID"] = corr_id
        logger.info(f"[cid:{corr_id}] {request.method} {request.url.path} -> {response.status_code} ({process_time_ms:.1f}ms)")
        return response

app.add_middleware(CorrelationIDMiddleware)

async def verify_internal_secret(
    x_internal_secret: str = Header(..., alias="X-Internal-Secret", description="Mã xác thực nội bộ giữa các microservices")
):
    """Bảo vệ các endpoint gửi mail nội bộ: Chống spam và truy cập trái phép từ bên ngoài."""
    if x_internal_secret != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Truy cập nội bộ bị từ chối. Mã xác thực Service không chính xác."
        )


@app.get("/health", tags=["System"])
async def health_check():
    """Kiểm tra sức khỏe Notification Service."""
    return {"status": "ok", "service": settings.APP_NAME, "smtp_host": settings.SMTP_HOST}


@app.post(
    "/notifications/send-otp",
    response_model=EmailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Email Notifications"],
    dependencies=[Depends(verify_internal_secret)]
)
async def api_send_otp_email(req: SendOtpEmailRequest, background_tasks: BackgroundTasks):
    """
    Tiếp nhận yêu cầu gửi Email chứa mã OTP xác thực:
    - Bảo vệ bởi Header X-Internal-Secret.
    - Đẩy vào BackgroundTasks gửi ngầm bất đồng bộ, phản hồi HTTP chỉ trong vài mili-giây.
    """
    background_tasks.add_task(
        send_otp_email,
        to_email=str(req.to_email),
        recipient_name=req.recipient_name,
        otp_code=req.otp_code,
        student_name=req.student_name,
        amount=req.amount,
        expires_minutes=req.expires_minutes,
        student_code=req.student_code
    )
    return {
        "success": True,
        "message": f"Yêu cầu gửi mã OTP tới {req.to_email} đã được đưa vào hàng đợi xử lý."
    }


@app.post(
    "/notifications/send-receipt",
    response_model=EmailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Email Notifications"],
    dependencies=[Depends(verify_internal_secret)]
)
async def api_send_receipt_email(req: SendReceiptEmailRequest, background_tasks: BackgroundTasks):
    """
    Tiếp nhận yêu cầu gửi Email biên nhận thanh toán học phí thành công.
    """
    background_tasks.add_task(
        send_receipt_email,
        to_email=str(req.to_email),
        recipient_name=req.recipient_name,
        transaction_id=req.transaction_id,
        student_code=req.student_code,
        student_name=req.student_name,
        amount=req.amount,
        completed_at=req.completed_at
    )
    return {
        "success": True,
        "message": f"Yêu cầu gửi biên nhận thanh toán tới {req.to_email} đã được đưa vào hàng đợi xử lý."
    }


@app.post(
    "/notifications/send-failure-refund",
    response_model=EmailResponse,
    status_code=status.HTTP_200_OK,
    tags=["Email Notifications"],
    dependencies=[Depends(verify_internal_secret)]
)
async def api_send_failure_refund_email(req: SendFailureRefundEmailRequest, background_tasks: BackgroundTasks):
    """
    Tiếp nhận yêu cầu gửi Email thông báo giao dịch thất bại và đã hoàn lại tiền vào tài khoản iBanking.
    """
    background_tasks.add_task(
        send_refund_email,
        to_email=str(req.to_email),
        recipient_name=req.recipient_name,
        transaction_id=req.transaction_id,
        student_code=req.student_code,
        amount=req.amount,
        reason=req.reason
    )
    return {
        "success": True,
        "message": f"Yêu cầu gửi thông báo hoàn tiền tới {req.to_email} đã được đưa vào hàng đợi xử lý."
    }
