from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "TDTU Tuition Service"
    PORT: int = 8002
    HOST: str = "0.0.0.0"

    # MySQL Configuration
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "rootpassword"
    MYSQL_DATABASE: str = "tdtu_tuition_db"

    # Khóa xác thực API nội bộ
    INTERNAL_API_KEY: str = "ibanking-internal-secret-token-2026"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
