from fastapi import APIRouter
from pydantic import BaseModel
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

router = APIRouter()

class LoginReq(BaseModel):
    email: str
    password: str

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "service": settings.service_name}

@router.post("/auth/login")
async def login(body: LoginReq):
    # TODO: replace with real user lookup & password check
    payload = {
        "sub": body.email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "scope": "user",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"accessToken": token}

@router.get("/me")
async def me():
    # TODO: read user from token; stub for now
    return {"id": "stub-user", "email": "stub@example.com", "displayName": "Stub"}