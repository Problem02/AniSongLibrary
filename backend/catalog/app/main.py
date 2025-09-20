from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="catalog-service")
app.include_router(router)