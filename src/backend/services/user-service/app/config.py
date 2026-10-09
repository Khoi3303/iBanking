from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "iBanking User & Account Service"
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # MySQL Configuration
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "rootpassword"
    MYSQL_DATABASE: str = "ibanking_user_db"

    # JWT Config
    JWT_SECRET_KEY: str = "ibanking-super-secret-key-tdtu-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Khóa xác thực API nội bộ (chỉ cho phép các Microservice nội bộ gọi)
    INTERNAL_API_KEY: str = "ibanking-internal-secret-token-2026"

    @property
    def DATABASE_URL(self) -> str:
        # Async URL cho SQLAlchemy aiomysql
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
