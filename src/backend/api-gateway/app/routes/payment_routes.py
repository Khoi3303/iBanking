from fastapi import APIRouter, Request, Depends, status
from fastapi.security import HTTPBearer
from app.config import settings
from app.proxy import forward_request
from app.schemas import InitiatePaymentRequest, ConfirmOtpRequest, CancelPaymentRequest

router = APIRouter(prefix="/api/payments", tags=["4. Payment & OTP Lifecycle"])
security = HTTPBearer()

@router.post(
    "/initiate",
    status_code=status.HTTP_201_CREATED,
    summary="Khởi tạo giao dịch đóng học phí và sinh mã OTP",
    dependencies=[Depends(security)]
)
async def initiate_payment(req: InitiatePaymentRequest, request: Request):
    """
    Chuyển tiếp yêu cầu khởi tạo thanh toán sang Payment Service:
    - Kiểm tra số dư và trạng thái nợ.
    - Sinh mã OTP 6 số (TTL 300s) và gửi email tự động.
    """
    target_url = f"{settings.PAYMENT_SERVICE_URL}/payments/initiate"
    return await forward_request(target_url, request)


@router.post(
    "/confirm",
    status_code=status.HTTP_200_OK,
    summary="Xác nhận mã OTP và hoàn tất thanh toán",
    dependencies=[Depends(security)]
)
async def confirm_payment(req: ConfirmOtpRequest, request: Request):
    """
    Chuyển tiếp yêu cầu xác thực OTP sang Payment Service:
    - Xác thực và tiêu thụ OTP (chỉ dùng 1 lần).
    - Thực thi Saga phân tán: Trừ tiền + Gạch nợ + Tự động bồi hoàn nếu xung đột.
    """
    target_url = f"{settings.PAYMENT_SERVICE_URL}/payments/confirm"
    return await forward_request(target_url, request)


@router.post(
    "/cancel",
    status_code=status.HTTP_200_OK,
    summary="Hủy giao dịch tại Modal OTP và vô hiệu hóa mã OTP",
    dependencies=[Depends(security)]
)
async def cancel_payment(req: CancelPaymentRequest, request: Request):
    """
    Chuyển tiếp yêu cầu hủy phiên giao dịch sang Payment Service:
    - Hủy bỏ và xóa mã OTP trong Redis.
    - Cập nhật trạng thái giao dịch sang CANCELLED.
    """
    target_url = f"{settings.PAYMENT_SERVICE_URL}/payments/cancel"
    return await forward_request(target_url, request)


@router.get(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết trạng thái một giao dịch",
    dependencies=[Depends(security)]
)
async def get_transaction(transaction_id: str, request: Request):
    """
    Chuyển tiếp yêu cầu tra cứu chi tiết giao dịch sang Payment Service.
    """
    target_url = f"{settings.PAYMENT_SERVICE_URL}/payments/transactions/{transaction_id}"
    return await forward_request(target_url, request)


@router.get(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="Xem lịch sử các giao dịch thanh toán học phí",
    dependencies=[Depends(security)]
)
async def get_payment_history(request: Request, limit: int = 50):
    """
    Chuyển tiếp yêu cầu lấy lịch sử thanh toán học phí sang Payment Service.
    """
    target_url = f"{settings.PAYMENT_SERVICE_URL}/payments/history"
    return await forward_request(target_url, request)
