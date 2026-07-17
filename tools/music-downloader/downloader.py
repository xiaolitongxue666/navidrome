#!/usr/bin/env python3
"""
Soulseek 下载器
===============
从 Soulseek P2P 网络搜索周杰伦专辑并排队下载。

依赖: pip install requests
用法: python3 downloader.py                      # 下载所有专辑
      python3 downloader.py --album 七里香       # 下载指定专辑
      python3 downloader.py --album 2004          # 按年份下载
      python3 downloader.py --search             # 仅搜索，不下载
"""
import argparse
import json
import os
import sys
import time
import re

import requests

# 添加项目根到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    SLSKD_API, ALBUMS, SEARCH_KEYWORDS, SEARCH_TIMEOUT,
    MAX_FILES_PER_USER, PREFERRED_FORMATS,
)

# ── API 辅助 ──────────────────────────────────────────────

def api_get(path):
    """GET 请求 slskd API。"""
    r = requests.get(f"{SLSKD_API}{path}", timeout=10)
    r.raise_for_status()
    return r.json() if r.text else {}

def api_post(path, data=None):
    """POST 请求 slskd API。"""
    r = requests.post(f"{SLSKD_API}{path}", json=data or {}, timeout=10)
    return r

def api_delete(path):
    """DELETE 请求 slskd API。"""
    r = requests.delete(f"{SLSKD_API}{path}", timeout=10)
    return r

# ── 工具函数 ──────────────────────────────────────────────

def is_jay_chou_file(filename):
    """判断文件名是否属于周杰伦。"""
    name = filename.lower()
    for kw in SEARCH_KEYWORDS:
        if kw.lower() in name:
            return True
    return False

def get_file_format(filename):
    """获取文件扩展名。"""
    _, ext = os.path.splitext(filename)
    return ext.lower()

def format_size(n):
    """可读的文件大小。"""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

# ── 核心功能 ──────────────────────────────────────────────

def check_server():
    """检查 slskd 连接状态。"""
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
    """清理旧的搜索结果，避免干扰。"""
    for s in api_get("/searches"):
        try:
            api_delete(f"/searches/{s['id']}")
        except Exception:
            pass

def search_tracks(keyword, timeout=SEARCH_TIMEOUT):
    """
    搜索关键词，实时收集响应。
    返回: [(username, [file_dict, ...]), ...]
    """
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
        s = api_get(f"/searches/{sid}")
        rc = s.get("responseCount", 0)

        if rc > last_count:
            r = api_get(f"/searches/{sid}/responses")
            if r:
                for rd in r:
                    uname = rd.get("username", "")
                    if uname and uname not in seen_users:
                        seen_users.add(uname)
                        files = rd.get("files", [])
                        # 筛选：只保留 Jay Chou 的音频文件
                        jay_files = [
                            f for f in files
                            if is_jay_chou_file(
                                f.get("filename", f.get("name", ""))
                            ) and get_file_format(
                                f.get("filename", f.get("name", ""))
                            ) in PREFERRED_FORMATS
                        ]
                        if jay_files:
                            all_responses.append((uname, jay_files))
                last_count = rc
                total = sum(len(f) for _, f in all_responses)
                print(f"    [{len(all_responses)} users, {total} files]", flush=True)

        state = s.get("state", "")
        if "Completed" in state or "TimedOut" in state:
            break

    return all_responses


def download_from_user(username, files):
    """
    从一个用户排队下载文件。
    返回: 成功排队的数量
    """
    if not files:
        return 0

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
        if queued:
            print(f"    ✓ 已排队 {len(queued)} 个文件从 {username}")
            for q in queued:
                fn = q.get("filename", "?")[-50:]
                print(f"      → {fn}")
        return len(queued)
    elif resp.status_code == 409:
        print(f"    - 已存在队列中: {username}")
        return 0
    else:
        print(f"    ✗ 排队失败 {username}: {resp.status_code}")
        return 0


def show_transfer_status():
    """显示当前下载队列状态。"""
    try:
        transfers = api_get("/transfers/downloads")
    except Exception:
        print("  (无法获取传输状态)")
        return

    if not transfers:
        print("  当前无下载任务")
        return

    by_state = {}
    for t in transfers:
        state = t.get("state", "?")
        by_state[state] = by_state.get(state, 0) + 1

    print(f"  传输记录总数: {len(transfers)}")
    for s, c in sorted(by_state.items()):
        print(f"    {s}: {c}")

    # 显示进行中的
    for t in transfers:
        s = t.get("state", "")
        if "Progress" in s or "Queued" in s:
            fn = t.get("filename", "?")[-50:]
            tr = t.get("bytesTransferred", 0)
            sz = t.get("size", 0)
            sp = t.get("averageSpeed", 0)
            pct = (tr / sz * 100) if sz > 0 else 0
            print(f"    ⏳ {fn}  {pct:.0f}%  {sp // 1024}KB/s")


# ── 专辑匹配 ──────────────────────────────────────────────

def match_album_files(responses):
    """
    将搜索结果按专辑归类。
    返回: {album_index: [(username, files), ...]}
    """
    album_map = {}
    for album in ALBUMS:
        # 为每张专辑构建曲目名模式
        track_pattern = "|".join(re.escape(t) for t in album["tracks"])
        if len(album["tracks"]) > 10:
            # 只取部分常见曲目做匹配
            track_pattern = "|".join(re.escape(t) for t in album["tracks"][:5])
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


# ── 主流程 ────────────────────────────────────────────────

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

    # 检查服务器
    ok, state = check_server()
    if not ok:
        print(f"[!] slskd 未就绪 (state={state})")
        print("    请先启动: docker compose up -d")
        sys.exit(1)
    print(f"[✓] slskd 已连接 (state={state})")

    # 筛选专辑
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
            album_list = ', '.join(f"{a['year']} - {a['name']}" for a in ALBUMS)
            print(f"    可选: {album_list}")
            sys.exit(1)

    # 搜索
    all_responses = []
    for keyword in SEARCH_KEYWORDS:
        print(f"\n[1/3] 搜索 '{keyword}'...")
        results = search_tracks(keyword)
        all_responses.extend(results)
        if results:
            break  # 有结果就停

    if not all_responses:
        print("\n[!] 未找到在线用户分享的周杰伦歌曲。")
        print("    Soulseek 是 P2P 网络，需要等待有资源的用户在线。")
        print("    建议过段时间再试。")
        sys.exit(0)

    # 按专辑归类
    print(f"\n[2/3] 归类搜索结果（{sum(len(f) for _, f in all_responses)} 个文件）...")
    album_map = match_album_files(all_responses)
    for aname, info in album_map.items():
        if info["matches"]:
            users = set(m[0] for m in info["matches"])
            print(f"  {info['info']['year']} - {aname}: "
                  f"{len(info['matches'])} 个文件, 来自 {len(users)} 个用户")

    if args.search_only:
        print("\n[✓] 搜索完成（--search-only 模式）")
        return

    # 下载
    print(f"\n[3/3] 排队下载...")
    total_queued = 0
    for aname, info in album_map.items():
        if not info["matches"]:
            continue

        # 按用户分组
        by_user = {}
        for username, f in info["matches"]:
            by_user.setdefault(username, []).append(f)

        for username, files in by_user.items():
            q = download_from_user(username, files)
            total_queued += q

    print(f"\n{'='*50}")
    print(f"完成！共排队 {total_queued} 个文件")
    print(f"下载完成后运行: python3 organizer.py")
    print(f"查看状态: python3 downloader.py --status")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
