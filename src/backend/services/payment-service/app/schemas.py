from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional
from datetime import datetime

class InitiatePaymentRequest(BaseModel):
    student_code: str = Field(..., description="MSSV sinh viên cần đóng học phí")
    amount: Decimal = Field(..., gt=0, description="Số tiền cần đóng (toàn bộ khoản học phí)")
    invoice_id: Optional[int] = Field(None, description="Khóa chính ID của hóa đơn")

class InitiatePaymentResponse(BaseModel):
    transaction_id: str
    status: str
    student_code: str
    student_name: str
    semester: str
    amount: Decimal
    expires_in_seconds: int = 300
    user_email: str
    message: str

class ConfirmOtpRequest(BaseModel):
    transaction_id: str = Field(..., description="Mã giao dịch UUID")
    otp_code: str = Field(..., min_length=6, max_length=6, description="Mã OTP 6 số nhận qua Email")

class ConfirmOtpResponse(BaseModel):
    success: bool
    transaction_id: str
    status: str
    student_code: str
    student_name: str
    semester: str
    amount: Decimal
    completed_at: datetime
    message: str

class TransactionResponse(BaseModel):
    id: str
    user_id: int
    username: str
    student_code: str
    student_name: str
    semester: str
    amount: Decimal
    status: str
    failure_reason: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CancelPaymentRequest(BaseModel):
    transaction_id: str = Field(..., description="Mã giao dịch UUID cần hủy")

class CancelPaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    status: str
    message: str

