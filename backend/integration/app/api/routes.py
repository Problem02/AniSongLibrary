from fastapi import APIRouter
from pydantic import BaseModel
import httpx

router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "integration"}

class SyncReq(BaseModel):
    anilist_id: int

@router.post("/sync/anilist/anime/{anilist_id}")
async def sync_anilist_anime(anilist_id: int):
    # TODO: call AniList (GraphQL), map, then call Catalog admin upsert
    return {"status": "accepted", "anilistId": anilist_id}