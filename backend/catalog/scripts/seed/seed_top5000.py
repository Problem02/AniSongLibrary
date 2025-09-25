import os, sys, time, asyncio
from typing import List, Dict, Any, Optional, Set
import aiohttp
from datetime import datetime, timedelta

# ---------------- config ----------------
API_BASE = os.getenv("API_BASE", "http://localhost:8001/api")
MAX_IMPORTS = int(os.getenv("MAX_IMPORTS", "5000"))

# AniList pacing — safe for 30 rpm periods; override with ANILIST_RPS=0.33..0.5
ANILIST_RPS = float(os.getenv("ANILIST_RPS", "0.45"))
REQ_INTERVAL = 1.0 / max(ANILIST_RPS, 0.1)

# Catalog/AnisongDB pacing — intentionally slower than AniList
ANISONGDB_RPS = float(os.getenv("ANISONGDB_RPS", "0.20"))  # ≈ 12 rpm by default
ANISONGDB_MAX_BACKOFF = float(os.getenv("ANISONGDB_MAX_BACKOFF", "60"))

CONCURRENCY = int(os.getenv("CONCURRENCY", "8"))
CALL_SONGS_BY_PERSON = os.getenv("CALL_SONGS_BY_PERSON", "0") == "1"

VERBOSE = int(os.getenv("VERBOSE", "1"))            # 0=silent-ish, 1=normal, 2=extra
LOG_EVERY = int(os.getenv("LOG_EVERY", "25"))       # progress heartbeat every N items

PAGE_SIZE = 50
ANILIST_GQL = "https://graphql.anilist.co"
ANILIST_QUERY = """
query ($page:Int, $perPage:Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { hasNextPage }
    media(type: ANIME, sort: POPULARITY_DESC) { id }
  }
}
"""

def _hdr_int(headers, key, default=None):
    try:
        return int(headers.get(key)) if headers.get(key) is not None else default
    except Exception:
        return default

def _fmt_eta(start_ts: float, done: int, total: int) -> str:
    if done <= 0:
        return "—"
    rate = done / max(time.time() - start_ts, 1e-6)
    remaining = max(total - done, 0)
    secs = remaining / max(rate, 1e-9)
    return str(timedelta(seconds=int(secs)))

def _println(msg: str):
    print(msg, flush=True)

# ---------------- simple async rate limiter ----------------
class AsyncRateLimiter:
    """Global min-interval gate for friendly pacing across concurrent tasks."""
    def __init__(self, rps: float):
        self.min_interval = 1.0 / max(rps, 0.001)
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self, extra_sleep: float = 0.0):
        async with self._lock:
            now = time.monotonic()
            wait = max(self._last + self.min_interval - now, 0.0)
            total = wait + max(extra_sleep, 0.0)
            if total > 0:
                await asyncio.sleep(total)
            self._last = time.monotonic()

anisongdb_rl = AsyncRateLimiter(ANISONGDB_RPS)

# ---------------- AniList ----------------
async def fetch_top_anilist_ids(limit: int) -> List[int]:
    ids: List[int] = []
    page = 1
    backoff = 1.0
    max_backoff = 60.0
    start = time.time()

    if VERBOSE:
        _println(f"[AniList] Starting fetch (limit={limit}, rps≈{ANILIST_RPS})")

    async with aiohttp.ClientSession() as s:
        while len(ids) < limit:
            t0 = time.perf_counter()
            try:
                async with s.post(
                    ANILIST_GQL,
                    json={"query": ANILIST_QUERY, "variables": {"page": page, "perPage": PAGE_SIZE}},
                ) as r:
                    if r.status == 429:
                        ra = r.headers.get("Retry-After")
                        wait = float(ra) if (ra and ra.replace(".", "", 1).isdigit()) else 60.0
                        _println(f"[AniList] 429 rate-limited. Sleeping {wait:.1f}s…")
                        await asyncio.sleep(min(wait, max_backoff))
                        continue

                    if 500 <= r.status < 600:
                        _println(f"[AniList] {r.status} server err. Backoff {backoff:.1f}s…")
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, max_backoff)
                        continue

                    r.raise_for_status()
                    data = await r.json()

                    remaining = _hdr_int(r.headers, "X-RateLimit-Remaining")
                    reset_ts = _hdr_int(r.headers, "X-RateLimit-Reset")
                    now = int(time.time())
                    if remaining is not None and reset_ts is not None:
                        secs_left = max(reset_ts - now, 1)
                        paced_delay = (secs_left / max(remaining, 1)) + 0.05
                    else:
                        paced_delay = 0.0

            except aiohttp.ClientError as e:
                _println(f"[AniList] network error: {e!r}. Backoff {backoff:.1f}s…")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                continue

            backoff = 1.0
            media = (data.get("data", {}).get("Page", {}).get("media")) or []
            if not media:
                if VERBOSE:
                    _println(f"[AniList] No media on page {page}. Stopping.")
                break

            ids.extend([m["id"] for m in media])
            took = time.perf_counter() - t0

            if VERBOSE:
                eta = _fmt_eta(start, len(ids), limit)
                head = f"[AniList] page={page:>3} ids={len(ids)}/{limit}"
                tail = f"took={took:.2f}s, next_sleep={max(REQ_INTERVAL - took, paced_delay):.2f}s, eta≈{eta}"
                if remaining is not None and reset_ts is not None:
                    tail += f", rem={remaining}, reset_in={max(reset_ts - now,0)}s"
                _println(f"{head} — {tail}")

            if not data["data"]["Page"]["pageInfo"]["hasNextPage"]:
                break
            page += 1

            # sleep based on chosen RPS and window pacing
            dt = took
            base_sleep = max(REQ_INTERVAL - dt, 0.0)
            sleep_for = max(base_sleep, paced_delay)
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

    if VERBOSE:
        _println(f"[AniList] Done. Collected {len(ids)} IDs in {int(time.time()-start)}s")
    return ids[:limit]

