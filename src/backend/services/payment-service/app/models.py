import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Transaction(Base):
    """Bảng lưu trữ toàn bộ các giao dịch thanh toán học phí iBanking."""
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(50), nullable=False)
    user_email = Column(String(100), nullable=False)
    student_code = Column(String(20), nullable=False, index=True)
    student_name = Column(String(100), nullable=False)
    invoice_id = Column(Integer, nullable=True)
    semester = Column(String(50), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    idempotency_key = Column(String(64), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="PENDING_OTP", index=True) # PENDING_OTP, PROCESSING, SUCCESS, FAILED, CANCELLED, EXPIRED
    failure_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    otp = relationship("OtpToken", back_populates="transaction", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction(id='{self.id}', user_id={self.user_id}, student='{self.student_code}', status='{self.status}')>"


class OtpToken(Base):
    """Lưu trữ vết mã OTP trong Database phục vụ kiểm toán (Audit Log)."""
    __tablename__ = "otp_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True)
    otp_code = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="otp")

    def __repr__(self):
        return f"<OtpToken(tx='{self.transaction_id}', code='{self.otp_code}', is_used={self.is_used})>"
