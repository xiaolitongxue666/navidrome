#!/usr/bin/env python3
"""Enrich and embed tags for MP3s not in manifest (B站 extra downloads)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from tag_utils import apply_tags_from_manifest, expected_filename, primary_artist_name

DEPLOY = Path(__file__).resolve().parent.parent
LIKED_DIR = DEPLOY / "music" / "liked"
DEFAULT_MANIFEST = DEPLOY / "playlist-enriched.json"
AUDIT_REPORT = DEPLOY / "audit-tags-report.json"
CANONICAL_PATH = DEPLOY / "data" / "jay-chou-canonical.json"
SEARCH_URL = "https://music.163.com/api/cloudsearch/pc?s={query}&type=1&limit=20"
DETAIL_URL = "https://music.163.com/api/song/detail/?ids=[{ids}]"

BAD_ALBUM_KEYWORDS = (
    "type beat",
    "remix",
    "翻唱",
    "钢琴",
    "轻音乐",
    "slowed",
    "cover",
    "beat",
    "sample",
    "柔情版",
    "女声版",
    "live at",
    "演唱会",
)


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))


def parse_filename(name: str) -> tuple[str, str]:
    stem = Path(name).stem
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
        artist = artist.replace(" _ ", " / ").strip()
        return artist.strip(), title.strip()
    return "", stem.strip()


def load_canonical() -> dict[str, dict]:
    if not CANONICAL_PATH.is_file():
        return {}
    with open(CANONICAL_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("songs") or {}


def lookup_manifest(songs: list[dict], artist: str, title: str) -> dict | None:
    artist_primary = primary_artist_name(artist).lower()
    title_lower = title.lower()
    for song in songs:
        if (song.get("name") or "").strip().lower() != title_lower:
            continue
        song_artist = primary_artist_name(song.get("artist") or "").lower()
        if song_artist == artist_primary:
            if song.get("albumName") or song.get("album"):
                return song
    return None


def is_bad_album(name: str) -> bool:
    lower = (name or "").lower()
    return any(k in lower for k in BAD_ALBUM_KEYWORDS)


def search_candidates(artist: str, title: str) -> list[str]:
    query = urllib.parse.quote(f"{artist} {title}".strip())
    url = SEARCH_URL.format(query=query)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [str(s["id"]) for s in (data.get("result") or {}).get("songs") or []]


def fetch_details(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    url = DETAIL_URL.format(ids=",".join(ids))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")).get("songs") or []


def to_song_entry(s: dict) -> dict:
    album = s.get("album") or {}
    artists = s.get("artists") or []
    artist_names = " / ".join(a.get("name", "") for a in artists)
    album_artist = artists[0].get("name", "") if artists else ""
    return {
        "id": str(s["id"]),
        "name": s.get("name") or "",
        "artist": artist_names,
        "albumName": album.get("name") or "",
        "album": album.get("name") or "",
        "albumPicUrl": album.get("picUrl") or "",
        "albumArtist": album_artist,
    }


def pick_best_match(artist: str, title: str, songs: list[dict]) -> dict | None:
    artist_primary = primary_artist_name(artist)
    title_norm = title.strip()

    ranked: list[tuple[int, dict]] = []
    for s in songs:
        entry = to_song_entry(s)
        song_artists = [a.get("name", "") for a in (s.get("artists") or [])]
        if artist_primary and artist_primary not in song_artists:
            continue
        if entry["name"].strip() != title_norm:
            continue
        if is_bad_album(entry["albumName"]):
            continue
        score = 0
        if entry["albumArtist"] == artist_primary:
            score += 10
        if entry["artist"] == artist:
            score += 5
        if "周杰伦" in entry["albumArtist"] and artist_primary == "周杰伦":
            score += 3
        ranked.append((score, entry))

    if not ranked:
        return None
    ranked.sort(key=lambda x: -x[0])
    return ranked[0][1]


def resolve_song(
    artist: str,
    title: str,
    manifest_songs: list[dict],
    canonical: dict[str, dict],
) -> dict | None:
    if title in canonical and primary_artist_name(artist) == "周杰伦":
        return canonical[title]

    hit = lookup_manifest(manifest_songs, artist, title)
    if hit:
        return hit

    ids = search_candidates(artist, title)
    details = fetch_details(ids[:20])
    return pick_best_match(artist, title, details)


def load_unmatched(report_path: Path, liked_dir: Path, by_name: dict[str, dict]) -> list[Path]:
    names: list[str] = []
    if report_path.is_file():
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        names = report.get("unmatched_files") or []

    files = [liked_dir / n for n in names if (liked_dir / n).is_file()] if names else []
    if not files:
        files = [p for p in sorted(liked_dir.glob("*.mp3")) if p.name not in by_name]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix unmatched MP3 tags via canonical map / NetEase")
    parser.add_argument("--liked-dir", type=Path, default=LIKED_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=AUDIT_REPORT)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="re-embed even if previously fixed")
    args = parser.parse_args()

    liked_dir = args.liked_dir if args.liked_dir.is_absolute() else DEPLOY / args.liked_dir
    manifest_path = args.manifest if args.manifest.is_absolute() else DEPLOY / args.manifest
    report_path = args.report if args.report.is_absolute() else DEPLOY / args.report

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    songs = manifest.get("songs") or []
    by_name = {expected_filename(s): s for s in songs}
    canonical = load_canonical()

    unmatched = load_unmatched(report_path, liked_dir, by_name)
    safe_print(f"unmatched_to_fix={len(unmatched)} canonical_jay_chou={len(canonical)}")
    stats = {"ok": 0, "no_match": 0, "no_album": 0, "no_cover": 0, "error": 0, "added": 0}

    for mp3 in unmatched:
        artist, title = parse_filename(mp3.name)
        safe_print(f"  resolve: {artist} - {title}")
        if args.dry_run:
            stats["ok"] += 1
            continue

        try:
            detail = resolve_song(artist, title, songs, canonical)
            if not detail or not (detail.get("albumName") or detail.get("album")):
                stats["no_match"] += 1
                safe_print(f"    [no_match] {mp3.name}")
                continue

            # Replace prior bad manifest entries for same file
            songs = [s for s in songs if s.get("_originalFile") != mp3.name and expected_filename(s) != mp3.name]
            detail = dict(detail)
            detail["_originalFile"] = mp3.name
            detail["_fixedBy"] = "fix-unmatched.py"
            songs.append(detail)
            stats["added"] += 1

            status = apply_tags_from_manifest(mp3, detail, dry_run=False)
            stats[status] = stats.get(status, 0) + 1
            safe_print(
                f"    [{status}] {mp3.name} -> {detail.get('albumName')} / {detail.get('albumArtist')}"
            )
        except Exception as e:
            stats["error"] += 1
            safe_print(f"    [error] {mp3.name}: {e}")

        time.sleep(args.delay)

    manifest["songs"] = songs
    manifest["fixedUnmatchedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    safe_print(f"stats: {stats}")
    return 0 if stats.get("error", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
