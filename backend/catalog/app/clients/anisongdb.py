from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional, Set

import httpx

ANISONGDB_BASE = os.getenv("ANISONGDB_BASE_URL")
DEFAULT_TIMEOUT = float(os.environ.get("ANISONGDB_TIMEOUT_SEC", "10.0"))

if ANISONGDB_BASE and ANISONGDB_BASE.endswith("/"):
    ANISONGDB_BASE = ANISONGDB_BASE[:-1]

_ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|/|&| feat\. | feat | ft\. | x )\s*", re.IGNORECASE)
_num_re = re.compile(r"(\d+)")

_TYPE_MAP = {
    "op": "OP", "opening": "OP",
    "ed": "ED", "ending": "ED",
    "in": "IN", "insert": "IN", "insert song": "IN",
}

# Default flags matching for artist
ARTIST_FILTERS: Dict[str, Any] = {
    "group_granularity": 99,
    "max_other_artist": 0,
    "ignore_duplicate": False,
    "opening_filter": True,
    "ending_filter": True,
    "insert_filter": True,
    "normal_broadcast": True,
    "dub": True,
    "rebroadcast": True,
    "standard": True,
    "instrumental": True,
    "chanting": True,
    "character": True,
}

# Default flags matching for composer
COMPOSER_FILTERS: Dict[str, Any] = {
    "arrangement": True,
    "ignore_duplicate": False,
    "opening_filter": True,
    "ending_filter": True,
    "insert_filter": True,
    "normal_broadcast": True,
    "dub": True,
    "rebroadcast": True,
    "standard": True,
    "instrumental": True,
    "chanting": True,
    "character": True,
}

class AniSongDBNotConfigured(RuntimeError):
    pass


def _require_base() -> str:
    if not ANISONGDB_BASE:
        raise AniSongDBNotConfigured("Set ANISONGDB_BASE_URL (e.g. https://host/api)")
    return ANISONGDB_BASE


async def _post_json(client: httpx.AsyncClient, url: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    r = await client.post(url, json=payload)
    r.raise_for_status()
    data = r.json()
    return data or []


def parse_use_type_and_seq(s: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    """
    Accepts: 'OP', 'OP 1', 'Opening 2', 'Ending 10', 'Insert Song', 'Insert 3', etc.
    Returns: ('OP'|'ED'|'IN'|None, sequence:int|None)
    """
    if not s:
        return None, None
    low = s.lower().strip()
    # normalize separators
    low = low.replace("_", " ").replace("-", " ")

    # sequence: first integer anywhere
    mnum = _num_re.search(low)
    seq = int(mnum.group(1)) if mnum else None

    # type: look for any mapped keyword as a whole word
    for key, val in _TYPE_MAP.items():
        if re.search(rf"\b{re.escape(key)}\b", low):
            return val, seq

    # fallback: literal tokens
    mtype = re.search(r"\b(op|ed|in)\b", low)
    if mtype:
        return mtype.group(1).upper(), seq

    return None, seq


def explode_names_from_string(s: Optional[str]) -> List[str]:
    if not s:
        return []
    parts = [p.strip() for p in _ARTIST_SPLIT_RE.split(s) if p.strip()]
    seen, out = set(), []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


async def fetch_by_mal_ids(mal_ids: List[int]) -> List[Dict[str, Any]]:
    """
    POST /api/mal_ids_request with body: {"mal_ids":[...] }
    Returns a list[SongEntry].
    """
    base = _require_base()
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(f"{base}/mal_ids_request", json={"mal_ids": mal_ids})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []


async def search_by_title(title: str) -> List[Dict[str, Any]]:
    """
    POST /api/search_request with body:
      {"anime_search_filter":{"search": "<title>"}}
    Returns a list[SongEntry].
    """
    base = _require_base()
    payload = {
        "anime_search_filter": {"search": title},
        # leave all filters at their defaults: opening/ending/insert all true
    }
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(f"{base}/search_request", json=payload)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    
    
async def fetch_songs_by_artist_ids(
    artist_ids: List[int],
    *,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if not artist_ids:
        return []
    payload = {**ARTIST_FILTERS, **(filters or {}), "artist_ids": [int(i) for i in artist_ids]}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        try:
            r = await client.post(f"{ANISONGDB_BASE}/artist_ids_request", json=payload)
            r.raise_for_status()
            return r.json() or []
        except httpx.HTTPStatusError as e:
            # Treat server/client errors as "no results" so imports continue
            if e.response is None or e.response.status_code >= 400:
                return []
            raise


async def fetch_songs_by_composer_ids(
    composer_ids: List[int],
    *,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if not composer_ids:
        return []
    payload = {**COMPOSER_FILTERS, **(filters or {}), "composer_ids": [int(i) for i in composer_ids]}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        try:
            r = await client.post(f"{ANISONGDB_BASE}/composer_ids_request", json=payload)
            r.raise_for_status()
            return r.json() or []
        except httpx.HTTPStatusError as e:
            # We treat that as empty and move on.
            if e.response is None or e.response.status_code >= 400:
                return []
            raise
    

async def search_songs_for_person(name: str, roles: Set[str], *, size: int = 1000) -> List[Dict[str, Any]]:
    """
    POST /api/search_request using role-specific filters (artist/composer/arranger).
    Uses partial_match for broader coverage.
    """
    if not name:
        return []
    payload: Dict[str, Any] = dict(ARTIST_FILTERS)
    if "artist" in roles:
        payload["artist_search_filter"] = {"search": name, "partial_match": True}
    if "composer" in roles:
        payload["composer_search_filter"] = {"search": name, "partial_match": True}
    if "arranger" in roles:
        payload["arranger_search_filter"] = {"search": name, "partial_match": True}
    payload["size"] = int(size)

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(f"{ANISONGDB_BASE}/search_request", json=payload)
        r.raise_for_status()
        return r.json() or []
