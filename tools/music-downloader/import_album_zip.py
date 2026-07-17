#!/usr/bin/env python3
"""
DoubleDouble（等）专辑 zip 导入
================================
解压 zip → 按 config.ALBUMS 中文轨名写入曲库 MP3 320k。
不覆盖已存在文件。主流整专主路径；Soulseek 见 downloader.py。

用法:
  python import_album_zip.py --zip path/to.zip --album 范特西
  python import_album_zip.py --zip path/to.zip --album 2002 --dry-run
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ALBUMS, ARTIST, MUSIC_DIR

_TOOL_DIR = Path(__file__).resolve().parent
_AUDIO_EXTS = {".flac", ".mp3", ".m4a", ".aac", ".wav", ".ogg"}
_COVER_NAMES = ("cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "Folder.jpg")


def find_album(query: str) -> dict:
    q = query.strip().lower()
    for album in ALBUMS:
        if q == album["year"] or q == album["name"].lower() or q == album["name_en"].lower():
            return album
        if q in album["name"].lower() or q in album["name_en"].lower():
            return album
    raise SystemExit(f"未找到专辑: {query!r}（可用年份或中英文名）")


def track_no_from_name(name: str) -> int | None:
    m = re.match(r"^(\d{1,2})\D", name.strip())
    if m:
        return int(m.group(1))
    return None


def collect_audio(root: Path) -> list[Path]:
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in _AUDIO_EXTS]
    def sort_key(p: Path):
        n = track_no_from_name(p.name)
        return (n if n is not None else 999, p.name.lower())
    return sorted(files, key=sort_key)


def find_cover(root: Path) -> Path | None:
    for p in root.rglob("*"):
        if p.is_file() and p.name in _COVER_NAMES:
            return p
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"} and "cover" in p.name.lower():
            return p
    return None


def dest_path(music_dir: Path, album: dict, track_no: int, title: str) -> Path:
    folder = music_dir / ARTIST / f"{album['year']} - {album['name']}"
    return folder / f"{track_no:02d} - {title}.mp3"


def ffmpeg_to_mp3(
    src: Path,
    dest: Path,
    *,
    album: dict,
    title: str,
    track_no: int,
    cover: Path | None,
    dry_run: bool,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta = [
        "-metadata", f"artist={ARTIST}",
        "-metadata", f"album_artist={ARTIST}",
        "-metadata", f"album={album['name']}",
        "-metadata", f"title={title}",
        "-metadata", f"track={track_no}",
        "-metadata", f"date={album['year']}",
    ]
    if dry_run:
        print(f"  [dry-run] {src.name} -> {dest}")
        return

    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if cover and cover.is_file():
        cmd += [
            "-i", str(cover),
            "-map", "0:a", "-map", "1:0",
            "-c:a", "libmp3lame", "-b:a", "320k",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            "-disposition:v", "attached_pic",
        ]
    else:
        cmd += ["-c:a", "libmp3lame", "-b:a", "320k"]
    cmd += meta + [str(dest)]
    subprocess.run(cmd, check=True, capture_output=True)


def extract_zip(zip_path: Path, out_dir: Path) -> Path:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Import DoubleDouble album zip into Navidrome library")
    parser.add_argument("--zip", required=True, help="专辑 zip 路径")
    parser.add_argument("--album", required=True, help="专辑名或年份（匹配 config.ALBUMS）")
    parser.add_argument("--music-dir", default=MUSIC_DIR, help="曲库根目录")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-extract", action="store_true", help="保留 _rt_test 解压目录")
    args = parser.parse_args()

    zip_path = Path(args.zip).expanduser().resolve()
    if not zip_path.is_file():
        raise SystemExit(f"zip 不存在: {zip_path}")

    album = find_album(args.album)
    music_dir = Path(args.music_dir).expanduser().resolve()
    extract_root = _TOOL_DIR / "_rt_test" / f"import_{album['year']}_{album['name']}"

    print(f"专辑: {album['year']} - {album['name']} ({len(album['tracks'])} 轨)")
    print(f"zip:  {zip_path}")
    print(f"解压: {extract_root}")

    if not args.dry_run:
        extract_zip(zip_path, extract_root)
    elif not extract_root.exists():
        # dry-run 仍需看内容：只列 zip 内音频名
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = [n for n in zf.namelist() if Path(n).suffix.lower() in _AUDIO_EXTS]
        print(f"zip 内音频 {len(names)} 个（dry-run 未解压）")
        for i, title in enumerate(album["tracks"], start=1):
            dest = dest_path(music_dir, album, i, title)
            exists = dest.is_file()
            print(f"  {i:02d} {title}: {'SKIP exists' if exists else 'would import'} -> {dest.name}")
        return

    audio = collect_audio(extract_root)
    cover = find_cover(extract_root)
    print(f"音频 {len(audio)} 个; 封面: {cover.name if cover else '无'}")

    tracks = album["tracks"]
    # 优先按文件名轨号对齐；否则按排序后的顺序填满
    by_no: dict[int, Path] = {}
    unordered: list[Path] = []
    for p in audio:
        n = track_no_from_name(p.name)
        if n is not None and 1 <= n <= len(tracks) and n not in by_no:
            by_no[n] = p
        else:
            unordered.append(p)

    used = set(by_no.values())
    ui = 0
    for i in range(1, len(tracks) + 1):
        if i not in by_no:
            while ui < len(unordered) and unordered[ui] in used:
                ui += 1
            if ui < len(unordered):
                by_no[i] = unordered[ui]
                used.add(unordered[ui])
                ui += 1

    imported = skipped = missing = 0
    for i, title in enumerate(tracks, start=1):
        dest = dest_path(music_dir, album, i, title)
        if dest.is_file():
            print(f"  SKIP {dest.name}")
            skipped += 1
            continue
        src = by_no.get(i)
        if src is None:
            print(f"  MISS {i:02d} - {title}")
            missing += 1
            continue
        print(f"  CONVERT {src.name} -> {dest.name}")
        try:
            ffmpeg_to_mp3(src, dest, album=album, title=title, track_no=i, cover=cover, dry_run=args.dry_run)
            imported += 1
        except subprocess.CalledProcessError as e:
            print(f"  FAIL ffmpeg: {e}", file=sys.stderr)

    print(f"完成: imported={imported} skipped={skipped} missing={missing}")
    if not args.dry_run and not args.keep_extract and extract_root.exists():
        shutil.rmtree(extract_root, ignore_errors=True)


if __name__ == "__main__":
    main()
