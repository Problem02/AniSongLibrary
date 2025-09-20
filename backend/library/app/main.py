from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="library-service")
app.include_router(router)