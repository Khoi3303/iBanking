from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "iBanking Payment & Transaction Service"
    PORT: int = 8003
    HOST: str = "0.0.0.0"

    # MySQL Configuration (Dedicated Service Account - Data Ownership)
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "ibanking_payment_app"
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str = "ibanking_payment_db"

    # OTP Business Rules (theo đề bài)
    OTP_EXPIRE_SECONDS: int = 300  # Hiệu lực tối đa 5 phút
    OTP_LENGTH: int = 6

    # Redis Configuration (Distributed Lock & OTP Cache)
    REDIS_URL: str = "redis://redis:6379/0"

    # Internal Microservices Endpoints & Security (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    INTERNAL_API_KEY: str
    USER_SERVICE_URL: str = "http://user-service:8001"
    TUITION_SERVICE_URL: str = "http://tuition-service:8002"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8004"

    # JWT Config (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
