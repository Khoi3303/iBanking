from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Student(Base):
    """Thông tin sinh viên TDTU."""
    __tablename__ = "students"

    student_code = Column(String(20), primary_key=True, index=True) # MSSV, vd: 52100888
    full_name = Column(String(100), nullable=False)
    class_name = Column(String(50), nullable=False)
    major = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("TuitionInvoice", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student(mssv='{self.student_code}', name='{self.full_name}')>"


class TuitionInvoice(Base):
    """Khoản thu học phí sinh viên theo học kỳ."""
    __tablename__ = "tuition_invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_code = Column(String(20), ForeignKey("students.student_code", ondelete="CASCADE"), nullable=False, index=True)
    semester = Column(String(50), nullable=False)           # vd: 'HK1/2026-2027'
    amount = Column(Numeric(15, 2), nullable=False)         # Số tiền cần đóng
    status = Column(String(20), nullable=False, default="UNPAID") # 'UNPAID', 'PAID'
    paid_at = Column(DateTime, nullable=True)
    paid_by_user = Column(String(50), nullable=True)        # username người đã đóng
    transaction_ref = Column(String(100), nullable=True)    # transaction_id
    version = Column(Integer, nullable=False, default=1)    # Dùng cho Optimistic locking

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="invoices")

    __table_args__ = (
        UniqueConstraint('student_code', 'semester', name='uq_student_semester'),
        CheckConstraint('amount > 0', name='chk_positive_tuition'),
    )

    def __repr__(self):
        return f"<TuitionInvoice(id={self.id}, mssv='{self.student_code}', amount={self.amount}, status='{self.status}')>"
