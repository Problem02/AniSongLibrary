#!/usr/bin/env python3
"""
Scrape AMQ master list to populate songs/anime/people in the Catalog DB,
politely and with rate limiting.

It expects your API to expose:
  POST /api/anime/import/by-amq-song/{amq_song_id:int}

That route should:
  - ensure the Song exists (creating if missing, setting amq_song_id)
  - upsert all Anime the song appears in
  - link song <-> anime appearances
  - upsert people credits (artists/composers/arrangers) when available

Usage:
  python backend/catalog/scripts/scrape_amq_master_list.py \
      --file backend/catalog/app/data/libraryMasterList.json \
      --api http://localhost:8001 \
      --concurrency 2 \
      --sleep 0.5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Set

import aiohttp

DEFAULT_API_BASE = "http://localhost:8001"
IMPORT_ROUTE_FMT = "/api/anime/import/by-amq-song/{amq_song_id}"

def extract_unique_amq_song_ids(master: dict) -> list[int]:
    out: Set[int] = set()
    anime_map = master.get("animeMap") or {}
    for _ann_id, anime in anime_map.items():
        song_links = (anime.get("songLinks") or {})
        for key in ("OP", "ED", "INS"):
            for link in song_links.get(key, []) or []:
                song_id = link.get("songId")
                if isinstance(song_id, int):
                    out.add(song_id)
    return sorted(out)

@dataclass
class Limits:
    concurrency: int = 2
    base_sleep: float = 1.0
    jitter: float = 0.4

class State:
    def __init__(self, path: Path):
        self.path = path
        self.done: Set[int] = set()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.done = set(int(x) for x in data.get("done", []))
            except Exception:
                self.done = set()
        # runtime counters
        self.ok = 0
        self.skipped = 0
        self.errors = 0
        self.started_at = time.time()
        self.total_to_do = 0
        self.lock = asyncio.Lock()

    def mark_done_idempotent(self, amq_id: int):
        self.done.add(int(amq_id))
        self._flush()

    def _flush(self):
        tmp = {"done": sorted(self.done)}
        self.path.write_text(json.dumps(tmp, indent=2), encoding="utf-8")

async def polite_sleep(base: float, jitter: float):
    if base <= 0:
        return
    delta = base * jitter
    await asyncio.sleep(max(0.0, random.uniform(base - delta, base + delta)))

async def one_import(session: aiohttp.ClientSession, api_base: str, amq_id: int) -> tuple[str, dict]:
    url = api_base.rstrip("/") + IMPORT_ROUTE_FMT.format(amq_song_id=amq_id)
    async with session.post(url, json={}) as resp:
        try:
            payload = await resp.json()
        except Exception:
            payload = {"_raw": await resp.text()}

        if resp.status == 404:
            return "not_found", payload
        if resp.status == 409:
            return "ok_conflict", payload
        if 200 <= resp.status < 300:
            return "ok", payload

        raise aiohttp.ClientResponseError(
            request_info=resp.request_info,
            history=resp.history,
            status=resp.status,
            message=str(payload)[:500],
            headers=resp.headers,
        )

async def import_with_retries(session: aiohttp.ClientSession, api_base: str, amq_id: int) -> tuple[str, dict]:
    attempt, delay, max_delay, tries = 0, 1.5, 20.0, 6
    while True:
        attempt += 1
        try:
            return await one_import(session, api_base, amq_id)
        except aiohttp.ClientResponseError as e:
            if e.status == 429 or 500 <= e.status < 600:
                if attempt >= tries:
                    return "error", {"detail": f"HTTP {e.status} after {attempt} tries: {e.message}"}
                await asyncio.sleep(delay + random.uniform(0, 0.5))
                delay = min(max_delay, delay * 1.8)
                continue
            return "error", {"detail": f"HTTP {e.status}: {e.message}"}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt >= tries:
                return "error", {"detail": f"Network error after {attempt} tries: {e}"}
            await asyncio.sleep(delay + random.uniform(0, 0.5))
            delay = min(max_delay, delay * 1.8)
        except Exception as e:
            return "error", {"detail": f"Unexpected: {e}"}

async def worker(name: str, api_base: str, todo: asyncio.Queue, limits: Limits, state: State, verbose: bool):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        while True:
            amq_id = await todo.get()
            try:
                await polite_sleep(limits.base_sleep, limits.jitter)
                status, _payload = await import_with_retries(session, api_base, amq_id)
                async with state.lock:
                    if status.startswith("ok"):
                        state.ok += 1
                        state.mark_done_idempotent(amq_id)
                    elif status == "not_found":
                        state.skipped += 1
                        state.mark_done_idempotent(amq_id)
                    else:
                        state.errors += 1
                if verbose:
                    print(f"[{name}] {amq_id} -> {status}")
                    sys.stdout.flush()
            finally:
                todo.task_done()

def fmt_eta(seconds: float) -> str:
    if seconds <= 0 or seconds == float("inf"):
        return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

async def progress_task(state: State, interval: float):
    last_done = 0
    last_time = state.started_at
    while True:
        await asyncio.sleep(interval)
        async with state.lock:
            done = state.ok + state.skipped + state.errors
            remaining = max(0, state.total_to_do - done)
            now = time.time()
            dt = now - last_time
            d_done = done - last_done
            inst_rps = (d_done / dt) if dt > 0 else 0.0
            avg_rps = (done / (now - state.started_at)) if (now > state.started_at) else 0.0
            eta = fmt_eta(remaining / avg_rps) if avg_rps > 0 else "--:--:--"
            print(
                f"\rProcessed {done}/{state.total_to_do} "
                f"(ok:{state.ok} skip:{state.skipped} err:{state.errors})  "
                f"RPS now:{inst_rps:.2f} avg:{avg_rps:.2f}  ETA:{eta}   ",
                end="",
                flush=True,
            )
            last_done, last_time = done, now

async def main(args):
    json_path = Path(args.file)
    master = json.loads(json_path.read_text(encoding="utf-8"))
    amq_ids = extract_unique_amq_song_ids(master)

    state = State(Path(args.resume_state))
    remaining_ids = [i for i in amq_ids if i not in state.done]
    state.total_to_do = len(remaining_ids)

    print(f"Found {len(amq_ids)} unique AMQ song ids; resuming with {len(state.done)} done, {len(remaining_ids)} to go.")

    todo: asyncio.Queue[int] = asyncio.Queue()
    for i in remaining_ids:
        await todo.put(i)

    limits = Limits(concurrency=args.concurrency, base_sleep=args.sleep, jitter=args.jitter)

    # Start progress heartbeat
    prog = asyncio.create_task(progress_task(state, args.progress_interval))

    workers = [
        asyncio.create_task(worker(f"W{idx+1}", args.api, todo, limits, state, args.verbose))
        for idx in range(max(1, limits.concurrency))
    ]
    await todo.join()
    for w in workers:
        w.cancel()
    prog.cancel()
    print("\nAll done.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to libraryMasterList.json")
    parser.add_argument("--api", default=DEFAULT_API_BASE, help="Base URL for your Catalog API (e.g., http://localhost:8001)")
    parser.add_argument("--concurrency", type=int, default=2, help="Concurrent workers (keep small)")
    parser.add_argument("--sleep", type=float, default=1.0, help="Base delay between requests per worker (seconds)")
    parser.add_argument("--jitter", type=float, default=0.4, help="Fractional jitter around sleep (0.0–1.0)")
    parser.add_argument("--resume-state", default=".amq_scrape_state.json", help="Path to a JSON file to store progress")
    parser.add_argument("--progress-interval", type=float, default=5.0, help="Seconds between progress updates")
    parser.add_argument("--verbose", action="store_true", help="Log each item result")
    args = parser.parse_args()
    try:
        exit_code = asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        exit_code = 130
    sys.exit(exit_code)
