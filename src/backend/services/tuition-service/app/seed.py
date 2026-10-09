import asyncio
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select
from app.database import AsyncSessionLocal, engine, Base
from app.models import Student, TuitionInvoice

async def seed_data():
    """Khởi tạo dữ liệu mẫu chuẩn TDTU cho Tuition Service phục vụ demo & chấm điểm."""
    async with AsyncSessionLocal() as session:
        # 1. Thêm danh sách sinh viên
        sample_students = [
            Student(
                student_code="524H0001",
                full_name="Nguyễn Văn An",
                class_name="24050301",
                major="Kỹ thuật phần mềm",
                email="524H0001@student.tdtu.edu.vn"
            ),
            Student(
                student_code="524H0002",
                full_name="Trần Thị Mai",
                class_name="24050201",
                major="Khoa học máy tính",
                email="524H0002@student.tdtu.edu.vn"
            ),
            Student(
                student_code="524H0003",
                full_name="Lê Hoàng Nam",
                class_name="24050401",
                major="Mạng máy tính & TTTT",
                email="524H0003@student.tdtu.edu.vn"
            ),
            Student(
                student_code="524H0004",
                full_name="Phạm Minh Đức",
                class_name="24050101",
                major="Hệ thống thông tin",
                email="524H0004@student.tdtu.edu.vn"
            ),
        ]

        for student in sample_students:
            res = await session.execute(select(Student).where(Student.student_code == student.student_code))
            if not res.scalar_one_or_none():
                session.add(student)

        await session.flush()

        # 2. Thêm các hóa đơn học phí tương ứng với các kịch bản kiểm thử
        sample_invoices = [
            # SV 1: Nợ 15,000,000 (UNPAID) -> Demo đóng tiền thành công & Test Concurrency Race Condition
            TuitionInvoice(
                id=1,
                student_code="524H0001",
                semester="HK1/2026-2027",
                amount=Decimal("15000000.00"),
                status="UNPAID"
            ),
            # SV 2: Đã thanh toán 12,000,000 (PAID) -> Demo tra cứu ra nhưng nút thanh toán bị vô hiệu hóa
            TuitionInvoice(
                id=2,
                student_code="524H0002",
                semester="HK1/2026-2027",
                amount=Decimal("12000000.00"),
                status="PAID",
                paid_at=datetime.utcnow(),
                paid_by_user="nguyenvana",
                transaction_ref="INIT_TX_PAID_002"
            ),
            # SV 3: Nợ 50,000,000 (UNPAID) -> Demo trường hợp số dư tài khoản người nộp không đủ
            TuitionInvoice(
                id=3,
                student_code="524H0003",
                semester="HK1/2026-2027",
                amount=Decimal("50000000.00"),
                status="UNPAID"
            ),
            # SV 4: Không có hóa đơn -> Test edge case sinh viên chưa có nợ
        ]

        for inv in sample_invoices:
            res = await session.execute(select(TuitionInvoice).where(TuitionInvoice.id == inv.id))
            if not res.scalar_one_or_none():
                session.add(inv)

        await session.commit()
        print(">>> [TDTU Tuition Service] Seed data created successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
