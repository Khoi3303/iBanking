from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

class LoginRequest(BaseModel):
    username: str = Field(..., example="nguyenvana", description="Tên đăng nhập")
    password: str = Field(..., example="123456", description="Mật khẩu")

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

