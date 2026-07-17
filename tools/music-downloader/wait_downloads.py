#!/usr/bin/env python3
"""轮询 Soulseek 下载进度，完成后整理到曲库。"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from downloader import api_get, iter_transfer_files, show_transfer_status


def summarize():
    transfers = api_get("/transfers/downloads")
    files = iter_transfer_files(transfers)
    by = {}
    active = 0
    done_ok = 0
    done_fail = 0
    for f in files:
        st = f.get("state", "?")
        by[st] = by.get(st, 0) + 1
        finished = any(
            x in st
            for x in ("Completed", "Cancelled", "TimedOut", "Failed", "Aborted")
        )
        if finished:
            if "Succeeded" in st or (
                "Completed" in st
                and "Cancelled" not in st
                and "TimedOut" not in st
                and "Failed" not in st
            ):
                done_ok += 1
            else:
                done_fail += 1
        else:
            active += 1
    return files, by, active, done_ok, done_fail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=900, help="最长等待秒数")
    parser.add_argument("--interval", type=int, default=20)
    parser.add_argument("--organize", action="store_true", help="结束后运行 organizer.py")
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        files, by, active, done_ok, done_fail = summarize()
        print(
            f"\n[{time.strftime('%H:%M:%S')}] "
            f"total={len(files)} active={active} ok~={done_ok} fail~={done_fail}"
        )
        for s, c in sorted(by.items()):
            print(f"  {s}: {c}")
        show_transfer_status()
        if files and active == 0:
            print("\n队列已无活动任务。")
            break
        if not files:
            print("无传输任务。")
            break
        time.sleep(args.interval)

    if args.organize:
        subprocess.check_call(
            [sys.executable, os.path.join(os.path.dirname(__file__), "organizer.py")],
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )


if __name__ == "__main__":
    main()
