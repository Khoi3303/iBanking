from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

class LoginRequest(BaseModel):
    username: str = Field(..., example="nguyenvana", description="Tên đăng nhập")
    password: str = Field(..., example="123456", description="Mật khẩu")

class RegisterRequest(BaseModel):
    username: str = Field(..., example="tranvanb", description="Tên đăng nhập")
    password: str = Field(..., example="123456", description="Mật khẩu")
    full_name: str = Field(..., example="Trần Văn B", description="Họ và tên")
    phone_number: str = Field(..., example="0912345678", description="Số điện thoại")
    email: str = Field(..., example="tranvanb@gmail.com", description="Email cá nhân")
    balance: Optional[Decimal] = Field(Decimal("0.00"), description="Số dư ban đầu (Mặc định: 0đ)")

class DepositRequest(BaseModel):
    amount: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("500000000.00"),
        example=10000000.00,
        description="Số tiền cần nạp, tối thiểu 1 VNĐ và tối đa 500,000,000 VNĐ"
    )
    description: Optional[str] = Field("Nạp tiền vào tài khoản iBanking", max_length=255, description="Mô tả nạp tiền")

class DepositResponse(BaseModel):
    success: bool
    user_id: int
    deposited_amount: Decimal
    new_balance: Decimal
    message: str

class UserProfileResponse(BaseModel):
    id: int
    username: str
    full_name: str
    phone_number: str
    email: str
    balance: Decimal
    created_at: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse

class StudentInquiryResponse(BaseModel):
    student_code: str
    student_name: str
    class_name: str
    major: str
    invoice_id: Optional[int] = None
    semester: Optional[str] = None
    amount: Decimal
    status: str
    can_pay: bool
    message: str

class InitiatePaymentRequest(BaseModel):
    student_code: str = Field(..., example="524H0001", description="MSSV sinh viên cần đóng học phí")
    amount: Decimal = Field(..., example=15000000.00, gt=0, description="Số tiền cần đóng")
    invoice_id: Optional[int] = Field(None, example=1, description="ID hóa đơn")

class ConfirmOtpRequest(BaseModel):
    transaction_id: str = Field(..., description="Mã giao dịch UUID")
    otp_code: str = Field(..., min_length=6, max_length=6, example="123456", description="Mã OTP 6 số nhận qua Email")

class CancelPaymentRequest(BaseModel):
    transaction_id: str = Field(..., description="Mã giao dịch UUID cần hủy")

