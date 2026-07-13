#!/usr/bin/env python3
"""Download songs from NetEase manifest via yt-dlp; rename to 'artist - name.mp3'; log jsonl."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent
LOG_PATH = DEPLOY / "download-status.jsonl"
LIKED_DIR = DEPLOY / "music" / "liked"
INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))



def sanitize_filename(name: str) -> str:
    name = INVALID_CHARS.sub("_", name).strip()
    return name[:200] if len(name) > 200 else name


def expected_filename(song: dict) -> str:
    artist = song.get("artist") or "Unknown"
    title = song.get("name") or song.get("id")
    return sanitize_filename(f"{artist} - {title}.mp3")


def log_status(entry: dict) -> None:
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def download_one(song: dict, target: str, dry_run: bool) -> str:
    """Return status: ok | skipped | failed | preview_only"""
    out_path = LIKED_DIR / expected_filename(song)
    if out_path.exists() and out_path.stat().st_size > 500_000:
        return "skipped"

    url = f"https://music.163.com/song?id={song['id']}"
    tmp_pattern = str(LIKED_DIR / f"__dl_{song['id']}.%(ext)s")

    if dry_run:
        safe_print(f"  [dry-run] {url} -> {out_path.name}")
        return "ok"

    LIKED_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--no-update",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "-o",
        tmp_pattern,
        url,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        err = getattr(e, "stderr", None) or str(e)
        log_status(
            {
                "id": song["id"],
                "name": song.get("name"),
                "artist": song.get("artist"),
                "likedIndex": song.get("likedIndex"),
                "status": "failed",
                "error": err[:500],
            }
        )
        return "failed"

    candidates = list(LIKED_DIR.glob(f"__dl_{song['id']}.*"))
    if not candidates:
        log_status(
            {
                "id": song["id"],
                "name": song.get("name"),
                "status": "failed",
                "error": "no output file",
            }
        )
        return "failed"

    src = candidates[0]
    size = src.stat().st_size
    if size < 500_000:
        try:
            src.unlink(missing_ok=True)
        except PermissionError:
            safe_print(f"  [warn] cannot delete locked temp file: {src.name}")
        log_status(
            {
                "id": song["id"],
                "name": song.get("name"),
                "status": "preview_only",
                "size": size,
            }
        )
        return "preview_only"

    if out_path.exists():
        out_path.unlink()
    src.rename(out_path)
    log_status(
        {
            "id": song["id"],
            "name": song.get("name"),
            "artist": song.get("artist"),
            "likedIndex": song.get("likedIndex"),
            "status": "ok",
            "file": out_path.name,
            "size": size,
        }
    )
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch download NetEase songs via yt-dlp")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--batch", type=int, default=0, help="0-based batch index")
    parser.add_argument("--target", choices=["local", "vps"], default="local")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else DEPLOY / args.manifest
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    songs = manifest.get("songs") or []
    start = args.batch * args.batch_size
    end = start + args.batch_size
    batch_songs = songs[start:end]
    if not batch_songs:
        print(f"empty batch {args.batch} (offset {start})")
        return 0

    safe_print(f"manifest={manifest_path.name} batch={args.batch} songs={start}-{end - 1} count={len(batch_songs)}")
    stats = {"ok": 0, "skipped": 0, "failed": 0, "preview_only": 0}

    for i, song in enumerate(batch_songs):
        idx = song.get("likedIndex", start + i)
        safe_print(f"[{idx}] {song.get('artist')} - {song.get('name')}")
        status = download_one(song, args.target, args.dry_run)
        stats[status] = stats.get(status, 0) + 1

    safe_print(f"stats: {stats}")
    return 0 if stats.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
