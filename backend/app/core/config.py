import warnings
from pathlib import Path
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / '.env'
_INSECURE_SECRET_KEY = 'CHANGE-THIS-TO-A-STRONG-RANDOM-SECRET-KEY'

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding='utf-8', case_sensitive=True, extra='ignore')

    PROJECT_NAME: str = 'Ungozu R & D API'
    VERSION: str = '1.0.0'
    DEBUG: bool = False
    DATABASE_URL: str = 'mysql+pymysql://ungozu_rdp:CHANGE_ME@127.0.0.1:3306/ungozu_rdp'

    SECRET_KEY: str = _INSECURE_SECRET_KEY
    CREDENTIAL_ENCRYPTION_KEY: str = ''
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    FRONTEND_URL: str = 'http://localhost:3010'
    BACKEND_PUBLIC_URL: str = 'http://localhost:8010'
    MAIN_SITE_URL: str = 'https://iniakpothompson.com'
    CORS_ORIGINS: list[str] = ['http://localhost:3010']

    PAYMENT_ACTIVE_ENVIRONMENT: str = 'test'
    PAYSTACK_SECRET_KEY: str = ''
    PAYSTACK_PUBLIC_KEY: str = ''
    STRIPE_SECRET_KEY: str = ''
    STRIPE_PUBLISHABLE_KEY: str = ''
    STRIPE_WEBHOOK_SECRET: str = ''
    RDP_ALLOW_OUT_OF_WINDOW_APPLICATIONS: bool = False

    SMTP_HOST: str = ''
    SMTP_PORT: int = 465
    SMTP_USER: str = ''
    SMTP_PASS: str = ''
    SMTP_FROM: str = ''
    SMTP_USE_TLS: bool = True

    @property
    def smtp_from_address(self) -> str:
        return self.SMTP_FROM or self.SMTP_USER or 'no-reply@rdp.local'

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value

    @property
    def async_database_url(self) -> str:
        return self.DATABASE_URL.replace('mysql+pymysql://', 'mysql+aiomysql://', 1)

    @model_validator(mode='after')
    def validate_security(self):
        if not self.DEBUG:
            if self.SECRET_KEY == _INSECURE_SECRET_KEY:
                raise ValueError('SECRET_KEY must be changed in production')
            if len(self.SECRET_KEY) < 32:
                warnings.warn('SECRET_KEY should be at least 32 characters', UserWarning)
            if not (self.CREDENTIAL_ENCRYPTION_KEY or '').strip():
                warnings.warn('CREDENTIAL_ENCRYPTION_KEY is blank; SECRET_KEY fallback will encrypt payment credentials.', UserWarning)
        return self

settings = Settings()
