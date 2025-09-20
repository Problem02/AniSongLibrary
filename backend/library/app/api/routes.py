from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "service": settings.service_name}

class PutSongRating(BaseModel):
    score: int
    note: str | None = None

@router.put("/users/{user_id}/ratings/songs/{song_id}")
async def put_rating(user_id: str, song_id: str, body: PutSongRating):
    # TODO: persist; stub for now
    return {"userId": user_id, "songId": song_id, "score": body.score}