# 本地音乐工作流

## 已完成部署（2026-07-13）

| 环境 | 地址 | 说明 |
|------|------|------|
| 本地测试 | http://localhost:4533 | `docker compose -f docker-compose.local.yml up -d` |
| VPS 生产 | https://xiaolitongxue.com.cn/music/ | Nginx 子路径反代，仅 127.0.0.1:4533 |
| Subsonic 客户端 | `https://xiaolitongxue.com.cn/music` | 管理员凭据见 VPS `/home/ubuntu/navidrome/.admin-credentials` |

### UI 主题

VPS `docker-compose.yml` 已配置 `ND_DEFAULTTHEME: "Tokyo Night"`。新浏览器首次登录默认使用该主题；若仍显示 Dark，请在 **个人设置 → 主题** 手动选择 **Tokyo Night**（localStorage 会覆盖服务器默认）。

## 网易云「我喜欢的音乐」迁移

| 层级 | 范围 | 清单文件 |
|------|------|----------|
| 本地全量 | 7269 首 | `playlist-157658592.json` |
| 富化元数据 | 7269 首（含专辑/封面 URL） | `playlist-enriched.json` |
| VPS 子集 | 最新 1000 首（`trackIds` 前 1000） | `playlist-latest1000.json` |

### 1. 生成子集清单

```bash
python deploy/scripts/build-latest1000.py
```

### 2. 补全专辑与封面 URL（可选，embed 前执行）

```bash
python deploy/scripts/enrich-manifest.py
```

从网易云 `song/detail` API 补全 `albumName`、`albumPicUrl`，输出 `playlist-enriched.json`。

### 3. 下载（yt-dlp 批量，可续传）

下载目录：`deploy/music/liked/`（文件名 `歌手 - 歌曲名.mp3`）

新下载会自动 `--embed-thumbnail` 并从 manifest 写入 UTF-8 ID3 + 封面（需 `mutagen`）。

```bash
pip install mutagen   # 或 C:\Python313\python.exe -m pip install mutagen

# 单批（50 首）
python deploy/scripts/download-batch.py --manifest deploy/playlist-latest1000.json --batch-size 50 --batch 0

# latest1000 全部 20 批
python deploy/scripts/download-all-batches.py --manifest deploy/playlist-latest1000.json --batch-size 50
```

日志：`deploy/download-status.jsonl`

### 4. 批量修复已有 MP3 标签与封面

对本地 `music/liked/` 全部 MP3 写入 UTF-8 ID3 + APIC（不重下音频）：

```bash
python deploy/scripts/embed-tags-covers.py --manifest deploy/playlist-enriched.json
```

日志：`deploy/embed-status.jsonl`

### 5. LX Music（可选 GUI）

详见 [lx-music-setup.md](lx-music-setup.md)。命令行脚本与 LX 共用同一 `music/liked/` 目录。

### 6. 同步至 VPS

**全部本地 liked MP3**（不仅 latest1000 清单）：

```bash
python deploy/scripts/sync-liked-all-to-vps.py
```

仅 latest1000 清单内文件：

```bash
python deploy/scripts/sync-latest1000-to-vps.py
```

- 同步前检查 VPS 磁盘（剩余 < 3GB 中止）
- 不使用 `scp *.mp3` 通配全量、不使用 `--delete`

### 7. Navidrome 扫库与配置

VPS compose 环境变量（`deploy/docker-compose.yml`）：

- `ND_COVERARTPRIORITY: embedded,external,cover.*,folder.*,front.*`
- `ND_DEFAULTTHEME: Tokyo Night`
- `ND_ENABLEEXTERNALSERVICES: true`

部署/重启：

```bash
ssh ubuntu@xiaolitongxue.com.cn 'cd /home/ubuntu/Code/Go/navidrome/deploy && docker compose up -d --force-recreate navidrome'
# 或仅重启
ssh ubuntu@xiaolitongxue.com.cn 'docker restart navidrome'
```

## 目录结构

```text
deploy/
  playlist-157658592.json      # 全量 7269
  playlist-enriched.json       # 含 albumName/albumPicUrl
  playlist-latest1000.json     # VPS 子集
  download-status.jsonl
  embed-status.jsonl
  music/
    SoundHelix-*.mp3             # 测试曲库（保留）
    liked/                       # 网易云下载
  scripts/
    enrich-manifest.py
    embed-tags-covers.py
    tag_utils.py
    build-latest1000.py
    download-batch.py
    download-all-batches.py
    sync-latest1000-to-vps.py
    sync-liked-all-to-vps.py
    check-downloads.ps1
```
