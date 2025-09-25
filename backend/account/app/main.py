# app/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.session import SessionLocal
from app.core.bootstrap import ensure_admin_user
from app.api.auth import router as auth_router
from app.api.user import router as user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup -----------------------------------------------------------
    enabled = os.getenv("ENABLE_ADMIN_SEED", "false").lower() in ("1", "true", "yes")
    env = os.getenv("ENV", "development").lower()

    # Hard block in production even if someone flips the flag
    if env in ("prod", "production") and enabled:
        raise RuntimeError("Refusing to seed admin in production. Remove ENABLE_ADMIN_SEED.")

    if enabled:
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")
        if not email or not password:
            print("ENABLE_ADMIN_SEED is true but ADMIN_EMAIL or ADMIN_PASSWORD is missing; skipping.")
        else:
            display_name = os.getenv("ADMIN_DISPLAY_NAME", "Admin")
            db = SessionLocal()
            try:
                ensure_admin_user(db, email=email, password=password, display_name=display_name)
                print("Admin seed ensured.")
            finally:
                db.close()

    yield  # ---- shutdown (nothing to do) -----------------------------------

app = FastAPI(title="account-service", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(user_router)
