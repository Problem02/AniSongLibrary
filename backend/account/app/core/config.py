import os
from pydantic import BaseModel


class Settings(BaseModel):
    service_name: str = os.getenv("SERVICE_NAME", "account")
    database_url: str = os.getenv("ACCOUNT_DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret")


settings = Settings()