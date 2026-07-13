#!/usr/bin/env python3
"""Run all batches for a manifest (resume-safe)."""
import argparse
import math
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "download-batch.py"
DEPLOY = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--from-batch", type=int, default=0)
    parser.add_argument("--to-batch", type=int, default=-1, help="-1 = all")
    args = parser.parse_args()

    import json

    manifest_path = DEPLOY / args.manifest if not Path(args.manifest).is_absolute() else Path(args.manifest)
    with open(manifest_path, encoding="utf-8") as f:
        n = len(json.load(f).get("songs") or [])

    total_batches = math.ceil(n / args.batch_size)
    end = total_batches if args.to_batch < 0 else min(args.to_batch + 1, total_batches)
    py = sys.executable

    for b in range(args.from_batch, end):
        print(f"\n=== batch {b}/{total_batches - 1} ===")
        rc = subprocess.call(
            [
                py,
                str(SCRIPT),
                "--manifest",
                str(manifest_path),
                "--batch-size",
                str(args.batch_size),
                "--batch",
                str(b),
            ]
        )
        if rc != 0:
            print(f"batch {b} had failures (rc={rc}), continuing...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