# ---------------- Catalog API calls (with AnisongDB-friendly pacing) ----------------
async def _do_request(session: aiohttp.ClientSession, method: str, url: str, json: dict | None = None) -> aiohttp.ClientResponse:
    """
    Shared request helper that:
    - waits on the anisongdb rate limiter BEFORE hitting endpoints likely to touch AnisongDB
    - respects Retry-After on 429
    - exponential backoff for 5xx and network errors
    """
    backoff = 1.0
    while True:
        # polite pre-wait (for everything that might hit AnisongDB)
        # We detect that by URL path:
        path = url.split("/api", 1)[-1] if "/api" in url else url
        if any(path.startswith(p) for p in ("/songs/by-anime", "/people/import/anisongdb", "/songs/by-person")):
            await anisongdb_rl.wait()

        try:
            if method == "GET":
                r = await session.get(url)
            elif method == "POST":
                r = await session.post(url, json=json)
            else:
                raise RuntimeError(f"Unsupported method {method}")
        except aiohttp.ClientError as e:
            if VERBOSE >= 2:
                _println(f"[HTTP] network error {e!r}, backoff {backoff:.1f}s … ({method} {url})")
            await asyncio.sleep(min(backoff, ANISONGDB_MAX_BACKOFF))
            backoff = min(backoff * 2, ANISONGDB_MAX_BACKOFF)
            continue

        # Handle rate limit from your API (likely bubbling up from AnisongDB)
        if r.status == 429:
            ra = r.headers.get("Retry-After")
            wait = float(ra) if (ra and ra.replace(".", "", 1).isdigit()) else max(5.0, backoff)
            if VERBOSE:
                _println(f"[HTTP] 429 from {url} — sleeping {wait:.1f}s")
            await asyncio.sleep(min(wait, ANISONGDB_MAX_BACKOFF))
            backoff = min(backoff * 2, ANISONGDB_MAX_BACKOFF)
            continue

        if 500 <= r.status < 600:
            if VERBOSE >= 2:
                _println(f"[HTTP] {r.status} from {url} — backoff {backoff:.1f}s")
            await asyncio.sleep(min(backoff, ANISONGDB_MAX_BACKOFF))
            backoff = min(backoff * 2, ANISONGDB_MAX_BACKOFF)
            await r.release()
            continue

        # success or handled non-5xx
        return r

async def import_anime(session: aiohttp.ClientSession, anilist_id: int) -> Optional[str]:
    # anime import uses AniList under the hood; still fine to go at app speed
    url = f"{API_BASE}/anime/import/anilist/{anilist_id}"
    r = await _do_request(session, "POST", url)
    if r.status in (200, 201):
        try:
            return (await r.json()).get("id")
        except Exception:
            return None
    if r.status == 404:
        return None
    raise RuntimeError(f"anime {anilist_id}: {r.status} {await r.text()}")

async def songs_by_anime(session: aiohttp.ClientSession, anime_uuid: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE}/songs/by-anime/{anime_uuid}"
    r = await _do_request(session, "GET", url)
    if r.status in (200, 201):
        try:
            return await r.json()
        except Exception:
            return []
    return []

