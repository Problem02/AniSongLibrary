import uuid
import jwt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
import app.db.models as m
import app.db.schemas as s
from app.core.config import settings

router = APIRouter(prefix="/user", tags=["user"])


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

bearer = HTTPBearer(auto_error=False)


# --- helpers -----------------------------------------------------------------

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")
    token = credentials.credentials
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=60,  # tolerate small clock skew
        )
        return claims
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

def current_user(db: Session = Depends(get_db), claims: dict = Depends(require_auth)) -> m.User:
    try:
        uid = uuid.UUID(claims["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_subject")
    user = db.get(m.User, uid)
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")
    return user

def require_admin(claims: dict = Depends(require_auth)) -> dict:
    if claims.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="forbidden")
    return claims

def to_public(u: m.User) -> s.UserPublic:
    return s.UserPublic(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        avatar_url=u.avatar_url,
        role=u.role,
        created_at=u.created_at,
        updated_at=u.updated_at,
        last_login_at=u.last_login_at,
    )


# --- self-service routes -----------------------------------------------------

@router.get("/me", response_model=s.UserPublic)
def get_me(me: m.User = Depends(current_user)) -> s.UserPublic:
    return to_public(me)

@router.patch("/me", response_model=s.UserPublic)
def update_me(update: s.UserUpdate, db: Session = Depends(get_db), me: m.User = Depends(current_user)) -> s.UserPublic:
    if update.display_name is not None:
        me.display_name = update.display_name
    if update.avatar_url is not None:
        me.avatar_url = update.avatar_url
    db.add(me)
    db.commit()
    db.refresh(me)
    return to_public(me)

@router.delete("/me", status_code=204)
def delete_me(db: Session = Depends(get_db), me: m.User = Depends(current_user)):
    db.delete(me)
    db.commit()
    return


# --- admin routes ------------------------------------------------------------

@router.get("", response_model=list[s.UserPublic])
def list_users(db: Session = Depends(get_db), _claims: dict = Depends(require_admin)) -> list[s.UserPublic]:
    rows = db.query(m.User).order_by(m.User.created_at.desc()).all()
    return [to_public(u) for u in rows]

@router.get("/{user_id}", response_model=s.UserPublic)
def get_user_by_id(user_id: uuid.UUID, db: Session = Depends(get_db), _claims: dict = Depends(require_admin)) -> s.UserPublic:
    user = db.get(m.User, user_id)
    if not user:
        raise HTTPException(404, detail="not_found")
    return to_public(user)

@router.patch("/{user_id}", response_model=s.UserPublic)
def admin_update_user(user_id: uuid.UUID, update: s.UserUpdate, db: Session = Depends(get_db), _claims: dict = Depends(require_admin)) -> s.UserPublic:
    user = db.get(m.User, user_id)
    if not user:
        raise HTTPException(404, detail="not_found")
    if update.display_name is not None:
        user.display_name = update.display_name
    if update.avatar_url is not None:
        user.avatar_url = update.avatar_url
    db.add(user)
    db.commit()
    db.refresh(user)
    return to_public(user)

@router.delete("/{user_id}", status_code=204)
def admin_delete_user(user_id: uuid.UUID, db: Session = Depends(get_db), claims: dict = Depends(require_admin)):
    # Block self-deletion
    if claims.get("sub") == str(user_id):
        raise HTTPException(status_code=400, detail="cannot_delete_self")
    user = db.get(m.User, user_id)
    if not user:
        raise HTTPException(404, detail="not_found")
    db.delete(user)
    db.commit()
