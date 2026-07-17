#!/usr/bin/env python3
"""
Soulseek 下载器（长尾兜底）
==========================
从 Soulseek P2P 搜索周杰伦专辑并排队下载。
主流整专优先用 DoubleDouble + import_album_zip.py（见 README）。

依赖: pip install requests
用法: python3 downloader.py                      # 下载所有专辑
      python3 downloader.py --album 七里香       # 下载指定专辑
      python3 downloader.py --album 2004          # 按年份下载
      python3 downloader.py --search-only         # 仅搜索，不下载
      python3 downloader.py --status              # 查看下载队列
"""
import argparse
import os
import sys
import time
import re

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    SLSKD_API, ALBUMS, SEARCH_KEYWORDS, SEARCH_TIMEOUT,
    MAX_FILES_PER_USER, PREFERRED_FORMATS,
    SEARCH_RETRIES, SEARCH_RETRY_DELAY, TRACK_ALIASES,
    MUSIC_DIR, ARTIST,
)


def api_get(path):
    r = requests.get(f"{SLSKD_API}{path}", timeout=30)
    r.raise_for_status()
    return r.json() if r.text else {}


def api_post(path, data=None):
    return requests.post(f"{SLSKD_API}{path}", json=data or {}, timeout=30)


def api_delete(path):
    return requests.delete(f"{SLSKD_API}{path}", timeout=15)


def is_jay_chou_file(filename):
    """判断文件名是否属于周杰伦（艺人名或曲目/专辑名）。"""
    name = filename.lower()
    for kw in SEARCH_KEYWORDS:
        if kw.lower() in name:
            return True
    for album in ALBUMS:
        if album["name"].lower() in name or album["name_en"].lower() in name:
            return True
        for track in album["tracks"]:
            if track.lower() in name:
                return True
    return False