async def import_person(session: aiohttp.ClientSession, anisongdb_id: int) -> Optional[str]:
    url = f"{API_BASE}/people/import/anisongdb/{anisongdb_id}"  # import_songs defaults true
    r = await _do_request(session, "POST", url)
    if r.status in (200, 201, 204, 409):
        try:
            j = await r.json()
            return j.get("id")
        except Exception:
            return None
    if r.status == 404:
        return None
    return None

async def songs_by_person(session: aiohttp.ClientSession, person_uuid: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE}/songs/by-person/{person_uuid}?roles=artist,composer,arranger"
    r = await _do_request(session, "GET", url)
    if r.status in (200, 201):
        try:
            return await r.json()
        except Exception:
            return []
    return []

# ---------------- credit extraction ----------------
def collect_people_from_songs(songs: List[Dict[str, Any]]) -> Set[int]:
    out: Set[int] = set()
    if not isinstance(songs, list):
        return out
    for s in songs:
        for c in (s.get("credits") or []):
            p = c.get("people") or {}
            v = p.get("anisongdb_id")
            if isinstance(v, int):
                out.add(v)
            else:
                try:
                    if v is not None:
                        out.add(int(v))
                    else:
                        ext = p.get("external_links") or {}
                        v2 = ext.get("anisongdb")
                        if v2 is not None:
                            out.add(int(v2))
                except Exception:
                    pass
    return out

# ---------------- progress helpers ----------------
class Counter:
    def __init__(self): self.n=0
    def inc(self, k=1): self.n += k; return self.n

# ---------------- orchestrator ----------------
async def main():
    _println(f"Seeding start @ {datetime.now().strftime('%H:%M:%S')} • API_BASE={API_BASE}")
    top_ids = await fetch_top_anilist_ids(MAX_IMPORTS)
    total_anime = len(top_ids)
    if total_anime == 0:
        _println("No AniList IDs fetched. Exiting.")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    anime_done = Counter()
    people_done = Counter()
    anime_errors = Counter()
    people_errors = Counter()
    people_ids_global: Set[int] = set()
    t0_anime = time.time()

    async with aiohttp.ClientSession() as session:
        async def work_anime(aid: int) -> Set[int]:
            async with sem:
                try:
                    uuid = await import_anime(session, aid)
                    if not uuid:
                        anime_errors.inc()
                        return set()
                    songs = await songs_by_anime(session, uuid)
                    return collect_people_from_songs(songs)
                except Exception as e:
                    anime_errors.inc()
                    if VERBOSE >= 2:
                        _println(f"[anime err] {aid}: {e}")
                    return set()
                finally:
                    i = anime_done.inc()
                    if i % LOG_EVERY == 0 or i == total_anime:
                        eta = _fmt_eta(t0_anime, i, total_anime)
                        _println(f"[anime] {i}/{total_anime} done • errors={anime_errors.n} • eta≈{eta}")

        # run anime with progress using as_completed
        tasks = [asyncio.create_task(work_anime(a)) for a in top_ids]
        for t in asyncio.as_completed(tasks):
            pids = await t
            people_ids_global.update(pids)

        _println(f"[anime] Done. {anime_done.n}/{total_anime} • errors={anime_errors.n} • unique people found={len(people_ids_global)}")

        # --- import people ---
        total_people = len(people_ids_global)
        if total_people == 0:
            _println("[people] No people to import. Seeding complete.")
            return

        t0_people = time.time()
        pid_to_uuid: Dict[int, Optional[str]] = {}

        async def work_person(pid: int):
            async with sem:
                try:
                    person_uuid = await import_person(session, pid)
                    pid_to_uuid[pid] = person_uuid
                    if CALL_SONGS_BY_PERSON and person_uuid:
                        await songs_by_person(session, person_uuid)
                except Exception as e:
                    people_errors.inc()
                    if VERBOSE >= 2:
                        _println(f"[people err] pid={pid}: {e}")
                finally:
                    j = people_done.inc()
                    if j % LOG_EVERY == 0 or j == total_people:
                        eta = _fmt_eta(t0_people, j, total_people)
                        _println(f"[people] {j}/{total_people} done • errors={people_errors.n} • eta≈{eta}")

        tasks = [asyncio.create_task(work_person(pid)) for pid in people_ids_global]
        for t in asyncio.as_completed(tasks):
            await t

    _println(f"Seeding finished @ {datetime.now().strftime('%H:%M:%S')}")
    _println(f"Summary: anime={anime_done.n}/{total_anime} (errors={anime_errors.n}), people={people_done.n}/{len(people_ids_global)} (errors={people_errors.n})")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _println("\nInterrupted.")
