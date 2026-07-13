#!/usr/bin/env python3
"""Audit MP3 ID3 tags against manifest; report issues for Navidrome album grouping."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tag_utils import album_artist_name, album_display_name, expected_filename, read_mp3_tag_fields

DEPLOY = Path(__file__).resolve().parent.parent
LIKED_DIR = DEPLOY / "music" / "liked"
DEFAULT_MANIFEST = DEPLOY / "playlist-enriched.json"
FALLBACK_MANIFEST = DEPLOY / "playlist-157658592.json"
DEFAULT_SUBSET = DEPLOY / "playlist-latest1000.json"
REPORT_PATH = DEPLOY / "audit-tags-report.json"


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))


def tag_text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "text"):
        return str(value.text[0]) if value.text else ""
    return str(value)


def load_manifest(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("songs") or []


def subset_ids(path: Path | None) -> set[str] | None:
    if not path or not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)
    raw = meta.get("trackIds") or meta.get("ids") or meta.get("songs") or meta
    if not raw:
        return None
    if isinstance(raw[0], dict):
        return {str(x["id"]) for x in raw}
    return {str(x) for x in raw}


def primary_artist(artist: str) -> str:
    return (artist or "").split(" / ")[0].strip()


def is_fake_album(album: str, artist: str) -> bool:
    if not album:
        return True
    if album in ("单曲", "[Unknown Album]"):
        return True
    if artist and album == primary_artist(artist):
        return True
    return False


def audit_file(mp3: Path, song: dict | None) -> dict:
    fields = read_mp3_tag_fields(mp3)
    issues: list[str] = []

    title = fields["title"]
    artist = fields["artist"]
    album = fields["album"]
    album_artist = fields["album_artist"]
    compilation = fields["compilation"]
    has_cover = fields["has_cover"]

    if not title:
        issues.append("missing_TIT2")
    if not artist:
        issues.append("missing_TPE1")
    if not album:
        issues.append("missing_TALB")
    if not album_artist:
        issues.append("missing_TPE2")
    if compilation:
        issues.append("TCMP_set")
    if not has_cover:
        issues.append("missing_APIC")

    if song:
        expected_album = album_display_name(song)
        expected_aa = album_artist_name(song)
        if expected_album and album != expected_album:
            issues.append("TALB_mismatch")
        if expected_aa and album_artist != expected_aa:
            issues.append("TPE2_mismatch")
        if not expected_album:
            issues.append("manifest_no_album")
        if is_fake_album(album, artist):
            issues.append("fake_album_name")
    else:
        issues.append("unmatched")
        if is_fake_album(album, artist):
            issues.append("fake_album_name")

    return {
        "file": mp3.name,
        "id": str(song["id"]) if song else None,
        "title": title,
        "artist": artist,
        "album": album,
        "album_artist": album_artist or "",
        "compilation": compilation,
        "has_cover": has_cover,
        "expected_album": album_display_name(song) if song else "",
        "expected_album_artist": album_artist_name(song) if song else "",
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit MP3 tags vs manifest for Navidrome")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--liked-dir", type=Path, default=LIKED_DIR)
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET, help="limit audit to manifest ids")
    parser.add_argument("--no-subset", action="store_true", help="audit all local MP3s")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--sample", type=int, default=0, help="print first N issue rows")
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else DEPLOY / args.manifest
    if not manifest_path.is_file():
        manifest_path = FALLBACK_MANIFEST

    songs = load_manifest(manifest_path)
    by_name = {expected_filename(s): s for s in songs}
    ids_filter = None if args.no_subset else subset_ids(
        args.subset if args.subset.is_absolute() else DEPLOY / args.subset
    )

    liked_dir = args.liked_dir if args.liked_dir.is_absolute() else DEPLOY / args.liked_dir
    mp3_files = sorted(liked_dir.glob("*.mp3"))

    rows: list[dict] = []
    issue_counter: Counter = Counter()
    album_groups: dict[tuple[str, str], list[str]] = defaultdict(list)

    for mp3 in mp3_files:
        song = by_name.get(mp3.name)
        if song and ids_filter is not None and str(song["id"]) not in ids_filter:
            continue
        if not song and ids_filter is not None:
            # unmatched files still in liked dir — include in audit
            pass

        row = audit_file(mp3, song)
        rows.append(row)
        for issue in row["issues"]:
            issue_counter[issue] += 1
        key = (row["album_artist"] or row["artist"] or "?", row["album"] or "?")
        album_groups[key].append(mp3.name)

    fragmented = [
        {"album_artist": k[0], "album": k[1], "tracks": v}
        for k, v in sorted(album_groups.items())
        if len(v) == 1 and k[1] not in ("?", "")
    ]

    jay_samples = [
        r for r in rows
        if r.get("artist") and "周杰伦" in r["artist"]
    ][:6]

    report = {
        "manifest": str(manifest_path),
        "mp3_count": len(rows),
        "issue_counts": dict(issue_counter),
        "unmatched_files": [r["file"] for r in rows if "unmatched" in r["issues"]],
        "fragmented_albums_sample": fragmented[:30],
        "fragmented_album_count": len(fragmented),
        "jay_chou_sample": jay_samples,
        "rows": rows,
    }

    report_path = args.report if args.report.is_absolute() else DEPLOY / args.report
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    safe_print(f"audited={len(rows)} manifest={manifest_path.name}")
    safe_print("issue_counts:")
    for k, v in sorted(issue_counter.items(), key=lambda x: -x[1]):
        safe_print(f"  {k}: {v}")
    safe_print(f"unmatched: {len(report['unmatched_files'])}")
    safe_print(f"fragmented single-track albums: {len(fragmented)}")
    safe_print(f"report -> {report_path}")

    if args.sample:
        shown = 0
        for r in rows:
            if r["issues"]:
                safe_print(f"  {r['file']}: {','.join(r['issues'])}")
                shown += 1
                if shown >= args.sample:
                    break

    return 0


if __name__ == "__main__":
    sys.exit(main())
