from datetime import datetime, timezone
import jwt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from argon2 import PasswordHasher

from app.db.session import SessionLocal
import app.db.models as m 
import app.db.schemas as s
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# --- deps --------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

ph = PasswordHasher()


# --- helpers -----------------------------------------------------------------

def _hash_password(pwd: str) -> str:
    return ph.hash(pwd)

def _verify_password(pwd: str, pwd_hash: str) -> bool:
    try:
        return ph.verify(pwd_hash, pwd)
    except Exception:
        return False

def _create_access_token(*, sub: str, role: str) -> str:
    now = int(datetime.now(tz=timezone.utc).timestamp())
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + settings.jwt_ttl_minutes * 60,
        "sub": sub,
        "role": role,
        "scope": "openid profile",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


# --- routes ------------------------------------------------------------------

@router.post("/register", response_model=s.UserPublic, status_code=201)
def register(payload: s.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()

    existing = db.query(m.User).filter(m.User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="email_in_use")

    user = m.User(
        email=email,
        password_hash=_hash_password(payload.password),
        display_name=payload.display_name or "",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Handles the rare race where two requests bypass the existence check
        raise HTTPException(status_code=409, detail="email_in_use")
    db.refresh(user)

    return s.UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )

@router.post("/login", response_model=s.TokenResponse)
def login(payload: s.UserLogin, db: Session = Depends(get_db)):
    user = db.query(m.User).filter(m.User.email == payload.email.lower()).first()
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    # Transparently upgrade hash if params changed
    try:
        if ph.check_needs_rehash(user.password_hash):
            user.password_hash = _hash_password(payload.password)
    except Exception:
        pass

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_access_token(sub=str(user.id), role=user.role)
    return s.TokenResponse(access_token=token)
