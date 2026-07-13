"""Shared filename rules and MP3 tag/cover helpers for deploy scripts."""
from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path
from typing import Any

# Avoid local HTTP proxy breaking NetEase API / cover downloads.
for _env_key in list(os.environ):
    if "proxy" in _env_key.lower():
        os.environ.pop(_env_key, None)

INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    name = INVALID_CHARS.sub("_", name).strip()
    return name[:200] if len(name) > 200 else name


def expected_filename(song: dict[str, Any]) -> str:
    artist = song.get("artist") or "Unknown"
    title = song.get("name") or str(song.get("id", "unknown"))
    return sanitize_filename(f"{artist} - {title}.mp3")


def primary_artist_name(artist: str) -> str:
    return (artist or "").split(" / ")[0].strip()


def album_display_name(song: dict[str, Any]) -> str:
    """Return NetEase album name only; empty if manifest has no album (do not fallback to artist)."""
    return (song.get("albumName") or song.get("album") or "").strip()


def album_artist_name(song: dict[str, Any]) -> str:
    explicit = (song.get("albumArtist") or "").strip()
    if explicit:
        return explicit
    return primary_artist_name(song.get("artist") or "")


def tag_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "text"):
        return str(value.text[0]) if value.text else ""
    return str(value)


def read_mp3_tag_fields(mp3_path: Path) -> dict[str, Any]:
    from mutagen.id3 import ID3, ID3NoHeaderError

    try:
        tags = ID3(mp3_path)
    except (ID3NoHeaderError, Exception):
        tags = None

    if tags is None:
        return {
            "title": "",
            "artist": "",
            "album": "",
            "album_artist": "",
            "compilation": False,
            "has_cover": False,
        }

    tcmp = tags.get("TCMP")
    compilation = False
    if tcmp is not None:
        val = tag_text(tcmp).lower()
        compilation = val in ("1", "true")

    return {
        "title": tag_text(tags.get("TIT2")),
        "artist": tag_text(tags.get("TPE1")),
        "album": tag_text(tags.get("TALB")),
        "album_artist": tag_text(tags.get("TPE2")),
        "compilation": compilation,
        "has_cover": mp3_has_cover(tags),
    }


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
    if tags is None:
        return False
    for key in tags.keys():
        if key.startswith("APIC"):
            return True
    return False


def mp3_has_compilation(tags: Any) -> bool:
    if tags is None:
        return False
    tcmp = tags.get("TCMP")
    if tcmp is None:
        return False
    val = tag_text(tcmp).lower()
    return val in ("1", "true")


def mp3_tags_match(song: dict[str, Any], tags: Any) -> bool:
    if tags is None:
        return False
    title = tags.get("TIT2")
    artist = tags.get("TPE1")
    album = tags.get("TALB")
    album_artist = tags.get("TPE2")
    if not title or not artist or not album or not album_artist:
        return False
    if mp3_has_compilation(tags):
        return False

    expected_album = album_display_name(song)
    if not expected_album:
        return False

    t = tag_text(title)
    a = tag_text(artist)
    al = tag_text(album)
    aa = tag_text(album_artist)
    return (
        t == (song.get("name") or "")
        and a == (song.get("artist") or "")
        and al == expected_album
        and aa == album_artist_name(song)
        and mp3_has_cover(tags)
    )


def apply_tags_from_manifest(mp3_path: Path, song: dict[str, Any], *, dry_run: bool = False) -> str:
    """Write UTF-8 ID3v2.4 tags + APIC cover. Returns: ok | skipped | no_album | no_cover | error."""
    from mutagen.id3 import APIC, ID3, TALB, TPE1, TPE2, TIT2, ID3NoHeaderError

    album_name = album_display_name(song)
    if not album_name:
        return "no_album"

    album_artist = album_artist_name(song)
    if not album_artist:
        return "no_album"

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
        tags.delall("TPE2")
        tags.delall("TCMP")
        tags.delall("APIC")

        tags.add(TIT2(encoding=3, text=song.get("name") or ""))
        tags.add(TPE1(encoding=3, text=song.get("artist") or "Unknown"))
        tags.add(TALB(encoding=3, text=album_name))
        tags.add(TPE2(encoding=3, text=album_artist))

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
