"""Shared filename rules and MP3 tag/cover helpers for deploy scripts."""
from __future__ import annotations

import re
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    name = INVALID_CHARS.sub("_", name).strip()
    return name[:200] if len(name) > 200 else name


def expected_filename(song: dict[str, Any]) -> str:
    artist = song.get("artist") or "Unknown"
    title = song.get("name") or str(song.get("id", "unknown"))
    return sanitize_filename(f"{artist} - {title}.mp3")


def album_display_name(song: dict[str, Any]) -> str:
    album = (song.get("albumName") or song.get("album") or "").strip()
    if album:
        return album
    artist = (song.get("artist") or "").strip()
    return artist or "单曲"


def download_cover_bytes(pic_url: str, timeout: int = 30) -> bytes | None:
    if not pic_url:
        return None
    url = pic_url
    if url.endswith("?param="):
        url = url + "300y300"
    elif "?" not in url:
        url = url + "?param=300y300"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return data if len(data) > 500 else None
    except Exception:
        return None


def mp3_has_cover(tags: Any) -> bool:
    from mutagen.id3 import ID3

    if tags is None:
        return False
    for key in tags.keys():
        if key.startswith("APIC"):
            return True
    return False


def mp3_tags_match(song: dict[str, Any], tags: Any) -> bool:
    if tags is None:
        return False
    title = (tags.get("TIT2") or tags.get("\xa9nam"))
    artist = (tags.get("TPE1") or tags.get("\xa9ART"))
    album = (tags.get("TALB") or tags.get("\xa9alb"))
    if not title or not artist:
        return False
    t = str(title.text[0] if hasattr(title, "text") else title)
    a = str(artist.text[0] if hasattr(artist, "text") else artist)
    al = str(album.text[0] if album and hasattr(album, "text") else (album or ""))
    return (
        t == (song.get("name") or "")
        and a == (song.get("artist") or "")
        and al == album_display_name(song)
        and mp3_has_cover(tags)
    )


def apply_tags_from_manifest(mp3_path: Path, song: dict[str, Any], *, dry_run: bool = False) -> str:
    """Write UTF-8 ID3v2.4 tags + APIC cover. Returns: ok | skipped | no_cover | error."""
    from mutagen.id3 import APIC, ID3, TALB, TPE1, TIT2, ID3NoHeaderError

    if dry_run:
        return "ok"

    try:
        try:
            tags = ID3(mp3_path)
        except ID3NoHeaderError:
            tags = ID3()

        if mp3_tags_match(song, tags):
            return "skipped"

        tags.delall("TIT2")
        tags.delall("TPE1")
        tags.delall("TALB")
        tags.delall("APIC")

        tags.add(TIT2(encoding=3, text=song.get("name") or ""))
        tags.add(TPE1(encoding=3, text=song.get("artist") or "Unknown"))
        tags.add(TALB(encoding=3, text=album_display_name(song)))

        pic_url = song.get("albumPicUrl") or song.get("picUrl") or ""
        cover = download_cover_bytes(pic_url)
        if cover:
            mime = "image/jpeg"
            if cover[:4] == b"\x89PNG":
                mime = "image/png"
            tags.add(
                APIC(
                    encoding=3,
                    mime=mime,
                    type=3,
                    desc="Cover",
                    data=cover,
                )
            )
        else:
            tags.save(mp3_path, v2_version=4)
            return "no_cover"

        tags.save(mp3_path, v2_version=4)
        return "ok"
    except Exception:
        return "error"
