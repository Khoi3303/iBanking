from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "TDTU Tuition Service"
    PORT: int = 8002
    HOST: str = "0.0.0.0"

    # MySQL Configuration (Dedicated Service Account - Data Ownership)
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "ibanking_tuition_app"
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str = "tdtu_tuition_db"

    # Khóa xác thực API nội bộ (Fail-fast: Bắt buộc cung cấp qua biến môi trường)
    INTERNAL_API_KEY: str

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
