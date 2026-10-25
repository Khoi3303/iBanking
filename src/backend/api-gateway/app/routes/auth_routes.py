from fastapi import APIRouter, Request, status
from app.config import settings
from app.proxy import forward_request
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["1. Authentication & Security"])

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập tài khoản iBanking"
)
async def login(req: LoginRequest, request: Request):
    """
    Tiếp nhận thông tin đăng nhập và chuyển tiếp sang User Service.
    Trả về JWT Access Token và thông tin tài khoản (Họ tên, SĐT, Email, Số dư).
    """
    target_url = f"{settings.USER_SERVICE_URL}/auth/login"
    return await forward_request(target_url, request)



