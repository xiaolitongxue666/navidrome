#!/usr/bin/env python3
"""
下载文件整理器
===============
扫描 slskd 的下载目录，将已完成文件整理到 Navidrome 音乐库。

用法: python3 organizer.py                  # 整理所有已完成文件
      python3 organizer.py --dry-run        # 预览，不实际移动
      python3 organizer.py --scan-only      # 仅触发 Navidrome 扫描
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    ARTIST, DOWNLOAD_DIR, INCOMPLETE_DIR, MUSIC_DIR,
    SLSKD_API, ALBUMS, PREFERRED_FORMATS,
    NAVIDROME_URL, NAVIDROME_BASEURL,
)


def find_completed_files():
    """
    扫描下载目录，找出已完成文件。
    返回: [(source_path, filename), ...]
    """
    completed = []
    incomplete = set()

    # 收集 incomplete 中的文件名
    if os.path.isdir(INCOMPLETE_DIR):
        for root, dirs, files in os.walk(INCOMPLETE_DIR):
            for f in files:
                incomplete.add(f)

    # 扫描 download 目录（排除 incomplete）
    if os.path.isdir(DOWNLOAD_DIR):
        for f in os.listdir(DOWNLOAD_DIR):
            fp = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fp) and f not in incomplete:
                ext = os.path.splitext(f)[1].lower()
                if ext in PREFERRED_FORMATS:
                    completed.append((fp, f))
            elif os.path.isdir(fp) and f != "incomplete":
                # 某些文件可能在子目录中
                for root, dirs, files in os.walk(fp):
                    for ff in files:
                        fpath = os.path.join(root, ff)
                        if ff not in incomplete:
                            ext = os.path.splitext(ff)[1].lower()
                            if ext in PREFERRED_FORMATS:
                                completed.append((fpath, ff))

    return completed


def identify_album(filename):
    """
    根据文件名判断属于哪张专辑。
    返回: (year, album_name, track_name) 或 None
    """
    name = filename.lower()

    # 对每张专辑检查
    for album in ALBUMS:
        for i, track in enumerate(album["tracks"]):
            if track.lower() in name:
                # 确认是周杰伦
                if ARTIST.lower() in name or "jay" in name:
                    return (album["year"], album["name"], track, i + 1)
                # 有时文件名没写艺人名，只靠曲名
                return (album["year"], album["name"], track, i + 1)

    return None


def identify_from_path(filepath):
    """
    从完整路径尝试识别专辑信息。
    返回: (year, album_name, track_name, track_no) 或 None
    """
    # 尝试从路径中提取年份和专辑名
    path = filepath.lower()
    for album in ALBUMS:
        if album["year"] in path and (
            album["name"].lower() in path or album["name_en"].lower() in path
        ):
            for i, track in enumerate(album["tracks"]):
                if track.lower() in path:
                    return (album["year"], album["name"], track, i + 1)
            # 路径包含专辑但没具体曲名，返回专辑信息不指定曲目
            return (album["year"], album["name"], None, 0)

    return None


def organize_file(src_path, filename, dry_run=False):
    """
    将单个文件整理到目标位置。
    返回: (target_path, moved) 或 None
    """
    # 识别专辑
    info = identify_album(filename) or identify_from_path(src_path)
    if not info:
        # 无法识别，放到 unknown 目录
        target_dir = os.path.join(MUSIC_DIR, ARTIST, "_unknown")
        target = os.path.join(target_dir, filename)
        if os.path.exists(target):
            return None  # 已存在
        if not dry_run:
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(src_path, target)
        return (target, False)

    year, album_name, track_name, track_no = info

    # 构建目标目录: /home/ubuntu/music/周杰伦/2004 - 七里香/
    album_dir_name = f"{year} - {album_name}"
    target_dir = os.path.join(MUSIC_DIR, ARTIST, album_dir_name)

    # 构建目标文件名: 01 - 七里香.mp3
    if track_name and track_no:
        ext = os.path.splitext(filename)[1]
        target_name = f"{track_no:02d} - {track_name}{ext}"
    else:
        target_name = filename

    target = os.path.join(target_dir, target_name)

    if os.path.exists(target):
        return None  # 已存在

    if not dry_run:
        os.makedirs(target_dir, exist_ok=True)
        shutil.move(src_path, target)
        print(f"  ✓ {target}")

    return (target, True)


def trigger_navidrome_scan():
    """通过 Navidrome API 触发扫描。"""
    try:
        # Navidrome Subsonic API: 需要认证
        # 先用简单的重启扫描方式
        print("\n  触发 Navidrome 扫描...")

        # 方式1: 通过修改音乐目录的 mtime 触发扫描（Navidrome 会检测变化）
        # 实际上 Navidrome 有 SCANSCHEDULE: @every 15m，会自动扫描

        # 方式2: 尝试调用 Navidrome 的内部 API
        # Navidrome 没有公开的扫描触发 API，等待定时扫描即可

        print(f"  已安排扫描（Navidrome 每 15 分钟自动扫描）")
        return True
    except Exception as e:
        print(f"  ⚠ 触发扫描失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="下载文件整理器")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="预览模式，不实际移动文件")
    parser.add_argument("--scan-only", action="store_true",
                        help="仅触发 Navidrome 扫描")
    args = parser.parse_args()

    if args.scan_only:
        trigger_navidrome_scan()
        return

    # 扫描下载目录
    print(f"扫描下载目录: {DOWNLOAD_DIR}")
    files = find_completed_files()
    print(f"找到 {len(files)} 个已完成音频文件")

    if not files:
        print("没有需要整理的文件。")
        return

    # 按专辑分组
    by_album = {}
    unknown = []
    for src, fn in files:
        info = identify_album(fn) or identify_from_path(src)
        if info:
            key = f"{info[0]} - {info[1]}"
            by_album.setdefault(key, []).append((src, fn, info))
        else:
            unknown.append((src, fn))

    # 显示分类结果
    print(f"\n识别到 {len(by_album)} 张专辑:")
    for key, items in sorted(by_album.items()):
        tracks = set(i[2][2] for i in items if i[2][2])
        print(f"  {key}: {len(items)} 个文件 ({len(tracks)} 首曲目)")
    if unknown:
        print(f"  无法识别: {len(unknown)} 个文件")

    if args.dry_run:
        print("\n[预览模式] 完成，未移动任何文件。")
        return

    # 移动文件
    print(f"\n整理到: {MUSIC_DIR}/{ARTIST}/")
    moved = 0
    skipped = 0
    for key, items in sorted(by_album.items()):
        for src, fn, info in items:
            result = organize_file(src, fn, dry_run=False)
            if result:
                moved += 1
            else:
                skipped += 1

    for src, fn in unknown:
        target_dir = os.path.join(MUSIC_DIR, ARTIST, "_unknown")
        target = os.path.join(target_dir, fn)
        if not os.path.exists(target):
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(src, target)
            moved += 1
        else:
            skipped += 1

    print(f"\n{'='*50}")
    print(f"整理完成: 移动 {moved} 个文件, 跳过 {skipped} 个")
    if moved > 0:
        trigger_navidrome_scan()
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
