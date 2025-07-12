from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, Field, AnyHttpUrl, PostgresDsn
from functools import lru_cache
from typing_extensions import Self

class Settings(BaseSettings):
    PROJECT_NAME: str = "myapp"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(False, env="DEBUG")
    API_PREFIX: str = "/api"
    ALLOW_ORIGINS: list[AnyHttpUrl | str] = ["*"]
    db_url: PostgresDsn = Field(..., alias="DATABASE_URL")
    secret_key: str     = Field(..., alias="SECRET_KEY")
    algorithm: str      = Field("HS256", alias="ALGORITHM")

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "ducdatcuong@gmail.com"
    SMTP_PASSWORD: str = "mfkcncruqgfisbas"

    EMAIL_FROM: EmailStr = "ducdatcuong@gmail.com"   # <- thêm dòng này
    EMAIL_FROM_NAME: str = "Quiz Game Support"        # (tuỳ chọn)
    
    OTP_TTL_MIN: int = 10          #  ←  thêm dòng này khớp code email_utils
    VERIFIED_TTL_MIN: int = 5

    # PayOS Configuration
    PAYOS_CLIENT_ID: str = Field("", env="PAYOS_CLIENT_ID")
    PAYOS_API_KEY: str = Field("", env="PAYOS_API_KEY")
    PAYOS_CHECKSUM_KEY: str = Field("", env="PAYOS_CHECKSUM_KEY")
    PAYOS_SANDBOX: bool = Field(True, env="PAYOS_SANDBOX")

    # Application URLs
    BASE_URL: str = Field("http://localhost:8000", env="BASE_URL")
   
    @property
    def PAYMENT_SUCCESS_URL(self) -> str:
        """URL để PayOS redirect khi thanh toán thành công"""
        return f"{self.BASE_URL}/api/payment/success"
    
    @property
    def PAYMENT_CANCEL_URL(self) -> str:
        """URL để PayOS redirect khi hủy thanh toán"""
        return f"{self.BASE_URL}/api/payment/cancel"
    
    @property
    def WEBHOOK_URL(self) -> str:
        """URL để PayOS gửi webhook"""
        return f"{self.BASE_URL}/api/payment/webhook"
    
    def validate_payos_config(self) -> bool:
        """Kiểm tra xem PayOS config đã đầy đủ chưa"""
        required_config = [self.PAYOS_CLIENT_ID, self.PAYOS_API_KEY, self.PAYOS_CHECKSUM_KEY]

        if not all(required_config):
            missing = []
            if not self.PAYOS_CLIENT_ID:
                missing.append("PAYOS_CLIENT_ID")
            if not self.PAYOS_API_KEY:
                missing.append("PAYOS_API_KEY") 
            if not self.PAYOS_CHECKSUM_KEY:
                missing.append("PAYOS_CHECKSUM_KEY")
            
            raise ValueError(f"Thiếu PAYOS config: {', '.join(missing)}")
        
        return True
        
    class Config:
        env_file=".env"
        env_file_encoding="utf-8"
        populate_by_name=True
        extra="ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
