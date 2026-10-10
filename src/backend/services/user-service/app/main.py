from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.schemas import (
    LoginRequest, TokenResponse, UserProfileResponse,
    DeductBalanceRequest, DeductBalanceResponse,
    RefundBalanceRequest, RefundBalanceResponse,
    AccountTransactionResponse
)
from app.services import (
    authenticate_user, get_user_by_id,
    deduct_user_balance, refund_user_balance,
    get_user_transactions
)
from app.security import create_access_token, decode_access_token

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Quản lý tài khoản người dùng, xác thực iBanking, số dư tài khoản và lịch sử giao dịch.",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Tự động kiểm tra và seed sẵn tài khoản demo nếu CSDL trống."""
    from app.database import engine, Base, AsyncSessionLocal
    from app.models import User
    from sqlalchemy import select
    from decimal import Decimal

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            demo_users = [
                ("nguyenvana", "Nguyễn Văn A", "0901234567", "khoi18042006@gmail.com", Decimal("20000000.00")),
                ("tranthib", "Trần Thị B", "0912345678", "tranthib@gmail.com", Decimal("15000000.00")),
                ("lethanhc", "Lê Thành C", "0987654321", "lethanhc@gmail.com", Decimal("5000000.00")),
            ]
            for username, full_name, phone, email, balance in demo_users:
                stmt = select(User).where(User.username == username)
                res = await session.execute(stmt)
                user = res.scalar_one_or_none()
                if not user:
                    new_user = User(
                        username=username,
                        password_hash="$2b$12$KkQeGj3aX855lJ.w3N3Wv.Rj7X0q4i.24b0W09G6L1w2X8oVb2Uwe",
                        full_name=full_name,
                        phone_number=phone,
                        email=email,
                        balance=balance
                    )
                    session.add(new_user)
                else:
                    user.email = email
            await session.commit()
    except Exception as e:
        print(f"Startup seed notice: {e}")

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Dependency lấy thông tin người dùng từ JWT Token trong header Authorization."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ.")
    
    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại.")
    return user

async def verify_internal_secret(
    x_internal_secret: str = Header(..., alias="X-Internal-Secret", description="Mã bí mật giữa các Microservices nội bộ")
):
    """Bảo vệ các API nội bộ: Chỉ cho phép các Microservices nội bộ (Payment Service) gọi."""
    if x_internal_secret != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Truy cập nội bộ bị từ chối. Mã xác thực Service không chính xác."
        )


@app.get("/health", tags=["System"])
async def health_check():
    """Kiểm tra trạng thái hoạt động của User Service."""
    return {"status": "ok", "service": settings.APP_NAME}


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Đăng nhập hệ thống iBanking bằng username và password.
    Trả về Access Token và thông tin tài khoản người dùng.
    """
    user = await authenticate_user(db, req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác."
        )

    # Sinh Access Token với subject là user.id
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username, "email": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@app.get("/users/me", response_model=UserProfileResponse, tags=["Users"])
async def get_my_profile(current_user = Depends(get_current_user)):
    """Lấy thông tin cá nhân và số dư khả dụng của tài khoản đang đăng nhập."""
    return current_user


@app.get("/users/me/transactions", response_model=List[AccountTransactionResponse], tags=["Users"])
async def get_my_transactions(
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy lịch sử giao dịch và biến động số dư của người dùng đang đăng nhập.
    Đáp ứng yêu cầu Mục 1 & Mục 4 của đề bài.
    """
    transactions = await get_user_transactions(db=db, user_id=current_user.id, limit=limit)
    return transactions


# ========================================================
# CÁC API NỘI BỘ (INTERNAL APIS - YÊU CẦU X-Internal-Secret)
# ========================================================

@app.get("/internal/users/{user_id}", response_model=UserProfileResponse, tags=["Internal APIs"], dependencies=[Depends(verify_internal_secret)])
async def get_user_info_internal(user_id: int, db: AsyncSession = Depends(get_db)):
    """API nội bộ: Lấy thông tin tài khoản theo ID cho Payment Service."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại.")
    return user


@app.post("/internal/users/{user_id}/deduct", response_model=DeductBalanceResponse, tags=["Internal APIs"], dependencies=[Depends(verify_internal_secret)])
async def deduct_balance(
    user_id: int,
    req: DeductBalanceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    API nội bộ: Trừ tiền khỏi tài khoản người dùng.
    - Áp dụng PESSIMISTIC LOCK (SELECT ... FOR UPDATE) chống Double-spending.
    - Đảm bảo tính bất biến (Idempotency Key qua transaction_id) chống trừ tiền trùng khi network retry.
    - Tự động ghi vết vào bảng account_transactions.
    """
    prev_balance, new_balance = await deduct_user_balance(
        db=db,
        user_id=user_id,
        amount=req.amount,
        transaction_id=req.transaction_id,
        description=req.description
    )

    return {
        "success": True,
        "user_id": user_id,
        "deducted_amount": req.amount,
        "new_balance": new_balance,
        "message": f"Trừ thành công {req.amount:,.0f} VNĐ cho giao dịch {req.transaction_id}."
    }


@app.post("/internal/users/{user_id}/refund", response_model=RefundBalanceResponse, tags=["Internal APIs"], dependencies=[Depends(verify_internal_secret)])
async def refund_balance(
    user_id: int,
    req: RefundBalanceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    API nội bộ: Hoàn trả tiền vào tài khoản người dùng khi bước gạch nợ học phí bị lỗi (Saga Compensation).
    - Có kiểm tra Idempotency chống cộng tiền 2 lần.
    - Ghi nhận giao dịch CREDIT vào lịch sử tài khoản.
    """
    new_balance = await refund_user_balance(
        db=db,
        user_id=user_id,
        amount=req.amount,
        transaction_id=req.transaction_id,
        reason=req.reason
    )

    return {
        "success": True,
        "user_id": user_id,
        "refunded_amount": req.amount,
        "new_balance": new_balance,
        "message": f"Hoàn tiền thành công {req.amount:,.0f} VNĐ cho giao dịch {req.transaction_id}."
    }


@app.post("/internal/users/reset-demo", tags=["Internal APIs"], dependencies=[Depends(verify_internal_secret)])
async def reset_demo_users(db: AsyncSession = Depends(get_db)):
    """API nội bộ: Khôi phục số dư ban đầu cho các tài khoản demo để chạy test tự động lặp lại."""
    from sqlalchemy import update
    from decimal import Decimal
    await db.execute(update(User).where(User.username == "nguyenvana").values(balance=Decimal("20000000.00")))
    await db.execute(update(User).where(User.username == "tranthib").values(balance=Decimal("15000000.00")))
    await db.execute(update(User).where(User.username == "lethanhc").values(balance=Decimal("5000000.00")))
    await db.commit()
    return {"status": "ok", "message": "Đã khôi phục số dư tài khoản demo."}

