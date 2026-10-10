import os
import asyncio
import logging
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.config import settings

# Cấu hình logging chuyên nghiệp
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("notification_service")

# Khởi tạo Jinja2 template loader
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

# Đăng ký Custom Jinja2 Filter: Định dạng tiền tệ Việt Nam (vd: 15.000.000 VND)
def format_currency_vnd(value) -> str:
    """Format tiền tệ theo chuẩn Việt Nam: 15.000.000 VND."""
    try:
        val = int(Decimal(str(value)))
        return f"{val:,} VND".replace(",", ".")
    except Exception:
        return f"{value} VND"

jinja_env.filters["currency"] = format_currency_vnd


async def send_email_async(to_email: str, subject: str, html_content: str, max_retries: int = 3) -> bool:
    """
    Gửi email bất đồng bộ qua SMTP với cơ chế:
    - Retry tự động 3 lần nếu gặp sự cố mạng tạm thời.
    - Ghi log chi tiết bằng module logging.
    - Không làm sập ứng dụng nếu SMTP server chưa sẵn sàng.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    msg["To"] = to_email

    part = MIMEText(html_content, "html", "utf-8")
    msg.attach(part)

    for attempt in range(1, max_retries + 1):
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER if settings.SMTP_USER else None,
                password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
                start_tls=settings.USE_TLS,
                timeout=25.0
            )
            logger.info(f"Đã gửi email thành công tới {to_email} (Lần thử {attempt}): '{subject}'")
            return True
        except Exception as e:
            logger.warning(f"Lần thử {attempt}/{max_retries} gửi email tới {to_email} thất bại: {str(e)}")
            if attempt < max_retries:
                await asyncio.sleep(1.5)
            else:
                logger.error(f"GỬI MAIL THẤT BẠI HOÀN TOÀN tới {to_email} sau {max_retries} lần thử: {str(e)}")
                return False


async def send_otp_email(
    to_email: str,
    recipient_name: str,
    otp_code: str,
    student_name: str,
    amount: Decimal,
    expires_minutes: int = 5,
    student_code: str = None
):
    """Sinh nội dung và gửi email mã OTP."""
    try:
        template = jinja_env.get_template("otp_email.html")
        html_content = template.render(
            recipient_name=recipient_name,
            otp_code=otp_code,
            student_name=student_name,
            student_code=student_code,
            amount=amount,
            expires_minutes=expires_minutes
        )
        subject = f"[{settings.SMTP_FROM_NAME}] Mã OTP xác thực đóng học phí: {otp_code}"
        await send_email_async(to_email, subject, html_content)
    except Exception as e:
        logger.error(f"Lỗi render/gửi OTP email cho {to_email}: {str(e)}")


async def send_receipt_email(
    to_email: str,
    recipient_name: str,
    transaction_id: str,
    student_code: str,
    student_name: str,
    amount: Decimal,
    completed_at: str
):
    """Sinh nội dung và gửi email biên nhận thanh toán học phí thành công."""
    try:
        template = jinja_env.get_template("receipt_email.html")
        html_content = template.render(
            recipient_name=recipient_name,
            transaction_id=transaction_id,
            student_code=student_code,
            student_name=student_name,
            amount=amount,
            completed_at=completed_at
        )
        subject = f"[{settings.SMTP_FROM_NAME}] Biên lai xác nhận thanh toán học phí thành công (MSSV: {student_code})"
        await send_email_async(to_email, subject, html_content)
    except Exception as e:
        logger.error(f"Lỗi render/gửi biên lai cho {to_email}: {str(e)}")


async def send_refund_email(
    to_email: str,
    recipient_name: str,
    transaction_id: str,
    student_code: str,
    amount: Decimal,
    reason: str
):
    """Sinh nội dung và gửi email thông báo giao dịch thất bại và hoàn tiền về ví."""
    try:
        template = jinja_env.get_template("refund_email.html")
        html_content = template.render(
            recipient_name=recipient_name,
            transaction_id=transaction_id,
            student_code=student_code,
            amount=amount,
            reason=reason
        )
        subject = f"[{settings.SMTP_FROM_NAME}] Thông báo hoàn tiền giao dịch học phí (MSSV: {student_code})"
        await send_email_async(to_email, subject, html_content)
    except Exception as e:
        logger.error(f"Lỗi render/gửi email hoàn tiền cho {to_email}: {str(e)}")
