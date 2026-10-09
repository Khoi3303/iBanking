from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal
from typing import Optional

class SendOtpEmailRequest(BaseModel):
    to_email: EmailStr = Field(..., description="Email người nhận hợp lệ")
    recipient_name: str = Field(..., min_length=1, description="Tên người nhận")
    otp_code: str = Field(..., min_length=6, max_length=6, description="Mã OTP 6 số")
    student_code: Optional[str] = Field(None, description="MSSV sinh viên")
    student_name: str = Field(..., min_length=1, description="Tên sinh viên đóng học phí")
    amount: Decimal = Field(..., gt=0, description="Số tiền thanh toán (phải lớn hơn 0)")
    expires_minutes: int = Field(5, ge=1, le=60, description="Số phút có hiệu lực")

class SendReceiptEmailRequest(BaseModel):
    to_email: EmailStr = Field(..., description="Email người nhận hợp lệ")
    recipient_name: str = Field(..., min_length=1, description="Tên người nhận")
    transaction_id: str = Field(..., min_length=1, description="Mã giao dịch UUID")
    student_code: str = Field(..., min_length=1, description="MSSV")
    student_name: str = Field(..., min_length=1, description="Tên sinh viên")
    amount: Decimal = Field(..., gt=0, description="Số tiền học phí đã đóng")
    completed_at: str = Field(..., description="Thời gian hoàn tất giao dịch")

class SendFailureRefundEmailRequest(BaseModel):
    to_email: EmailStr = Field(..., description="Email người nhận hợp lệ")
    recipient_name: str = Field(..., min_length=1, description="Tên người nhận")
    transaction_id: str = Field(..., min_length=1, description="Mã giao dịch UUID")
    student_code: str = Field(..., min_length=1, description="MSSV")
    amount: Decimal = Field(..., gt=0, description="Số tiền hoàn lại")
    reason: str = Field(..., min_length=1, description="Lý do giao dịch thất bại và hoàn tiền")

class EmailResponse(BaseModel):
    success: bool
    message: str
