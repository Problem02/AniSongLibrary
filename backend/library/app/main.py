import os
from fastapi import FastAPI
from app.api.library import router as library_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="library-service")

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

app.include_router(library_router)