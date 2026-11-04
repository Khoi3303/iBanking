import json
import httpx
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from jose import jwt, JWTError

from app.config import settings
from app.proxy import forward_request
from app.schemas import StudentInquiryResponse

router = APIRouter(prefix="/api/tuition", tags=["3. TDTU Tuition Management"])
security = HTTPBearer()

@router.get(
    "/students/{student_code}",
    response_model=StudentInquiryResponse,
    status_code=status.HTTP_200_OK,
    summary="Tra cứu thông tin sinh viên và học phí cần đóng theo MSSV",
    dependencies=[Depends(security)]
)
async def get_student_tuition(student_code: str, request: Request):
    """
    Chuyển tiếp yêu cầu tra cứu thông tin sinh viên và công nợ học phí sang TDTU Tuition Service.
    Nếu học phí đang ở trạng thái UNPAID, Gateway kiểm tra chéo với Payment Service
    xem có phiên giao dịch PENDING_OTP của người dùng khác đang diễn ra hay không.
    Nếu có -> cập nhật can_pay = False và hiển thị thông báo trung tính (không lộ thông tin người khác).
    """
    target_url = f"{settings.TUITION_SERVICE_URL}/tuition/students/{student_code.strip()}"
    raw_response = await forward_request(target_url, request)

    if raw_response.status_code == 200:
        try:
            data = json.loads(raw_response.body.decode("utf-8"))
            if data.get("status") == "UNPAID" and data.get("can_pay") is True:
                curr_user_id = None
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                        sub = payload.get("sub")
                        if sub is not None:
                            curr_user_id = int(sub)
                    except JWTError:
                        pass

                client = getattr(request.app.state, "http_client", None)
                close_client = False
                if not client:
                    client = httpx.AsyncClient(timeout=5.0)
                    close_client = True

                try:
                    check_url = f"{settings.PAYMENT_SERVICE_URL}/payments/internal/pending-status/{student_code.strip()}"
                    res_check = await client.get(
                        check_url,
                        headers={"X-Internal-Secret": settings.INTERNAL_API_KEY}
                    )
                    if res_check.status_code == 200:
                        pending_info = res_check.json()
                        # Nếu có phiên pending của người khác -> vô hiệu hóa nút thanh toán
                        if pending_info.get("is_pending") and pending_info.get("user_id") != curr_user_id:
                            data["can_pay"] = False
                            data["message"] = "Khoản học phí này hiện tạm thời không thể thực hiện giao dịch."
                except Exception:
                    pass
                finally:
                    if close_client:
                        await client.aclose()

                return JSONResponse(status_code=200, content=data)
        except Exception:
            return raw_response

    return raw_response
