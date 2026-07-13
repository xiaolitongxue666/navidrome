#!/usr/bin/env python3
"""Sync all local liked MP3s to VPS (not limited to latest1000 manifest)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent
LOCAL_DIR = DEPLOY / "music" / "liked"
REMOTE = "ubuntu@xiaolitongxue.com.cn:/home/ubuntu/music/liked/"
REMOTE_HOST = "ubuntu@xiaolitongxue.com.cn"
MIN_FREE_GB = 3
MIN_SIZE = 500_000
SSH_IDENTITY = Path.home() / ".ssh" / "id_ed25519"
SSH_BASE = ["-i", str(SSH_IDENTITY), "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new"]


def ssh(cmd: str) -> str:
    r = subprocess.run(
        ["ssh", *SSH_BASE, REMOTE_HOST, cmd],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== VPS disk check ===", flush=True)
    print(ssh("df -h / && du -sh /home/ubuntu/music/* 2>/dev/null || true"), flush=True)

    avail_kb = int(ssh("df -k / | awk 'NR==2 {print $4}'").strip())
    avail_gb = avail_kb // 1024 // 1024
    print(f"available: ~{avail_gb}GB", flush=True)
    if avail_gb < MIN_FREE_GB:
        print(f"ABORT: free space < {MIN_FREE_GB}GB", file=sys.stderr)
        return 1

    if not args.dry_run:
        ssh("mkdir -p /home/ubuntu/music/liked")

    mp3s = [
        p
        for p in sorted(LOCAL_DIR.glob("*.mp3"))
        if p.is_file() and p.stat().st_size > MIN_SIZE
    ]
    print(f"local mp3 ready: {len(mp3s)}", flush=True)
    if not mp3s:
        print("nothing to sync")
        return 0

    for i, p in enumerate(mp3s, 1):
        dest = REMOTE + p.name
        if args.dry_run:
            print(f"scp [{i}/{len(mp3s)}] {p.name}")
            continue
        subprocess.run(["scp", *SSH_BASE, str(p), dest], check=True)
        if i % 10 == 0 or i == len(mp3s):
            print(f"  synced {i}/{len(mp3s)}: {p.name}", flush=True)

    if not args.dry_run:
        n = ssh("ls -1 /home/ubuntu/music/liked/*.mp3 2>/dev/null | wc -l").strip()
        print(f"remote liked mp3 count: {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
