from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

# --- Register/Login schemas --------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    

# --- User schemas ------------------------------------------------------------

class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: Optional[str] = None
    role: str
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
