#!/usr/bin/env python3
"""
将 deploy/music/liked/ 中已有的周杰伦曲目，按专辑整理到
MUSIC_DIR/周杰伦/{year} - {album}/，并写入 ID3（不访问网易云下载）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ALBUMS, ARTIST, MUSIC_DIR, TRACK_ALIASES

DEPLOY_SCRIPTS = Path(__file__).resolve().parents[2] / "deploy" / "scripts"
sys.path.insert(0, str(DEPLOY_SCRIPTS))
from tag_utils import read_mp3_tag_fields  # noqa: E402


def variants(track: str) -> list[str]:
    names = [track, *TRACK_ALIASES.get(track, [])]
    # 反查：别名指向主名
    for k, vs in TRACK_ALIASES.items():
        if track in vs or track == k:
            names.append(k)
            names.extend(vs)
    # 去重保序
    out = []
    seen = set()
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def build_track_index():
    idx = {}
    for album in ALBUMS:
        album_label = album.get("netease_album_name") or album["name"]
        for i, track in enumerate(album["tracks"], start=1):
            for name in variants(track):
                idx[name] = {
                    "track": track,
                    "track_no": i,
                    "year": album["year"],
                    "folder_album": album["name"],
                    "albumName": album_label,
                    "album": album_label,
                    "name": track,
                    "artist": ARTIST,
                    "albumArtist": ARTIST,
                    "albumPicUrl": "",
                }
    return idx


def find_liked_files(liked: Path) -> list[Path]:
    if not liked.is_dir():
        return []
    return sorted(liked.glob(f"{ARTIST} - *.mp3"))


def match_song(path: Path, idx: dict) -> dict | None:
    tags = read_mp3_tag_fields(path)
    title = (tags.get("title") or "").strip()
    stem = path.stem
    if stem.startswith(f"{ARTIST} - "):
        stem_title = stem[len(f"{ARTIST} - ") :]
    else:
        stem_title = stem

    for key in (title, stem_title):
        if key in idx:
            return idx[key]
        for name, meta in idx.items():
            if name in key or key in name:
                return meta
    return None


def target_path(meta: dict, ext: str = ".mp3") -> Path:
    album_dir = Path(MUSIC_DIR) / ARTIST / f"{meta['year']} - {meta['folder_album']}"
    fname = f"{meta['track_no']:02d} - {meta['name']}{ext}"
    for ch in '<>:"/\\|?*':
        fname = fname.replace(ch, "_")
    return album_dir / fname


def write_text_tags(mp3_path: Path, meta: dict) -> str:
    """只写文本标签，保留已有 APIC，不访问外网。"""
    from mutagen.id3 import ID3, TALB, TPE1, TPE2, TIT2, ID3NoHeaderError

    try:
        try:
            tags = ID3(mp3_path)
        except ID3NoHeaderError:
            tags = ID3()
        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.delall("TALB")
        tags.delall("TPE2")
        tags.delall("TCMP")
        tags.add(TIT2(encoding=3, text=meta["name"]))
        tags.add(TPE1(encoding=3, text=meta["artist"]))
        tags.add(TALB(encoding=3, text=meta["albumName"]))
        tags.add(TPE2(encoding=3, text=meta["albumArtist"]))
        tags.save(mp3_path, v2_version=4)
        return "ok"
    except Exception as e:
        return f"error:{e}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", "-n", action="store_true")
    args = parser.parse_args()

    liked = Path(MUSIC_DIR) / "liked"
    idx = build_track_index()
    files = find_liked_files(liked)
    print(f"liked 周杰伦文件: {len(files)}")

    copied = 0
    skipped = 0
    unmatched = 0
    for src in files:
        meta = match_song(src, idx)
        if not meta:
            unmatched += 1
            continue
        dest = target_path(meta)
        if dest.exists() and dest.stat().st_size > 100_000:
            # 仍校正标签
            if not args.dry_run:
                write_text_tags(dest, meta)
            skipped += 1
            continue
        print(f"  {src.name} -> {dest.relative_to(MUSIC_DIR)}")
        if args.dry_run:
            copied += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        status = write_text_tags(dest, meta)
        print(f"    tag={status}")
        copied += 1

    print(f"完成: copied={copied} skipped={skipped} unmatched={unmatched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
