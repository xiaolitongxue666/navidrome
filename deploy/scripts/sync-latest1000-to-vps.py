#!/usr/bin/env python3
"""Sync latest1000 manifest MP3s to VPS (filtered, no --delete)."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent
MANIFEST = DEPLOY / "playlist-latest1000.json"
LOCAL_DIR = DEPLOY / "music" / "liked"
REMOTE = "ubuntu@xiaolitongxue.com.cn:/home/ubuntu/music/liked/"
MIN_FREE_GB = 3
INVALID = re.compile(r'[<>:"/\\|?*]')


def expected_name(song: dict) -> str:
    artist = song.get("artist") or "Unknown"
    title = song.get("name") or str(song["id"])
    base = INVALID.sub("_", f"{artist} - {title}").strip()
    if len(base) > 200:
        base = base[:200]
    return base + ".mp3"


def ssh(cmd: str) -> str:
    r = subprocess.run(
        ["ssh", "ubuntu@xiaolitongxue.com.cn", cmd],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        songs = json.load(f).get("songs") or []

    print("=== VPS disk check ===")
    print(ssh("df -h / && du -sh /home/ubuntu/music/* 2>/dev/null || true"))

    avail_kb = int(ssh("df -k / | awk 'NR==2 {print $4}'").strip())
    avail_gb = avail_kb // 1024 // 1024
    print(f"available: ~{avail_gb}GB")
    if avail_gb < MIN_FREE_GB:
        print(f"ABORT: free space < {MIN_FREE_GB}GB", file=sys.stderr)
        return 1

    if not args.dry_run:
        ssh("mkdir -p /home/ubuntu/music/liked")

    to_sync: list[Path] = []
    for s in songs:
        name = expected_name(s)
        path = LOCAL_DIR / name
        if path.is_file() and path.stat().st_size > 500_000:
            to_sync.append(path)

    print(f"local ready: {len(to_sync)} / {len(songs)}")
    if not to_sync:
        print("nothing to sync")
        return 0

    for p in to_sync:
        dest = REMOTE + p.name
        if args.dry_run:
            print(f"scp {p.name}")
            continue
        subprocess.run(["scp", str(p), dest], check=True)

    if not args.dry_run:
        n = ssh("ls -1 /home/ubuntu/music/liked/*.mp3 2>/dev/null | wc -l").strip()
        print(f"remote liked mp3 count: {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
