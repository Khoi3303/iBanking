from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, List
from datetime import datetime

class InvoiceDetail(BaseModel):
    id: int
    student_code: str
    semester: str
    amount: Decimal
    status: str
    paid_at: Optional[datetime] = None
    paid_by_user: Optional[str] = None
    transaction_ref: Optional[str] = None

    class Config:
        from_attributes = True

# Schema tra cứu học phí theo MSSV hiển thị lên giao diện iBanking (Mục 2.b của đề bài)
class StudentInquiryResponse(BaseModel):
    student_code: str = Field(..., description="Mã số sinh viên (MSSV)")
    student_name: str = Field(..., description="Họ và tên sinh viên")
    class_name: str
    major: str
    invoice_id: Optional[int] = Field(None, description="Khóa chính ID của hóa đơn học phí cần đóng")
    semester: Optional[str] = Field(None, description="Học kỳ cần đóng học phí")
    amount: Decimal = Field(..., description="Số tiền học phí cần thanh toán (toàn bộ, không đóng 1 phần)")
    status: str = Field(..., description="Trạng thái: UNPAID, PAID, hoặc NO_DEBT")
    can_pay: bool = Field(..., description="Khoản học phí có đủ điều kiện để đóng hay không (True nếu tồn tại và UNPAID)")
    message: str

    class Config:
        from_attributes = True

# Request gạch nợ học phí (gọi từ Payment Service)
class PayInvoiceRequest(BaseModel):
    invoice_id: Optional[int] = Field(None, description="Khóa chính ID hóa đơn (để khóa dòng độc quyền chính xác 100%)")
    student_code: str = Field(..., description="MSSV cần gạch nợ")
    semester: Optional[str] = Field(None, description="Học kỳ (mặc định lấy kỳ nợ gần nhất)")
    amount: Decimal = Field(..., gt=0, description="Số tiền đóng, phải khớp chính xác với số nợ")
    username: str = Field(..., description="Username của người thanh toán iBanking")
    transaction_id: str = Field(..., description="ID giao dịch thanh toán để truy vết và đảm bảo Idempotency")

class PayInvoiceResponse(BaseModel):
    success: bool
    invoice_id: int
    student_code: str
    semester: str
    amount: Decimal
    status: str
    paid_by_user: str
    paid_at: datetime
    transaction_ref: str
    message: str

# Request hủy gạch nợ (trong trường hợp rollback Saga nếu có)
class CancelInvoicePaymentRequest(BaseModel):
    invoice_id: Optional[int] = Field(None, description="ID hóa đơn")
    student_code: str
    transaction_id: str
    reason: Optional[str] = None

class CancelInvoicePaymentResponse(BaseModel):
    success: bool
    invoice_id: Optional[int] = None
    message: str
