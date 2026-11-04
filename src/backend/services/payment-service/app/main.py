import uuid
import time
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db
from app.models import Transaction
from app.schemas import (
    InitiatePaymentRequest, InitiatePaymentResponse,
    ConfirmOtpRequest, ConfirmOtpResponse,
    CancelPaymentRequest, CancelPaymentResponse,
    TransactionResponse
)
from app.saga_orchestrator import initiate_payment_saga, confirm_payment_saga, cancel_payment_saga
from app.clients import close_http_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("payment_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quản lý vòng đời Payment Service:
    - Khởi động: Shared HTTP Client (connection pool) đã được lazy-init trong clients.py.
    - Tắt máy: Đóng gracefully shared HTTP Client để giải phóng connection.
    """
    yield
    await close_http_client()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Hệ thống điều phối giao dịch thanh toán học phí iBanking, quản lý OTP và Saga Orchestrator.",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan
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


security = HTTPBearer()

def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Xác thực JWT Token từ Header và trích xuất thông tin người dùng."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ.")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ hoặc đã hết hạn.")


@app.get("/health", tags=["System"])
async def health_check():
    """Kiểm tra sức khỏe Payment Service."""
    return {"status": "ok", "service": settings.APP_NAME}


@app.post(
    "/payments/initiate",
    response_model=InitiatePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Payment Lifecycle"]
)
async def initiate_payment(
    req: InitiatePaymentRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """
    Khởi tạo giao dịch đóng học phí (Mục 2 & Mục 3 của đề bài):
    - Hỗ trợ Idempotency-Key chống trùng lặp request khi bấm nhiều lần.
    - Kiểm tra số dư >= học phí và khoản học phí chưa thanh toán.
    - Hủy các phiên PENDING_OTP cũ của user này nếu có.
    - Tạo giao dịch mới, sinh OTP 6 số ngẫu nhiên có TTL 300s (5 phút) trên Redis.
    - Gửi email chứa mã OTP đến email của người nộp tiền.
    """
    user_id = int(current_user.get("sub"))
    username = current_user.get("username", "user")
    user_email = current_user.get("email", "")
    corr_id = getattr(request.state, "correlation_id", None)

    result = await initiate_payment_saga(
        db=db,
        user_id=user_id,
        username=username,
        user_email=user_email,
        student_code=req.student_code.strip(),
        amount=req.amount,
        invoice_id=req.invoice_id,
        idempotency_key=idempotency_key,
        correlation_id=corr_id
    )
    return result


@app.post(
    "/payments/confirm",
    response_model=ConfirmOtpResponse,
    tags=["Payment Lifecycle"]
)
async def confirm_payment(
    req: ConfirmOtpRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """
    Xác thực giao dịch bằng OTP và thực thi thanh toán (Mục 3 & Mục 4 của đề bài):
    - Kiểm tra OTP: Đúng mã, còn trong 5 phút, và tiêu thụ ngay lập tức (Single-use).
    - Chuyển trạng thái sang PROCESSING và thực thi Saga.
    - Gửi email biên nhận thanh toán thành công và cập nhật lịch sử.
    """
    user_id = int(current_user.get("sub"))
    corr_id = getattr(request.state, "correlation_id", None)

    result = await confirm_payment_saga(
        db=db,
        transaction_id=req.transaction_id,
        otp_code=req.otp_code.strip(),
        user_id=user_id,
        correlation_id=corr_id
    )
    return result


@app.post(
    "/payments/cancel",
    response_model=CancelPaymentResponse,
    tags=["Payment Lifecycle"]
)
async def cancel_payment(
    req: CancelPaymentRequest,
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """
    Hủy phiên giao dịch khi người dùng đóng Modal OTP:
    - Vô hiệu hóa và xóa ngay mã OTP trong Redis.
    - Cập nhật trạng thái giao dịch sang CANCELLED.
    """
    user_id = int(current_user.get("sub"))
    result = await cancel_payment_saga(
        db=db,
        transaction_id=req.transaction_id,
        user_id=user_id
    )
    return result


@app.get(
    "/payments/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["Payment Queries"]
)
async def get_transaction_detail(
    transaction_id: str,
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """Tra cứu chi tiết một giao dịch theo transaction_id."""
    user_id = int(current_user.get("sub"))
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    res = await db.execute(stmt)
    tx = res.scalar_one_or_none()

    if not tx or tx.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông tin giao dịch.")
    return tx


@app.get(
    "/payments/history",
    response_model=List[TransactionResponse],
    tags=["Payment Queries"]
)
async def get_payment_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách các giao dịch thanh toán của người dùng đang đăng nhập.
    Đáp ứng yêu cầu Mục 1 & Mục 4 trong đề bài.
    """
    user_id = int(current_user.get("sub"))
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@app.get(
    "/payments/internal/pending-status/{student_code}",
    tags=["Internal Payment APIs"]
)
async def check_student_pending_status(
    student_code: str,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db)
):
    """
    API nội bộ: Kiểm tra xem sinh viên có đang trong phiên giao dịch PENDING_OTP còn hạn (300s) hay không.
    Dùng cho API Gateway khi tra cứu học phí để vô hiệu hóa nút thanh toán nếu có người khác đang giữ mã OTP.
    """
    expire_cutoff = datetime.utcnow() - timedelta(seconds=settings.OTP_EXPIRE_SECONDS)
    stmt = (
        select(Transaction)
        .where(
            and_(
                Transaction.student_code == student_code.strip(),
                Transaction.status == "PENDING_OTP",
                Transaction.created_at >= expire_cutoff
            )
        )
        .order_by(desc(Transaction.created_at))
    )
    res = await db.execute(stmt)
    active_tx = res.scalar_one_or_none()

    if active_tx:
        return {
            "is_pending": True,
            "user_id": active_tx.user_id,
            "transaction_id": active_tx.id
        }
    return {
        "is_pending": False,
        "user_id": None,
        "transaction_id": None
    }



