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
            Student(student_code="524H0001", full_name="Nguyễn Văn An", class_name="24050301", major="Kỹ thuật phần mềm", email="524H0001@student.tdtu.edu.vn"),
            Student(student_code="524H0002", full_name="Trần Thị Mai", class_name="24050201", major="Khoa học máy tính", email="524H0002@student.tdtu.edu.vn"),
            Student(student_code="524H0003", full_name="Lê Hoàng Nam", class_name="24050401", major="Mạng máy tính & TTTT", email="524H0003@student.tdtu.edu.vn"),
            Student(student_code="524H0004", full_name="Phạm Minh Đức", class_name="24050101", major="Hệ thống thông tin", email="524H0004@student.tdtu.edu.vn"),
            Student(student_code="524H0005", full_name="Đỗ Gia Bảo", class_name="24050301", major="Kỹ thuật phần mềm", email="524H0005@student.tdtu.edu.vn"),
            Student(student_code="524H0006", full_name="Hoàng Thị Lan", class_name="24050201", major="Khoa học máy tính", email="524H0006@student.tdtu.edu.vn"),
            Student(student_code="524H0007", full_name="Vũ Đình Trọng", class_name="24050501", major="An toàn thông tin", email="524H0007@student.tdtu.edu.vn"),
            Student(student_code="524H0008", full_name="Bùi Ngọc Ánh", class_name="24050601", major="Kỹ thuật dữ liệu", email="524H0008@student.tdtu.edu.vn"),
            Student(student_code="524H0009", full_name="Phan Quốc Huy", class_name="24050701", major="Trí tuệ nhân tạo", email="524H0009@student.tdtu.edu.vn"),
            Student(student_code="524H0010", full_name="Nguyễn Thùy Trang", class_name="24050801", major="Thiết kế đồ họa", email="524H0010@student.tdtu.edu.vn"),
            Student(student_code="524H0011", full_name="Đặng Minh Khang", class_name="24050901", major="Thương mại điện tử", email="524H0011@student.tdtu.edu.vn"),
            Student(student_code="524H0012", full_name="Trịnh Mỹ Duyên", class_name="24051001", major="Quản trị kinh doanh", email="524H0012@student.tdtu.edu.vn"),
            Student(student_code="524H0013", full_name="Huỳnh Nhật Minh", class_name="24050602", major="Khoa học dữ liệu", email="524H0013@student.tdtu.edu.vn"),
            Student(student_code="524H0014", full_name="Mai Phương Thảo", class_name="24051101", major="Ngôn ngữ Anh", email="524H0014@student.tdtu.edu.vn"),
            Student(student_code="524H0015", full_name="Lương Thế Vinh", class_name="24050401", major="Mạng máy tính", email="524H0015@student.tdtu.edu.vn"),
            Student(student_code="524H0016", full_name="Cao Thu Hà", class_name="24051201", major="Tài chính ngân hàng", email="524H0016@student.tdtu.edu.vn"),
            Student(student_code="524H0017", full_name="Tạ Quang Khải", class_name="24051301", major="Kỹ thuật điện tử", email="524H0017@student.tdtu.edu.vn"),
            Student(student_code="524H0018", full_name="Đoàn Yến Nhi", class_name="24051401", major="Kế toán kiểm toán", email="524H0018@student.tdtu.edu.vn"),
            Student(student_code="524H0019", full_name="Ngô Gia Khiêm", class_name="24051501", major="Luật kinh tế", email="524H0019@student.tdtu.edu.vn"),
            Student(student_code="524H0020", full_name="Chu Bảo Trâm", class_name="24051601", major="Marketing số", email="524H0020@student.tdtu.edu.vn"),
        ]

        for student in sample_students:
            res = await session.execute(select(Student).where(Student.student_code == student.student_code))
            existing_student = res.scalar_one_or_none()
            if not existing_student:
                session.add(student)
            else:
                existing_student.full_name = student.full_name
                existing_student.class_name = student.class_name
                existing_student.major = student.major
                existing_student.email = student.email

        await session.flush()

        # 2. Khoi tao danh sach hoa don hoc phi
        sample_invoices = [
            # Hoa don chua thanh toan
            TuitionInvoice(id=1, student_code="524H0001", semester="HK1/2026-2027", amount=Decimal("15000000.00"), status="UNPAID"),
            # Hoa don da thanh toan
            TuitionInvoice(id=2, student_code="524H0002", semester="HK1/2026-2027", amount=Decimal("12000000.00"), status="PAID", paid_at=datetime.utcnow(), paid_by_user="nguyenvana", transaction_ref="INIT_TX_PAID_002"),
            # Hoa don gia tri lon
            TuitionInvoice(id=3, student_code="524H0003", semester="HK1/2026-2027", amount=Decimal("50000000.00"), status="UNPAID"),
            
            # Cac hoa don hoc phi bo sung
            TuitionInvoice(id=4, student_code="524H0005", semester="HK1/2026-2027", amount=Decimal("14000000.00"), status="UNPAID"),
            TuitionInvoice(id=5, student_code="524H0006", semester="HK1/2026-2027", amount=Decimal("11500000.00"), status="UNPAID"),
            TuitionInvoice(id=6, student_code="524H0007", semester="HK1/2026-2027", amount=Decimal("16000000.00"), status="UNPAID"),
            TuitionInvoice(id=7, student_code="524H0008", semester="HK1/2026-2027", amount=Decimal("13200000.00"), status="UNPAID"),
            TuitionInvoice(id=8, student_code="524H0009", semester="HK1/2026-2027", amount=Decimal("15500000.00"), status="UNPAID"),
            TuitionInvoice(id=9, student_code="524H0010", semester="HK1/2026-2027", amount=Decimal("9800000.00"), status="UNPAID"),
            TuitionInvoice(id=10, student_code="524H0011", semester="HK1/2026-2027", amount=Decimal("8500000.00"), status="UNPAID"),
            TuitionInvoice(id=11, student_code="524H0012", semester="HK1/2026-2027", amount=Decimal("12500000.00"), status="UNPAID"),
            TuitionInvoice(id=12, student_code="524H0013", semester="HK1/2026-2027", amount=Decimal("7500000.00"), status="UNPAID"),
            TuitionInvoice(id=13, student_code="524H0014", semester="HK1/2026-2027", amount=Decimal("10200000.00"), status="UNPAID"),
            TuitionInvoice(id=14, student_code="524H0015", semester="HK1/2026-2027", amount=Decimal("6800000.00"), status="UNPAID"),
            TuitionInvoice(id=15, student_code="524H0016", semester="HK1/2026-2027", amount=Decimal("13000000.00"), status="UNPAID"),
            TuitionInvoice(id=16, student_code="524H0017", semester="HK1/2026-2027", amount=Decimal("5500000.00"), status="UNPAID"),
            TuitionInvoice(id=17, student_code="524H0018", semester="HK1/2026-2027", amount=Decimal("11000000.00"), status="UNPAID"),
            TuitionInvoice(id=18, student_code="524H0019", semester="HK1/2026-2027", amount=Decimal("8900000.00"), status="UNPAID"),
            TuitionInvoice(id=19, student_code="524H0020", semester="HK1/2026-2027", amount=Decimal("14500000.00"), status="UNPAID"),
        ]

        for inv in sample_invoices:
            res = await session.execute(select(TuitionInvoice).where(TuitionInvoice.id == inv.id))
            if not res.scalar_one_or_none():
                session.add(inv)

        await session.commit()
        print("[Tuition Service] Seed data created successfully")

if __name__ == "__main__":
    asyncio.run(seed_data())
