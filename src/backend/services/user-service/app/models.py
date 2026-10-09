from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    balance = Column(Numeric(15, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ràng buộc cơ sở dữ liệu: Số dư tài khoản không bao giờ được âm
    __table_args__ = (
        CheckConstraint('balance >= 0', name='chk_positive_balance'),
    )

    # Quan hệ với lịch sử biến động số dư
    transactions = relationship("AccountTransaction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', balance={self.balance})>"


class AccountTransaction(Base):
    """Lịch sử biến động số dư / giao dịch tài khoản iBanking của người dùng."""
    __tablename__ = "account_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(String(10), nullable=False)  # 'DEBIT' (trừ tiền) hoặc 'CREDIT' (hoàn/nạp tiền)
    balance_after = Column(Numeric(15, 2), nullable=False)
    reference_id = Column(String(100), nullable=False)     # ID giao dịch thanh toán (transaction_id)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="transactions")

    # Idempotency constraint: Cùng 1 giao dịch và cùng 1 loại (DEBIT/CREDIT) chỉ ghi 1 lần duy nhất
    __table_args__ = (
        UniqueConstraint('user_id', 'reference_id', 'transaction_type', name='uq_user_ref_type'),
    )

    def __repr__(self):
        return f"<AccountTransaction(id={self.id}, user_id={self.user_id}, type={self.transaction_type}, amount={self.amount})>"
