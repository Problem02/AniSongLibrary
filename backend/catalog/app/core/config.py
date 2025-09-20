import os
from pydantic import BaseModel

class Settings(BaseModel):
    service_name: str = os.getenv("SERVICE_NAME", "catalog")
    database_url: str = os.getenv("DATABASE_URL", "")

settings = Settings()