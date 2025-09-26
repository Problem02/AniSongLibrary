import os
from pydantic import BaseModel

class Settings(BaseModel):
    service_name: str = os.getenv("SERVICE_NAME", "library")
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "https://auth.anisong.local")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "anisong.api")
    jwt_ttl_minutes: int = int(os.getenv("JWT_TTL_MINUTES", "20"))

settings = Settings()