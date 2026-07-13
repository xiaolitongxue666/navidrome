# 本地音乐工作流

## 已完成部署（2026-07-13）

| 环境 | 地址 | 说明 |
|------|------|------|
| 本地测试 | http://localhost:4533 | `docker compose -f docker-compose.local.yml up -d` |
| VPS 生产 | https://xiaolitongxue.com.cn/music/ | Nginx 子路径反代，仅 127.0.0.1:4533 |
| Subsonic 客户端 | `https://xiaolitongxue.com.cn/music` | 管理员凭据见 VPS `/home/ubuntu/navidrome/.admin-credentials` |

## 网易云「我喜欢的音乐」迁移

| 层级 | 范围 | 清单文件 |
|------|------|----------|
| 本地全量 | 7269 首 | `playlist-157658592.json` |
| VPS 子集 | 最新 1000 首（`trackIds` 前 1000） | `playlist-latest1000.json` |

### 1. 生成子集清单

```bash
python deploy/scripts/build-latest1000.py
```

### 2. 下载（yt-dlp 批量，可续传）

下载目录：`deploy/music/liked/`（文件名 `歌手 - 歌曲名.mp3`）

```bash
# 单批（50 首）
python deploy/scripts/download-batch.py --manifest deploy/playlist-latest1000.json --batch-size 50 --batch 0

# latest1000 全部 20 批
python deploy/scripts/download-all-batches.py --manifest deploy/playlist-latest1000.json --batch-size 50

# 全量 7269（跳过已存在文件）
python deploy/scripts/download-all-batches.py --manifest deploy/playlist-157658592.json --batch-size 50
```

日志：`deploy/download-status.jsonl`

检查进度：

```powershell
.\deploy\scripts\check-downloads.ps1 -Manifest playlist-latest1000.json
```

### 3. LX Music（可选 GUI）

详见 [lx-music-setup.md](lx-music-setup.md)。命令行脚本与 LX 共用同一 `music/liked/` 目录。

### 4. 同步至 VPS（仅 latest1000）

```bash
bash deploy/scripts/sync-latest1000-to-vps.sh
```

- 仅上传 `playlist-latest1000.json` 中已有本地 MP3
- 同步前检查 VPS 磁盘（剩余 < 3GB 中止）
- 不使用 `scp *.mp3` 全量、不使用 `--delete`

### 5. Navidrome 扫库

VPS 默认 `@every 15m` 自动扫库，或：

```bash
ssh ubuntu@xiaolitongxue.com.cn 'docker restart navidrome'
```

## 目录结构

```text
deploy/
  playlist-157658592.json      # 全量 7269
  playlist-latest1000.json     # VPS 子集
  download-status.jsonl          # 下载日志
  music/
    SoundHelix-*.mp3             # 测试曲库（保留）
    liked/                       # 网易云下载
  scripts/
    build-latest1000.py
    download-batch.py
    download-all-batches.py
    sync-latest1000-to-vps.sh
    check-downloads.ps1
```