def get_file_format(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower()


def check_server():
    try:
        app = api_get("/application")
        srv = app.get("server", {})
        state = srv.get("state", "?")
        connected = srv.get("isConnected", False)
        logged_in = srv.get("isLoggedIn", False)
        return connected and logged_in, state
    except requests.exceptions.ConnectionError:
        return False, "ConnectionRefused"


def clean_old_searches():
    try:
        searches = api_get("/searches")
    except Exception:
        return
    for s in searches or []:
        try:
            api_delete(f"/searches/{s['id']}")
        except Exception:
            pass


def _collect_jay_files(responses, seen_users, all_responses):
    if not responses:
        return
    for rd in responses:
        uname = rd.get("username", "")
        if not uname or uname in seen_users:
            continue
        seen_users.add(uname)
        files = rd.get("files", [])
        jay_files = [
            f for f in files
            if is_jay_chou_file(f.get("filename", f.get("name", "")))
            and get_file_format(f.get("filename", f.get("name", ""))) in PREFERRED_FORMATS
        ]
        if jay_files:
            all_responses.append((uname, jay_files))


def search_tracks(keyword, timeout=SEARCH_TIMEOUT, clean=True):
    """搜索关键词，返回 [(username, [file_dict, ...]), ...]。"""
    if clean:
        clean_old_searches()

    resp = api_post("/searches", {"searchText": keyword})
    if resp.status_code not in (200, 201):
        print(f"  [!] 搜索失败: {resp.status_code} {resp.text[:100]}")
        return []

    sid = resp.json()["id"]
    print(f"  [~] 搜索 ID: {sid}  (等待 {timeout}s...)")

    seen_users = set()
    all_responses = []
    deadline = time.time() + timeout
    last_count = 0

    while time.time() < deadline:
        time.sleep(2)
        try:
            s = api_get(f"/searches/{sid}")
        except Exception as e:
            print(f"    [!] 轮询失败: {e}")
            continue

        rc = s.get("responseCount", 0)
        if rc > last_count:
            try:
                r = api_get(f"/searches/{sid}/responses")
            except Exception:
                r = []
            _collect_jay_files(r, seen_users, all_responses)
            last_count = rc
            total = sum(len(f) for _, f in all_responses)
            print(f"    [{len(all_responses)} users, {total} files]", flush=True)

        state = str(s.get("state", ""))
        if "Completed" in state or "TimedOut" in state:
            try:
                r = api_get(f"/searches/{sid}/responses")
            except Exception:
                r = []
            _collect_jay_files(r, seen_users, all_responses)
            break

    return all_responses


def search_with_retries(keywords, albums=None):
    """专辑优先，再广搜艺人；合并命中。"""
    albums = albums or []
    queries = []
    for album in albums:
        queries.append(f"周杰伦 {album['name']} mp3")
        queries.append(f"Jay Chou {album['name_en']} mp3")
        queries.append(f"周杰伦 {album['name']}")
        queries.append(f"Jay Chou {album['name_en']}")
    queries.extend(keywords)

    seen_q = set()
    uniq = []
    for q in queries:
        if q not in seen_q:
            seen_q.add(q)
            uniq.append(q)

    merged = []
    seen_users = set()

    for attempt in range(1, SEARCH_RETRIES + 1):
        print(f"\n=== 搜索轮次 {attempt}/{SEARCH_RETRIES} ===")
        for i, keyword in enumerate(uniq):
            print(f"\n[1/3] 搜索 '{keyword}'...")
            results = search_tracks(keyword, clean=(attempt == 1 and i == 0))
            for username, files in results:
                if username in seen_users:
                    existing = next((f for u, f in merged if u == username), None)
                    if existing is not None:
                        known = {
                            f.get("filename", f.get("name", "")) for f in existing
                        }
                        for f in files:
                            fn = f.get("filename", f.get("name", ""))
                            if fn not in known:
                                existing.append(f)
                    continue
                seen_users.add(username)
                merged.append((username, list(files)))

            # 继续搜完全部关键词，尽量凑齐 MP3

        if merged:
            return merged
        if attempt < SEARCH_RETRIES:
            print(f"  无结果，{SEARCH_RETRY_DELAY}s 后重试...")
            time.sleep(SEARCH_RETRY_DELAY)
    return merged


def download_from_user(username, files):
    if not files:
        return 0

    def fmt_rank(f):
        ext = get_file_format(f.get("filename", f.get("name", "")))
        try:
            return PREFERRED_FORMATS.index(ext)
        except ValueError:
            return 99

    files = sorted(files, key=fmt_rank)
    payload = [
        {
            "filename": f.get("filename", f.get("name", "")),
            "size": f.get("size", 0),
        }
        for f in files[:MAX_FILES_PER_USER]
    ]

    resp = api_post(f"/transfers/downloads/{username}", payload)
    if resp.status_code == 201:
        result = resp.json()
        queued = result.get("enqueued", [])
        ignored = result.get("ignored", []) or result.get("errored", []) or []
        if ignored:
            print(f"    ! 忽略 {len(ignored)} 个文件")
            for ig in ignored[:5]:
                print(f"      - {str(ig)[-80:]}")
        if queued:
            print(f"    ✓ 已排队 {len(queued)} 个文件从 {username}")
            for q in queued:
                fn = q.get("filename", "?")[-50:]
                print(f"      → {fn}")
        return len(queued)
    if resp.status_code == 409:
        print(f"    - 已存在队列中: {username}")
        return 0
    print(f"    ✗ 排队失败 {username}: {resp.status_code} {resp.text[:120]}")
    return 0


def iter_transfer_files(transfers):
    """展开 slskd downloads API 的嵌套结构为文件列表。"""
    files = []
    if not transfers:
        return files
    for user in transfers:
        for directory in user.get("directories") or []:
            for f in directory.get("files") or []:
                files.append(f)
    return files


def show_transfer_status():
    try:
        transfers = api_get("/transfers/downloads")
    except Exception:
        print("  (无法获取传输状态)")
        return

    files = iter_transfer_files(transfers)
    if not files:
        print("  当前无下载任务")
        return

    by_state = {}
    for t in files:
        state = t.get("state", "?")
        by_state[state] = by_state.get(state, 0) + 1

    print(f"  传输任务总数: {len(files)}")
    for s, c in sorted(by_state.items()):
        print(f"    {s}: {c}")

    for t in files:
        s = t.get("state", "")
        if any(x in s for x in ("Progress", "Queued", "InProgress", "Initializing", "Transferring")):
            fn = t.get("filename", "?")[-60:]
            pct = t.get("percentComplete", 0) or 0
            sp = t.get("averageSpeed", 0) or 0
            print(f"    ⏳ {fn}  {pct:.0f}%  {sp // 1024}KB/s")


def track_already_in_library(album: dict, track_no: int, track: str) -> bool:
    """曲库中已有该曲（任意常见音频后缀）则跳过。"""
    album_dir = os.path.join(
        MUSIC_DIR, ARTIST, f"{album['year']} - {album['name']}"
    )
    if not os.path.isdir(album_dir):
        return False
    prefixes = [f"{track_no:02d} - {track}", f"{track_no:02d}-{track}", track]
    for name in os.listdir(album_dir):
        base, ext = os.path.splitext(name)
        if ext.lower() not in (".mp3", ".flac", ".m4a", ".ogg", ".wav"):
            continue
        for p in prefixes:
            if base == p or base.startswith(p) or p in base:
                return True
        if filename_matches_track(name, track):
            return True
    return False


def track_name_variants(track: str) -> list[str]:
    names = [track]
    names.extend(TRACK_ALIASES.get(track, []))
    return names


def filename_matches_track(filename: str, track: str) -> bool:
    fn = filename.lower()
    for name in track_name_variants(track):
        if name.lower() in fn:
            return True
    return False


def match_album_files(responses):
    album_map = {}
    for album in ALBUMS:
        variants = []
        for t in album["tracks"]:
            variants.extend(track_name_variants(t))
        track_pattern = "|".join(re.escape(t) for t in variants)
        album_map[album["name"]] = {
            "info": album,
            "pattern": re.compile(track_pattern, re.IGNORECASE),
            "matches": [],
        }

    for username, files in responses:
        for f in files:
            fn = f.get("filename", f.get("name", ""))
            for aname, info in album_map.items():
                if info["pattern"].search(fn):
                    info["matches"].append((username, f))
                    break
    return album_map


def main():
    parser = argparse.ArgumentParser(description="Soulseek 周杰伦专辑下载器")
    parser.add_argument("--album", "-a", help="指定专辑名或年份")
    parser.add_argument("--search-only", "-s", action="store_true",
                        help="仅搜索，不下载")
    parser.add_argument("--status", "-st", action="store_true",
                        help="查看下载状态")
    args = parser.parse_args()

    if args.status:
        show_transfer_status()
        return

    ok, state = check_server()
    if not ok:
        print(f"[!] slskd 未就绪 (state={state})")
        print("    请先启动: docker compose up -d")
        sys.exit(1)
    print(f"[✓] slskd 已连接 (state={state})")

    target_albums = ALBUMS
    if args.album:
        filtered = [
            a for a in ALBUMS
            if args.album in (a["name"], a["name_en"], a["year"])
        ]
        if filtered:
            target_albums = filtered
            print(f"[i] 仅下载专辑: {', '.join(a['name'] for a in target_albums)}")
        else:
            print(f"[!] 未找到专辑: {args.album}")
            album_list = ", ".join(f"{a['year']} - {a['name']}" for a in ALBUMS)
            print(f"    可选: {album_list}")
            sys.exit(1)

    all_responses = search_with_retries(SEARCH_KEYWORDS, albums=target_albums)

    # 专辑搜不到足够 MP3 时，按缺失曲目补搜
    if not args.search_only:
        for album in target_albums:
            missing_tracks = [
                t for i, t in enumerate(album["tracks"])
                if not track_already_in_library(album, i + 1, t)
            ]
            if not missing_tracks:
                continue
            # 已有结果覆盖多少
            covered = set()
            for _, files in all_responses:
                for f in files:
                    fn = f.get("filename", f.get("name", ""))
                    for t in missing_tracks:
                        if filename_matches_track(fn, t):
                            covered.add(t)
            still = [t for t in missing_tracks if t not in covered]
            for track in still[:5]:  # 每专最多补搜 5 首，避免过慢
                q = f"周杰伦 {track} mp3"
                print(f"\n[补搜] '{q}'...")
                extra = search_tracks(q, clean=False)
                all_responses.extend(extra)
    if not all_responses:
        print("\n[!] 未找到在线用户分享的周杰伦歌曲。")
        print("    Soulseek 是 P2P 网络，需要等待有资源的用户在线。")
        print("    建议过段时间再试。")
        sys.exit(0)

    print(f"\n[2/3] 归类搜索结果（{sum(len(f) for _, f in all_responses)} 个文件）...")
    album_map = match_album_files(all_responses)
    target_names = {a["name"] for a in target_albums}
    for aname, info in album_map.items():
        if aname not in target_names:
            info["matches"] = []
        elif info["matches"]:
            users = set(m[0] for m in info["matches"])
            print(f"  {info['info']['year']} - {aname}: "
                  f"{len(info['matches'])} 个文件, 来自 {len(users)} 个用户")

    if args.search_only:
        print("\n[✓] 搜索完成（--search-only 模式）")
        return

    print("\n[3/3] 排队下载...")
    total_queued = 0
    for aname, info in album_map.items():
        if not info["matches"]:
            continue

        album = info["info"]
        tracks = album["tracks"]
        by_user = {}
        for username, f in info["matches"]:
            by_user.setdefault(username, []).append(f)

        print(f"\n  专辑 {album['year']} - {aname}:")
        missing = [
            i for i, t in enumerate(tracks)
            if not track_already_in_library(album, i + 1, t)
        ]
        if not missing:
            print("    曲库已齐全，跳过")
            continue
        print(f"    需补 {len(missing)}/{len(tracks)} 曲（跳过已有）")

        # 优先选覆盖缺失曲目最多的用户
        ranked = []
        for username, files in by_user.items():
            covered = set()
            for f in files:
                fn = f.get("filename", f.get("name", "")).lower()
                for i in missing:
                    if filename_matches_track(fn, tracks[i]):
                        covered.add(i)
            ranked.append((len(covered), -len(files), username, files, covered))
        ranked.sort(reverse=True)

        queued_album = 0
        for cover_count, _, username, files, covered in ranked[:3]:
            if cover_count == 0:
                continue
            print(f"    选用 {username}（覆盖缺失 {cover_count}/{len(missing)} 曲）")
            best_by_track = {}
            for f in files:
                fn = f.get("filename", f.get("name", ""))
                for i in missing:
                    track = tracks[i]
                    if not filename_matches_track(fn, track):
                        continue
                    ext = get_file_format(fn)
                    try:
                        rank = PREFERRED_FORMATS.index(ext)
                    except ValueError:
                        continue
                    prev = best_by_track.get(i)
                    if prev is None or rank < prev[0]:
                        best_by_track[i] = (rank, f)
                    break
            selected = [pair[1] for pair in best_by_track.values()]
            if not selected:
                print("    无可用 MP3 源，试下一用户")
                continue
            queued_album += download_from_user(username, selected)
            if queued_album > 0:
                break
        if queued_album == 0:
            print("    未排到 MP3")
        total_queued += queued_album

    print(f"\n{'='*50}")
    print(f"完成！共排队 {total_queued} 个文件")
    print("下载完成后运行: python3 organizer.py")
    print("查看状态: python3 downloader.py --status")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
