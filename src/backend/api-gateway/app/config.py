from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "iBanking API Gateway"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # JWT Config (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Khóa bí mật giao tiếp nội bộ (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    INTERNAL_API_KEY: str

    # Internal Microservices Endpoints
    USER_SERVICE_URL: str = "http://user-service:8001"
    TUITION_SERVICE_URL: str = "http://tuition-service:8002"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8003"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8004"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
