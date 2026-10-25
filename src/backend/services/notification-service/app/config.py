from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "iBanking Notification Service"
    PORT: int = 8004
    HOST: str = "0.0.0.0"

    # Khóa xác thực API nội bộ (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    INTERNAL_API_KEY: str

    # SMTP Configuration (Cấu hình gửi email thông báo OTP và biên nhận)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@ibanking.tdtu.edu.vn"
    SMTP_FROM_NAME: str = "iBanking TDTU Support"
    USE_TLS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
