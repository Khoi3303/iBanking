from fastapi import APIRouter, Request, Depends, status
from fastapi.security import HTTPBearer
from app.config import settings
from app.proxy import forward_request
from app.schemas import UserProfileResponse

router = APIRouter(prefix="/api/users", tags=["2. User & Account Profile"])
security = HTTPBearer()

@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin tài khoản và số dư khả dụng",
    dependencies=[Depends(security)]
)
async def get_my_profile(request: Request):
    """
    Chuyển tiếp yêu cầu lấy thông tin cá nhân và số dư tài khoản của người dùng đang đăng nhập sang User Service.
    """
    target_url = f"{settings.USER_SERVICE_URL}/users/me"
    return await forward_request(target_url, request)


@router.get(
    "/me/transactions",
    status_code=status.HTTP_200_OK,
    summary="Xem lịch sử biến động số dư tài khoản",
    dependencies=[Depends(security)]
)
async def get_my_transactions(request: Request, limit: int = 50):
    """
    Chuyển tiếp yêu cầu xem lịch sử biến động số dư sang User Service.
    """
    target_url = f"{settings.USER_SERVICE_URL}/users/me/transactions"
    return await forward_request(target_url, request)


@router.post(
    "/me/deposit",
    status_code=status.HTTP_200_OK,
    summary="Nạp tiền vào tài khoản iBanking",
    dependencies=[Depends(security)]
)
async def deposit_money(request: Request):
    """
    Chuyển tiếp yêu cầu nạp tiền vào tài khoản iBanking sang User Service.
    """
    target_url = f"{settings.USER_SERVICE_URL}/users/me/deposit"
    return await forward_request(target_url, request)
