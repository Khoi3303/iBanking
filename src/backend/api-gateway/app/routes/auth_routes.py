from fastapi import APIRouter, Request, status
from app.config import settings
from app.proxy import forward_request
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

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


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản iBanking mới"
)
async def register(req: RegisterRequest, request: Request):
    """
    Đăng ký tài khoản mới và chuyển tiếp sang User Service.
    Tự động cấp JWT Access Token và đăng nhập ngay.
    """
    target_url = f"{settings.USER_SERVICE_URL}/auth/register"
    return await forward_request(target_url, request)


@router.get("/seed-demo", summary="Đồng bộ nạp tài khoản demo")
@router.post("/seed-demo", summary="Đồng bộ nạp tài khoản demo")
async def seed_demo(request: Request):
    """Chuyển tiếp lệnh đồng bộ tài khoản demo sang User Service."""
    target_url = f"{settings.USER_SERVICE_URL}/auth/seed-demo"
    return await forward_request(target_url, request)


