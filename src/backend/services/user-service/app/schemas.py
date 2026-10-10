from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime

# Request body cho Login
class LoginRequest(BaseModel):
    username: str = Field(..., example="nguyenvana", description="Tên đăng nhập")
    password: str = Field(..., example="123456", description="Mật khẩu tài khoản")

# Request body cho Đăng ký tài khoản mới
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="nguyenvanb", description="Tên đăng nhập")
    password: str = Field(..., min_length=6, example="123456", description="Mật khẩu tài khoản")
    full_name: str = Field(..., min_length=2, max_length=100, example="Nguyễn Văn B", description="Họ và tên người dùng")
    phone_number: str = Field(..., min_length=9, max_length=20, example="0912345678", description="Số điện thoại")
    balance: Optional[Decimal] = Field(Decimal("0.00"), description="Số dư khởi tạo ban đầu (Mặc định: 0đ)")

# Request body cho nạp tiền vào tài khoản
class DepositRequest(BaseModel):
    amount: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("500000000.00"),
        example=10000000.00,
        description="Số tiền cần nạp, tối thiểu 1 VNĐ và tối đa 500,000,000 VNĐ"
    )
    description: Optional[str] = Field("Nạp tiền vào tài khoản iBanking", max_length=255, description="Mô tả giao dịch nạp tiền")

# Response khi nạp tiền thành công
class DepositResponse(BaseModel):
    success: bool
    user_id: int
    deposited_amount: Decimal
    new_balance: Decimal
    message: str

# DTO trả về thông tin người dùng
class UserProfileResponse(BaseModel):
    id: int
    username: str
    full_name: str
    phone_number: str
    email: EmailStr
    balance: Decimal = Field(..., description="Số dư khả dụng trong tài khoản iBanking")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# DTO trả về khi login thành công
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse

# Request body khi trừ tiền tài khoản (gọi từ Payment Service)
class DeductBalanceRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Số tiền cần trừ, phải lớn hơn 0")
    transaction_id: str = Field(..., description="ID giao dịch để kiểm tra và truy vết")
    description: Optional[str] = Field(None, description="Mô tả lý do trừ tiền")

# Response khi trừ tiền
class DeductBalanceResponse(BaseModel):
    success: bool
    user_id: int
    deducted_amount: Decimal
    new_balance: Decimal
    message: str

# Request body khi hoàn tiền (Saga Compensating Transaction)
class RefundBalanceRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Số tiền cần hoàn lại")
    transaction_id: str = Field(..., description="ID giao dịch ban đầu")
    reason: Optional[str] = Field(None, description="Lý do hoàn trả tiền")

class RefundBalanceResponse(BaseModel):
    success: bool
    user_id: int
    refunded_amount: Decimal
    new_balance: Decimal
    message: str

# DTO trả về lịch sử biến động số dư / giao dịch
class AccountTransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: Decimal
    transaction_type: str
    balance_after: Decimal
    reference_id: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
