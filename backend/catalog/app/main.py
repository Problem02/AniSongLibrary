from fastapi import FastAPI
from app.api.anime import router as anime_router
from app.api.songs import router as song_router

app = FastAPI(title="catalog-service")
app.include_router(anime_router, prefix="/api")
app.include_router(song_router, prefix="/api")