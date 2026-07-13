#!/usr/bin/env python3
"""Embed UTF-8 ID3 tags and album covers into local liked MP3s from enriched manifest."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from tag_utils import apply_tags_from_manifest, expected_filename

DEPLOY = Path(__file__).resolve().parent.parent
LIKED_DIR = DEPLOY / "music" / "liked"
DEFAULT_MANIFEST = DEPLOY / "playlist-enriched.json"
FALLBACK_MANIFEST = DEPLOY / "playlist-157658592.json"
LOG_PATH = DEPLOY / "embed-status.jsonl"


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))


def log_status(entry: dict) -> None:
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_filename_index(songs: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for song in songs:
        index[expected_filename(song)] = song
    return index


def load_done_ids() -> set[str]:
    done: set[str] = set()
    if not LOG_PATH.is_file():
        return done
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") in ("ok", "skipped", "no_cover"):
                done.add(str(row.get("id", "")))
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed ID3 tags and covers into liked MP3s")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--liked-dir", type=Path, default=LIKED_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else (DEPLOY / args.manifest).resolve()
    if not manifest_path.is_file() and args.manifest != DEFAULT_MANIFEST:
        manifest_path = DEFAULT_MANIFEST.resolve()
    if not manifest_path.is_file():
        manifest_path = FALLBACK_MANIFEST.resolve()

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    songs = manifest.get("songs") or []
    by_name = build_filename_index(songs)

    liked_dir = args.liked_dir if args.liked_dir.is_absolute() else DEPLOY / args.liked_dir
    mp3_files = sorted(liked_dir.glob("*.mp3"))
    safe_print(f"manifest={manifest_path.name} mp3_files={len(mp3_files)}")

    done_ids = load_done_ids() if args.resume else set()
    stats = {"ok": 0, "skipped": 0, "no_cover": 0, "unmatched": 0, "error": 0}
    processed = 0

    for mp3 in mp3_files:
        if args.limit and processed >= args.limit:
            break
        song = by_name.get(mp3.name)
        if not song:
            stats["unmatched"] += 1
            log_status({"file": mp3.name, "status": "unmatched"})
            safe_print(f"  [unmatched] {mp3.name}")
            continue

        sid = str(song["id"])
        if sid in done_ids:
            stats["skipped"] += 1
            continue

        if args.dry_run:
            safe_print(f"  [dry-run] {mp3.name}")
            stats["ok"] += 1
            processed += 1
            continue

        status = apply_tags_from_manifest(mp3, song, dry_run=False)
        stats[status] = stats.get(status, 0) + 1
        log_status(
            {
                "id": sid,
                "file": mp3.name,
                "name": song.get("name"),
                "artist": song.get("artist"),
                "albumName": song.get("albumName") or song.get("album"),
                "status": status,
            }
        )
        safe_print(f"  [{status}] {mp3.name}")
        processed += 1

    safe_print(f"stats: {stats}")
    return 0 if stats.get("error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
