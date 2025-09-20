from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "service": settings.service_name}

class AnimeOut(BaseModel):
    id: str
    title_en: str | None = None
    title_jp: str | None = None
    season: str | None = None
    year: int | None = None
    cover_image_url: str | None = None

# Stub endpoint: replace with DB lookup
@router.get("/anime/{anime_id}", response_model=AnimeOut)
async def get_anime(anime_id: str):
    return AnimeOut(id=anime_id, title_en="Stub Anime")