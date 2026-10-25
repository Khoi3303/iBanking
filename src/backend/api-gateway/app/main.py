from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import (
    auth_routes,
    user_routes,
    tuition_routes,
    payment_routes
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quản lý vòng đời API Gateway:
    - Khởi tạo Http Connection Pool Singleton (tối đa 200 connections, 50 keepalive).
    - Tối ưu hiệu năng và ngăn ngừa cạn kiệt socket khi chạy Concurrency Stress Test.
    """
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)
    app.state.http_client = httpx.AsyncClient(limits=limits, timeout=15.0)
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="""
    ## Phân hệ Đóng học phí iBanking - Trường Đại học Tôn Đức Thắng (TDTU)
    **Môn:** Kiến Trúc Hướng Dịch Vụ (CS504070 - SOA)

    Cổng API Gateway tập trung cung cấp các chức năng:
    * **1. Authentication:** Đăng nhập và xác thực JWT Bearer Token.
    * **2. User Profile:** Xem thông tin cá nhân, số dư khả dụng và lịch sử biến động tài khoản.
    * **3. Tuition Management:** Tra cứu sinh viên TDTU và các khoản nợ học phí theo MSSV.
    * **4. Payment Lifecycle:** Khởi tạo thanh toán, sinh mã OTP 5 phút và xác thực thanh toán Saga.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Cấu hình CORS chặt chẽ theo Origin cho Web Frontend
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Đăng ký các Router nghiệp vụ
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(tuition_routes.router)
app.include_router(payment_routes.router)

@app.get("/health", tags=["System Health"])
async def health_check():
    """Kiểm tra sức khỏe hệ thống API Gateway."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "routing": {
            "user_service": settings.USER_SERVICE_URL,
            "tuition_service": settings.TUITION_SERVICE_URL,
            "payment_service": settings.PAYMENT_SERVICE_URL
        }
    }

@app.get("/", tags=["System Health"])
async def root():
    """Trang chủ API Gateway."""
    return {
        "message": "Chào mừng đến với iBanking API Gateway (TDTU SOA Project)",
        "docs_url": "/docs"
    }


