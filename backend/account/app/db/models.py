from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

def uid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(String, primary_key=True)
    theme = Column(String, nullable=True)
    time_format = Column(String, nullable=True) # 12h/24h


class ExternalLink(Base):
    __tablename__ = "external_links"
    user_id = Column(String, primary_key=True)
    provider = Column(String, primary_key=True)
    provider_user_id = Column(String, nullable=False)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(String, nullable=True)