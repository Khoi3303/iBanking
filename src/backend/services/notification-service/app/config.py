from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "iBanking Notification Service"
    PORT: int = 8004
    HOST: str = "0.0.0.0"

    # Khóa xác thực API nội bộ
    INTERNAL_API_KEY: str = "ibanking-internal-secret-token-2026"

    # SMTP Configuration (Mặc định dùng Mailpit khi chạy Docker Compose)
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "support@ibanking.tdtu.edu.vn"
    SMTP_FROM_NAME: str = "iBanking TDTU Support"
    USE_TLS: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
