from fastapi import FastAPI
from app.api.library import router as library_router

app = FastAPI(title="library-service")
app.include_router(library_router)