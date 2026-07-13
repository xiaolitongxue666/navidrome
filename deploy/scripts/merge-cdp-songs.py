#!/usr/bin/env python3
"""Merge CDP browser-log chunks into deploy/playlist-157658592.json."""
import json
import glob
import os
from datetime import datetime, timezone

LOG_DIR = os.path.expanduser(
    r"~/.cursor/browser-logs"
)
# Also check project-local path used on Windows
ALT_LOG_DIRS = [
    r"C:\Users\Administrator\.cursor\browser-logs",
]

OUT = os.path.join(
    os.path.dirname(__file__), "..", "playlist-157658592.json"
)
IDS = os.path.join(
    os.path.dirname(__file__), "..", "playlist-157658592-ids.json"
)

CHUNK_FILES = [
    "cdp-response-Runtime.evaluate-2026-07-13T01-55-42-784Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-55-48-574Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-55-54-884Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-55-55-898Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-55-57-424Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-56-03-135Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-56-04-177Z.json",
    "cdp-response-Runtime.evaluate-2026-07-13T01-56-05-071Z.json",
]


def find_log(path):
    for d in [LOG_DIR] + ALT_LOG_DIRS:
        p = os.path.join(d, path)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(path)


def load_chunk(filename):
    with open(find_log(filename), encoding="utf-8") as f:
        cdp = json.load(f)
    payload = json.loads(cdp["result"]["value"])
    return payload


def main():
    chunks = [load_chunk(f) for f in CHUNK_FILES]
    chunks.sort(key=lambda c: c["start"])

    all_songs = []
    for c in chunks:
        all_songs.extend(c["songs"])
        print(f"chunk start={c['start']} end={c['end']} count={c['count']}")

    with open(IDS, encoding="utf-8") as f:
        ids_meta = json.load(f)

    # Preserve playlist order from trackIds
    track_ids = ids_meta.get("trackIds") or ids_meta.get("ids") or []
    id_order = {str(tid): i for i, tid in enumerate(track_ids)}
    all_songs.sort(key=lambda s: id_order.get(s["id"], 999999))

    seen = set()
    deduped = []
    for s in all_songs:
        if s["id"] not in seen:
            seen.add(s["id"])
            deduped.append(s)

    manifest = {
        "playlistId": 157658592,
        "name": ids_meta.get("name", chunks[0].get("name", "")),
        "trackCount": ids_meta.get("trackCount", 7269),
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "source": "browser-login-api song/detail batches",
        "songs": deduped,
    }

    out_path = os.path.normpath(OUT)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nmerged: {len(deduped)} songs -> {out_path}")
    print(f"expected: {manifest['trackCount']}")
    if len(deduped) != manifest["trackCount"]:
        missing = manifest["trackCount"] - len(deduped)
        print(f"WARNING: missing {missing} songs")
    else:
        print("OK: full playlist exported")


if __name__ == "__main__":
    main()
