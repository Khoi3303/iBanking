from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime

# Request body cho Login
class LoginRequest(BaseModel):
    username: str = Field(..., example="nguyenvana", description="Tên đăng nhập")
    password: str = Field(..., example="123456", description="Mật khẩu tài khoản")

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
