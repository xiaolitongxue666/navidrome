#!/usr/bin/env python3
"""Slice first 1000 songs from full liked manifest (newest-first trackIds order)."""
import json
import os
from datetime import datetime, timezone

DEPLOY = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
FULL = os.path.join(DEPLOY, "playlist-157658592.json")
OUT = os.path.join(DEPLOY, "playlist-latest1000.json")
COUNT = 1000


def main():
    with open(FULL, encoding="utf-8") as f:
        full = json.load(f)

    songs = full.get("songs") or []
    if len(songs) < COUNT:
        raise SystemExit(f"expected >= {COUNT} songs, got {len(songs)}")

    latest = []
    for i, s in enumerate(songs[:COUNT]):
        latest.append(
            {
                "likedIndex": i,
                "id": s["id"],
                "name": s["name"],
                "artist": s.get("artist", ""),
                "album": s.get("album", ""),
                "fee": s.get("fee", 0),
                "duration": s.get("duration", 0),
            }
        )

    manifest = {
        "playlistId": full.get("playlistId", 157658592),
        "name": full.get("name", ""),
        "source": "trackIds[0:1000] newest-first liked subset",
        "parentTrackCount": full.get("trackCount", len(songs)),
        "trackCount": COUNT,
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "songs": latest,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"written {COUNT} songs -> {OUT}")
    print(f"first: [{latest[0]['likedIndex']}] {latest[0]['artist']} - {latest[0]['name']}")
    print(f"last:  [{latest[-1]['likedIndex']}] {latest[-1]['artist']} - {latest[-1]['name']}")


if __name__ == "__main__":
    main()
