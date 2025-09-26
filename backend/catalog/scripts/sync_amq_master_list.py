#!/usr/bin/env python3
import argparse, json, time, random
from pathlib import Path
from typing import Set, Tuple, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MASTER_URL = "https://animemusicquiz.com/libraryMasterList"
IMPORT_ROUTE = "/api/anime/import/by-amq-song/{amq_song_id}"

def http_get_json(url: str, etag: Optional[str], last_mod: Optional[str]):
    req = Request(url)
    if etag: req.add_header("If-None-Match", etag)
    if last_mod: req.add_header("If-Modified-Since", last_mod)
    try:
        with urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8")
            data = json.loads(text)
            headers = {k.lower(): v for k, v in r.headers.items()}
            return data, headers, False  # not 304
    except HTTPError as e:
        if e.code == 304:
            headers = {k.lower(): v for k, v in (e.headers or {}).items()}
            return None, headers, True   # 304
        raise

def http_post_json(url: str, body: dict):
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=60) as r:
        return r.status

def extract(master: dict) -> Tuple[str, Set[int]]:
    mid = str(master.get("masterListId", ""))
    ids: Set[int] = set()
    for anime in (master.get("animeMap") or {}).values():
        links = anime.get("songLinks") or {}
        for k in ("OP", "ED", "INS"):
            for it in links.get(k, []) or []:
                sid = it.get("songId")
                if isinstance(sid, int):
                    ids.add(sid)
    return mid, ids

def load_state(path: Path):
    if not path.exists():
        return {"masterListId": 0, "amq_ids": [], "etag": None, "last_modified": None}
    return json.loads(path.read_text(encoding="utf-8"))

def save_state(path: Path, state: dict):
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")

def fmt_eta(seconds: float) -> str:
    if seconds <= 0 or seconds == float("inf"):
        return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def main():
    ap = argparse.ArgumentParser(description="Delta-sync AMQ master list → Catalog")
    ap.add_argument("--api", default="http://localhost:8001", help="Catalog API base")
    ap.add_argument("--state", default="backend/catalog/app/data/.sync_state.json", help="State file path")
    ap.add_argument("--target-rps", type=float, default=0.5, help="Total requests/sec to your API")
    args = ap.parse_args()

    state_path = Path(args.state)
    st = load_state(state_path)

    # Fetch latest master list (honor HTTP caching)
    try:
        data, hdrs, is_304 = http_get_json(MASTER_URL, st.get("etag"), st.get("last_modified"))
    except (HTTPError, URLError) as e:
        print(f"Fetch failed: {e}")
        return 2

    if is_304:
        print("No changes (304 Not Modified).")
        return 0

    old_ids = set(int(x) for x in st.get("amq_ids", []))
    master_id, new_ids = extract(data)
    old_master = str(st.get("masterListId", "")) or "(none)"
    to_add = sorted(new_ids - old_ids)

    print(f"Master {old_master} → {master_id}. New songs: +{len(to_add)}")
    if not to_add:
        # Persist new state and exit
        new_state = {
            "masterListId": str(master_id),
            "amq_ids": sorted(new_ids),
            "etag": (hdrs or {}).get("etag"),
            "last_modified": (hdrs or {}).get("last-modified"),
            "updated_at": int(time.time()),
        }
        save_state(state_path, new_state)
        print("Nothing to import. Sync complete.")
        return 0

    # Import only additions, politely
    base = args.api.rstrip("/")
    delay = 1.0 / max(0.1, args.target_rps)

    ok = skip = err = 0
    total = len(to_add)
    start = last_print = time.time()

    for i, sid in enumerate(to_add, 1):
        url = base + IMPORT_ROUTE.format(amq_song_id=sid)
        try:
            status = http_post_json(url, {})
            if 200 <= status < 300:
                ok += 1
            elif status in (404, 409):
                skip += 1
            else:
                err += 1
        except Exception:
            err += 1

        # progress line every ~2s or at the end
        now = time.time()
        if (now - last_print >= 2.0) or (i == total):
            elapsed = max(1e-6, now - start)
            avg_rps = i / elapsed
            remaining = total - i
            eta = fmt_eta(remaining / avg_rps if avg_rps > 0 else 0)
            print(
                f"\rImported {i}/{total}  ok:{ok} skip:{skip} err:{err}  avg:{avg_rps:.2f} rps  ETA:{eta}   ",
                end="",
                flush=True,
            )
            last_print = now

        # small jitter to avoid a strict cadence
        time.sleep(delay + random.uniform(0, delay * 0.2))

    print()  # newline

    # Persist new state (including cache headers)
    new_state = {
        "masterListId": str(master_id),
        "amq_ids": sorted(new_ids),
        "etag": (hdrs or {}).get("etag"),
        "last_modified": (hdrs or {}).get("last-modified"),
        "updated_at": int(time.time()),
    }
    save_state(state_path, new_state)
    print("Sync complete.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
