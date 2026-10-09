from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "iBanking API Gateway"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # JWT Config
    JWT_SECRET_KEY: str = "ibanking-super-secret-key-tdtu-2026"
    JWT_ALGORITHM: str = "HS256"

    # Khóa bí mật giao tiếp nội bộ
    INTERNAL_API_KEY: str = "ibanking-internal-secret-token-2026"

    # Internal Microservices Endpoints
    USER_SERVICE_URL: str = "http://user-service:8001"
    TUITION_SERVICE_URL: str = "http://tuition-service:8002"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8003"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8004"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
