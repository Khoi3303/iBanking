from fastapi import APIRouter, Request, Depends, status
from fastapi.security import HTTPBearer
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
    """
    target_url = f"{settings.TUITION_SERVICE_URL}/tuition/students/{student_code.strip()}"
    return await forward_request(target_url, request)
