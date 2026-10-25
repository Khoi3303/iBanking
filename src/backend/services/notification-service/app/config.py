from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    APP_NAME: str = "iBanking Notification Service"
    PORT: int = 8004
    HOST: str = "0.0.0.0"

    # Khóa xác thực API nội bộ (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    INTERNAL_API_KEY: str

    # SMTP Configuration
    # Hỗ trợ 2 chế độ:
    # 1. Dev/Demo: Mailpit (mặc định trong Docker Compose, host=mailpit, port=1025, không cần mật khẩu)
    # 2. Production: Gmail / External SMTP (bắt buộc cấu hình đầy đủ SMTP_USER và SMTP_PASSWORD)
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@ibanking.tdtu.edu.vn"
    SMTP_FROM_NAME: str = "iBanking TDTU Support"
    USE_TLS: bool = False

    @model_validator(mode="after")
    def validate_smtp_credentials(self):
        is_local_mock = self.SMTP_HOST.lower() in ("mailpit", "localhost", "127.0.0.1")
        if not is_local_mock:
            if not self.SMTP_USER or not self.SMTP_PASSWORD:
                raise ValueError(
                    f"External SMTP host '{self.SMTP_HOST}' requires SMTP_USER and SMTP_PASSWORD. "
                    "Please configure them in .env or switch to SMTP_HOST=mailpit for local demo testing."
                )
        return self

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
