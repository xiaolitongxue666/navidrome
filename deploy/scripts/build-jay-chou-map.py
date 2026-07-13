#!/usr/bin/env python3
"""Build canonical Jay Chou song title -> NetEase metadata mapping from official albums."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent.parent
OUT_PATH = DEPLOY / "data" / "jay-chou-canonical.json"

# Studio albums first (higher priority); compilations last.
ALBUM_IDS = [
    18918,  # Jay
    18915,  # 范特西
    18907,  # 八度空间
    18905,  # 叶惠美
    18903,  # 七里香
    18896,  # 11月的萧邦
    18893,  # 依然范特西
    18886,  # 我很忙
    18877,  # 魔杰座
    18875,  # 跨时代
    18869,  # 惊叹号
    2263029,  # 十二新作
    3084335,  # 哎呦，不错哦
    34720827,  # 周杰伦的床边故事
    18888,  # 不能说的秘密 电影原声带
    18904,  # 寻找周杰伦
    18895,  # 霍元甲
    18898,  # Initial J (lowest — may duplicate titles)
]

# Fallback when album API returns no track list (e.g. 11月的萧邦).
MANUAL_SONG_IDS: dict[str, int] = {
    "夜曲": 185904,
    "发如雪": 185906,
    "黑色毛衣": 185908,
    "枫": 185912,
    "浪漫手机": 185914,
    "珊瑚海": 185920,
    "一路向北": 185924,
    "蓝色风暴": 185905,
    "四面楚歌": 185910,
    "逆鳞": 185916,
    "麦芽糖": 185918,
    "飘移": 185922,
}


def fetch_album(album_id: int, retries: int = 3) -> dict:
    url = f"https://music.163.com/api/album/{album_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    last: dict = {}
    for attempt in range(retries):
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        album = data.get("album") or {}
        if album.get("songs"):
            return album
        last = album
        time.sleep(0.5 * (attempt + 1))
    return last


def fetch_songs(ids: list[str]) -> list[dict]:
    url = f"https://music.163.com/api/song/detail/?ids=[{','.join(ids)}]"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8")).get("songs") or []


def song_entry(s: dict, album_name: str = "", album_pic: str = "") -> dict:
    album = s.get("album") or {}
    artists = " / ".join(a.get("name", "") for a in (s.get("artists") or []))
    return {
        "id": str(s["id"]),
        "name": s.get("name") or "",
        "artist": artists,
        "albumName": album_name or album.get("name") or "",
        "album": album_name or album.get("name") or "",
        "albumPicUrl": album_pic or album.get("picUrl") or "",
        "albumArtist": "周杰伦",
    }


def main() -> int:
    mapping: dict[str, dict] = {}

    for album_id in ALBUM_IDS:
        album = fetch_album(album_id)
        album_name = album.get("name") or ""
        album_pic = album.get("picUrl") or ""
        count = 0
        for s in album.get("songs") or []:
            artists = [a.get("name", "") for a in (s.get("artists") or [])]
            if not any("周杰伦" in a for a in artists):
                continue
            title = (s.get("name") or "").strip()
            if not title:
                continue
            if title in mapping:
                continue
            mapping[title] = song_entry(s, album_name, album_pic)
            count += 1
        print(f"{album_id} {album_name} -> {count} new tracks")
        time.sleep(0.35)

    for title, song_id in MANUAL_SONG_IDS.items():
        if title in mapping and mapping[title].get("albumName"):
            continue
        songs = fetch_songs([str(song_id)])
        if not songs:
            continue
        s = songs[0]
        artists = [a.get("name", "") for a in (s.get("artists") or [])]
        if not any("周杰伦" in a for a in artists):
            continue
        mapping[title] = song_entry(s)
        print(f"manual {title} -> {mapping[title]['albumName']}")
        time.sleep(0.15)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"songs": mapping, "count": len(mapping)}, f, ensure_ascii=False, indent=2)

    print(f"written {len(mapping)} songs -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
