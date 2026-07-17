#!/bin/bash
# ============================================================
# music-downloader 清理脚本
# 停止 slskd 容器、删除下载文件、清理配置
# 
# 用法:
#   bash cleanup.sh           # 停止容器 + 询问是否删下载文件
#   bash cleanup.sh --force   # 全部清理，不询问
#   bash cleanup.sh --soft    # 仅停容器，保留下载文件
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FORCE=false
SOFT=false

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=true ;;
        --soft)  SOFT=true ;;
    esac
done

echo "===== music-downloader 清理 ====="

# ── 1. 停止 Docker 容器 ──────────────────────────────────
echo ""
echo "[1/3] 停止 slskd 容器..."

if docker ps --format '{{.Names}}' | grep -q '^slskd-music-downloader$'; then
    echo "  停止容器..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" down 2>/dev/null || \
    docker stop slskd-music-downloader 2>/dev/null || true
    docker rm slskd-music-downloader 2>/dev/null || true
    echo "  ✓ 容器已停止"
else
    echo "  - 容器未在运行"
fi

# 也清理旧名的容器（之前叫 slskd）
if docker ps -a --format '{{.Names}}' | grep -q '^slskd$'; then
    echo "  清理旧容器 'slskd'..."
    docker stop slskd 2>/dev/null || true
    docker rm slskd 2>/dev/null || true
fi

# ── 2. 删除下载文件 ──────────────────────────────────────
echo ""
echo "[2/3] 下载文件..."

if [ "$SOFT" = true ]; then
    echo "  --soft 模式：保留下载文件"
else
    DOWNLOAD_DIR="$SCRIPT_DIR/downloads"
    if [ -d "$DOWNLOAD_DIR" ]; then
        SIZE=$(du -sh "$DOWNLOAD_DIR" 2>/dev/null | cut -f1)
        
        if [ "$FORCE" = true ]; then
            echo "  删除 $DOWNLOAD_DIR ($SIZE)..."
            rm -rf "$DOWNLOAD_DIR"
            echo "  ✓ 已删除"
        else
            echo "  下载目录: $DOWNLOAD_DIR ($SIZE)"
            read -p "  删除下载文件? [y/N] " CONFIRM
            if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
                rm -rf "$DOWNLOAD_DIR"
                echo "  ✓ 已删除"
            else
                echo "  - 保留"
            fi
        fi
    else
        echo "  - 没有下载文件"
    fi
fi

# ── 3. 从 Navidrome 音乐库删除（可选）────────────────────
echo ""
echo "[3/3] 从 Navidrome 音乐库清理..."
if [ "$FORCE" = true ]; then
    # 与 config.py 一致：MUSIC_DIR 环境变量，否则仓库 deploy/music
    if [ -n "${MUSIC_DIR:-}" ]; then
        ARTIST_DIR="$MUSIC_DIR/周杰伦"
    else
        REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
        ARTIST_DIR="$REPO_ROOT/deploy/music/周杰伦"
    fi
    if [ -d "$ARTIST_DIR" ]; then
        SIZE=$(du -sh "$ARTIST_DIR" 2>/dev/null | cut -f1)
        echo "  删除 $ARTIST_DIR ($SIZE)..."
        rm -rf "$ARTIST_DIR"
        echo "  ✓ 已从 Navidrome 音乐库删除"
    else
        echo "  - 没有周杰伦目录 ($ARTIST_DIR)"
    fi
else
    echo "  跳过（使用 --force 同时清理音乐库）"
fi

echo ""
echo "===== 清理完成 ====="
