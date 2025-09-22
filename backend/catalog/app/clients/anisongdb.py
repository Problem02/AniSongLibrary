from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional

import httpx

ANISONGDB_BASE = os.getenv("ANISONGDB_BASE_URL")
if ANISONGDB_BASE and ANISONGDB_BASE.endswith("/"):
    ANISONGDB_BASE = ANISONGDB_BASE[:-1]

_ARTIST_SPLIT_RE = re.compile(r"\s*(?:,|/|&| feat\. | feat | ft\. | x )\s*", re.IGNORECASE)
_num_re = re.compile(r"(\d+)")

_TYPE_MAP = {
    "op": "OP", "opening": "OP",
    "ed": "ED", "ending": "ED",
    "in": "IN", "insert": "IN", "insert song": "IN",
}

class AniSongDBNotConfigured(RuntimeError):
    pass

def _require_base() -> str:
    if not ANISONGDB_BASE:
        raise AniSongDBNotConfigured("Set ANISONGDB_BASE_URL (e.g. https://host/api)")
    return ANISONGDB_BASE

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

async def fetch_by_mal_ids(mal_ids: List[int], *, timeout: float = 12.0) -> List[Dict[str, Any]]:
    """
    POST /api/mal_ids_request with body: {"mal_ids":[...] }
    Returns a list[SongEntry].
    """
    base = _require_base()
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{base}/mal_ids_request", json={"mal_ids": mal_ids})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

async def search_by_title(title: str, *, timeout: float = 12.0) -> List[Dict[str, Any]]:
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
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{base}/search_request", json=payload)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
