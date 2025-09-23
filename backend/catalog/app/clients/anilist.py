# Lightweight AniList GraphQL client (httpx)
from __future__ import annotations
import httpx

ANILIST_URL = "https://graphql.anilist.co"

ANIME_QUERY = """
query ($id: Int!) {
  Media(id: $id, type: ANIME) {
    id
    idMal
    title { romaji english native }
    season      # WINTER | SPRING | SUMMER | FALL
    seasonYear
    format      # TV | MOVIE | OVA | ONA | SPECIAL | ...
    coverImage { extraLarge large medium color }
    synonyms
  }
}
"""

async def fetch_anime_by_id(anilist_id: int) -> dict | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
          ANILIST_URL, 
          json={"query": ANIME_QUERY, "variables": {"id": anilist_id}}
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        return data.get("Media")
