#!/usr/bin/env python3
"""Enrich playlist manifest with albumName/albumPicUrl/albumArtist from NetEase song/detail API."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent
DEFAULT_IN = DEPLOY / "playlist-157658592.json"
DEFAULT_OUT = DEPLOY / "playlist-enriched.json"
BATCH_SIZE = 200
API_URL = "https://music.163.com/api/song/detail/?ids=[{ids}]"


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))


def primary_artist(artists: list) -> str:
    if not artists:
        return ""
    return (artists[0].get("name") or "").strip()


def fetch_batch(ids: list[str]) -> dict[str, dict]:
    url = API_URL.format(ids=",".join(ids))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out: dict[str, dict] = {}
    for s in data.get("songs") or []:
        sid = str(s["id"])
        album = s.get("album") or s.get("al") or {}
        artists = s.get("artists") or s.get("ar") or []
        album_artist = primary_artist(artists)
        out[sid] = {
            "albumName": album.get("name") or "",
            "albumPicUrl": album.get("picUrl") or "",
            "albumArtist": album_artist,
        }
    return out


def needs_enrich(song: dict, *, force: bool = False) -> bool:
    if force:
        return True
    if not (song.get("albumName") or song.get("album")):
        return True
    if not (song.get("albumPicUrl") or song.get("picUrl")):
        return True
    if not song.get("albumArtist"):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich manifest with album/cover from NetEase API")
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--delay", type=float, default=0.12, help="seconds between API batches")
    parser.add_argument("--only-ids", type=Path, help="JSON file with id list to enrich (subset)")
    parser.add_argument("--force", action="store_true", help="re-fetch even when album fields exist")
    args = parser.parse_args()

    in_path = args.input if args.input.is_absolute() else DEPLOY / args.input
    out_path = args.output if args.output.is_absolute() else DEPLOY / args.output

    if out_path.is_file():
        with open(out_path, encoding="utf-8") as f:
            manifest = json.load(f)
        safe_print(f"resume from {out_path.name}")
    else:
        with open(in_path, encoding="utf-8") as f:
            manifest = json.load(f)

    songs = manifest.get("songs") or []
    target_ids: set[str] | None = None
    if args.only_ids:
        only_path = args.only_ids if args.only_ids.is_absolute() else DEPLOY / args.only_ids
        with open(only_path, encoding="utf-8") as f:
            meta = json.load(f)
        raw = meta.get("trackIds") or meta.get("ids") or meta.get("songs") or meta
        if raw and isinstance(raw[0], dict):
            target_ids = {str(x["id"]) for x in raw}
        else:
            target_ids = {str(x) for x in raw}

    if target_ids is not None:
        to_fetch = [s for s in songs if str(s["id"]) in target_ids and needs_enrich(s, force=args.force)]
    else:
        to_fetch = [s for s in songs if needs_enrich(s, force=args.force)]

    safe_print(f"songs total={len(songs)} need_enrich={len(to_fetch)} force={args.force}")

    enriched = 0
    failed_batches = 0
    for i in range(0, len(to_fetch), args.batch_size):
        batch = to_fetch[i : i + args.batch_size]
        ids = [str(s["id"]) for s in batch]
        try:
            details = fetch_batch(ids)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            failed_batches += 1
            safe_print(f"  batch {i // args.batch_size} failed: {e}")
            time.sleep(args.delay * 3)
            continue

        id_set = set(ids)
        for song in songs:
            sid = str(song["id"])
            if sid not in id_set:
                continue
            info = details.get(sid)
            if not info:
                continue
            if info.get("albumName"):
                song["albumName"] = info["albumName"]
                song["album"] = info["albumName"]
            if info.get("albumPicUrl"):
                song["albumPicUrl"] = info["albumPicUrl"]
            if info.get("albumArtist"):
                song["albumArtist"] = info["albumArtist"]
            enriched += 1

        safe_print(f"  batch {i // args.batch_size + 1}/{(len(to_fetch) + args.batch_size - 1) // args.batch_size} enriched={enriched}")
        time.sleep(args.delay)

        manifest["enrichedAt"] = datetime.now(timezone.utc).isoformat()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    manifest["enrichedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["source"] = (manifest.get("source") or "") + "; enrich-manifest.py"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    safe_print(f"done: enriched={enriched} failed_batches={failed_batches} -> {out_path}")
    return 0 if failed_batches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
