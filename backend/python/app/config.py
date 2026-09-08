import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Paths
APP_DIR = Path(__file__).resolve().parent
PYTHON_BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = PYTHON_BACKEND_DIR.parent.parent

# Database location: check if accident_system.db exists in python dir or root backend dir
if (PYTHON_BACKEND_DIR / "accident_system.db").exists():
    DB_FILE = PYTHON_BACKEND_DIR / "accident_system.db"
elif (PROJECT_ROOT / "backend" / "accident_system.db").exists():
    DB_FILE = PROJECT_ROOT / "backend" / "accident_system.db"
else:
    DB_FILE = PYTHON_BACKEND_DIR / "accident_system.db"

DEFAULT_DATABASE_URL = f"sqlite:///{DB_FILE.as_posix()}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Government Accident Detection System"
    API_V1_STR: str = ""
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "gov_accident_detection_secure_secret_key_2026_xyz")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5500,http://localhost:3000"
    )
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        DEFAULT_DATABASE_URL
    )
    
    # Twilio (SMS Alerts)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Firebase Cloud Messaging
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

    # SMTP Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@emergency-response.gov.in")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Government Emergency Portal")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "True").lower() in ("true", "1", "yes")

    # Dev Modes
    VIRTUAL_SMS_LOG_ENABLED: bool = True
    VIRTUAL_EMAIL_LOG_ENABLED: bool = True
    DEV_SHOW_OTP: bool = os.getenv("DEV_SHOW_OTP", "True").lower() in ("true", "1", "yes")
    
    class Config:
        case_sensitive = True

settings = Settings()
