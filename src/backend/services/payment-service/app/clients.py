import httpx
from decimal import Decimal
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.config import settings

def _get_headers(correlation_id: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "X-Internal-Secret": settings.INTERNAL_API_KEY,
        "Content-Type": "application/json"
    }
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    return headers

class UserServiceClient:
    """Client giao tiếp với User & Account Service."""

    @staticmethod
    async def get_user(user_id: int, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{settings.USER_SERVICE_URL}/internal/users/{user_id}",
                    headers=_get_headers(correlation_id)
                )
                if resp.status_code == 404:
                    raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
                resp.raise_for_status()
                return resp.json()
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Không thể kết nối đến User Service: {str(e)}")

    @staticmethod
    async def deduct_balance(user_id: int, amount: Decimal, transaction_id: str, description: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "amount": float(amount),
            "transaction_id": transaction_id,
            "description": description
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{settings.USER_SERVICE_URL}/internal/users/{user_id}/deduct",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
                if resp.status_code != 200:
                    err_msg = resp.json().get("detail", "Lỗi trừ tiền tài khoản.")
                    raise HTTPException(status_code=resp.status_code, detail=err_msg)
                return resp.json()
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Không thể kết nối đến User Service: {str(e)}")

    @staticmethod
    async def refund_balance(user_id: int, amount: Decimal, transaction_id: str, reason: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "amount": float(amount),
            "transaction_id": transaction_id,
            "reason": reason
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{settings.USER_SERVICE_URL}/internal/users/{user_id}/refund",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
                return resp.json()
            except Exception as e:
                print(f"[Warning] Gọi hoàn tiền thất bại qua User Service: {e}")
                return {"success": False}


class TuitionServiceClient:
    """Client giao tiếp với TDTU Tuition Service."""

    @staticmethod
    async def get_student_tuition(student_code: str, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{settings.TUITION_SERVICE_URL}/tuition/students/{student_code}",
                    headers=_get_headers(correlation_id)
                )
                if resp.status_code == 404:
                    err_msg = resp.json().get("detail", "Không tìm thấy sinh viên.")
                    raise HTTPException(status_code=404, detail=err_msg)
                resp.raise_for_status()
                return resp.json()
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Không thể kết nối đến Tuition Service: {str(e)}")

    @staticmethod
    async def pay_invoice(
        student_code: str,
        amount: Decimal,
        username: str,
        transaction_id: str,
        invoice_id: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "invoice_id": invoice_id,
            "student_code": student_code,
            "amount": float(amount),
            "username": username,
            "transaction_id": transaction_id
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{settings.TUITION_SERVICE_URL}/internal/tuition/pay",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
                if resp.status_code != 200:
                    err_msg = resp.json().get("detail", "Lỗi gạch nợ học phí.")
                    raise HTTPException(status_code=resp.status_code, detail=err_msg)
                return resp.json()
            except httpx.RequestError as e:
                # Bắt lỗi Timeout hoặc Lỗi kết nối mạng ở Bước 2
                raise HTTPException(
                    status_code=504,
                    detail=f"Mất kết nối hoặc timeout tới Tuition Service: {str(e)}"
                )

    @staticmethod
    async def cancel_invoice(student_code: str, transaction_id: str, invoice_id: Optional[int] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Gọi API hoàn tác gạch nợ (Saga rollback an toàn khi bước 2 gặp sự cố timeout)."""
        payload = {
            "invoice_id": invoice_id,
            "student_code": student_code,
            "transaction_id": transaction_id
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{settings.TUITION_SERVICE_URL}/internal/tuition/cancel",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
                return resp.json()
            except Exception as e:
                print(f"[Warning] Gọi cancel tuition thất bại: {e}")
                return {"success": False}


class NotificationServiceClient:
    """Client gửi yêu cầu gửi Email sang Notification Service."""

    @staticmethod
    async def send_otp(to_email: str, recipient_name: str, otp_code: str, student_name: str, amount: Decimal, correlation_id: Optional[str] = None):
        payload = {
            "to_email": to_email,
            "recipient_name": recipient_name,
            "otp_code": otp_code,
            "student_name": student_name,
            "amount": float(amount),
            "expires_minutes": 5
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/notifications/send-otp",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
            except Exception as e:
                print(f"[Warning] Gửi email OTP thất bại qua Notification Service: {e}")

    @staticmethod
    async def send_receipt(to_email: str, recipient_name: str, transaction_id: str, student_code: str, student_name: str, amount: Decimal, completed_at: str, correlation_id: Optional[str] = None):
        payload = {
            "to_email": to_email,
            "recipient_name": recipient_name,
            "transaction_id": transaction_id,
            "student_code": student_code,
            "student_name": student_name,
            "amount": float(amount),
            "completed_at": completed_at
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/notifications/send-receipt",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
            except Exception as e:
                print(f"[Warning] Gửi email biên nhận thất bại: {e}")

    @staticmethod
    async def send_failure_refund(to_email: str, recipient_name: str, transaction_id: str, student_code: str, amount: Decimal, reason: str, correlation_id: Optional[str] = None):
        """Gửi email thông báo giao dịch thất bại và đã hoàn tiền vào tài khoản."""
        payload = {
            "to_email": to_email,
            "recipient_name": recipient_name,
            "transaction_id": transaction_id,
            "student_code": student_code,
            "amount": float(amount),
            "reason": reason
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/notifications/send-failure-refund",
                    json=payload,
                    headers=_get_headers(correlation_id)
                )
            except Exception as e:
                print(f"[Warning] Gửi email thông báo hoàn tiền thất bại: {e}")
