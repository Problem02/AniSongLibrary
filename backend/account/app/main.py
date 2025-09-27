import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


# Base app
app = FastAPI(title="account-service", lifespan=lifespan)

# --- CORS setup --------------------------------------------------------------
# Prefer explicit dev origins. You can override with ALLOWED_ORIGINS env (comma-separated).
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    # e.g., ALLOWED_ORIGINS="http://localhost:5173,http://localhost:5174,https://my.dev.site"
    origins = [o.strip() for o in env_origins.split(",") if o.strip()]
else:
    origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # set True only if you use cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Authorization"],  # optional
    max_age=86400,
)

# Routers
app.include_router(auth_router)
app.include_router(user_router)
