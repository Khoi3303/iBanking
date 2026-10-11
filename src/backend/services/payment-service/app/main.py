from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
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


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Hệ thống điều phối giao dịch thanh toán học phí iBanking, quản lý OTP và Saga Orchestrator.",
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
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """
    Khởi tạo giao dịch đóng học phí (Mục 2 & Mục 3 của đề bài):
    - Kiểm tra số dư >= học phí và khoản học phí chưa thanh toán.
    - Hủy các phiên PENDING_OTP cũ của user này nếu có.
    - Tạo giao dịch mới, sinh OTP 6 số ngẫu nhiên có TTL 300s (5 phút) trên Redis.
    - Gửi email chứa mã OTP đến email của người nộp tiền.
    """
    user_id = int(current_user.get("sub"))
    username = current_user.get("username", "user")
    user_email = current_user.get("email", "")

    result = await initiate_payment_saga(
        db=db,
        user_id=user_id,
        username=username,
        user_email=user_email,
        student_code=req.student_code.strip(),
        amount=req.amount,
        invoice_id=req.invoice_id
    )
    return result


@app.post(
    "/payments/confirm",
    response_model=ConfirmOtpResponse,
    tags=["Payment Lifecycle"]
)
async def confirm_payment(
    req: ConfirmOtpRequest,
    current_user: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db)
):
    """
    Xác thực giao dịch bằng OTP và thực thi thanh toán (Mục 3 & Mục 4 của đề bài):
    - Kiểm tra OTP: Đúng mã, còn trong 5 phút, và tiêu thụ ngay lập tức (Single-use).
    - Thực thi Saga:
      + Trừ tiền tài khoản (với khóa dòng Pessimistic chống Double-spending).
      + Gạch nợ học phí tại TDTU (với khóa dòng chống Race condition 2 người trả).
      + Bồi hoàn hoàn tiền (Compensate) nếu bước gạch nợ học phí thất bại.
    - Gửi email biên nhận thanh toán thành công và cập nhật lịch sử.
    """
    user_id = int(current_user.get("sub"))

    result = await confirm_payment_saga(
        db=db,
        transaction_id=req.transaction_id,
        otp_code=req.otp_code.strip(),
        user_id=user_id
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
    "/internal/otp/{transaction_id}",
    tags=["Internal Testing"]
)
async def get_internal_test_otp(
    transaction_id: str,
    x_internal_secret: str = Header(..., alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db)
):
    """API nội bộ hỗ trợ kiểm thử tự động (test automation) lấy mã OTP."""
    if x_internal_secret != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    from app.models import OtpToken
    stmt = select(OtpToken).where(OtpToken.transaction_id == transaction_id, OtpToken.is_used == False)
    res = await db.execute(stmt)
    otp_record = res.scalar_one_or_none()
    if not otp_record:
        raise HTTPException(status_code=404, detail="OTP not found")
    return {"otp_code": otp_record.otp_code}

