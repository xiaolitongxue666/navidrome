# deploy/ — Agent 入口

会话优先读 [PROJECT_MEMORY.md](PROJECT_MEMORY.md) 与 [README.md](README.md)。

## 硬约束：获取音频

下载或迁移音频时**必须**同时保证元数据与封面，否则 Navidrome 会出现乱码、无专辑图。

| 项 | 要求 |
|----|------|
| **格式** | 曲库统一 **MP3**（`libmp3lame`）；新导入建议 **-b:a 320k**，不低于 192k；B站 M4A / FLAC 等须转 MP3 |
| **标签** | ID3v2.4 **UTF-8**：`TIT2` 歌名、`TPE1` 歌手、`TALB` 专辑、`TPE2` 专辑艺人（必填）；**禁止** `TCMP=1`（避免 Various Artists 合集） |
| **封面** | 嵌入 **APIC**（JPEG/PNG）；优先文件自带封面，其次外部图源 |
| **文件名** | `歌手 - 歌名.mp3` 或专辑目录 `nn - 曲名.ext`；非法字符 `/\|?*` 等替换为 `_`，最长 200 字符 |

### 渠道优先级（必须按序）

1. **主路径 — DoubleDouble**（[us.doubledouble.top](https://us.doubledouble.top/)）：Qobuz / iTunes 等整专 zip → 见下方入库流程。
2. **兜底 — Soulseek**：`tools/music-downloader/`（`docker compose` + `downloader.py` + `organizer.py`），用于 DD 无源或单曲补缺。
3. **人工扩展**：RuTracker / Telegram（**非**网易云 bot）仅在主路径失败且本机已登录时由人工使用；Agent **不默认**依赖。
4. **禁止**：网易云音频（`music.163.com`）、`@Music163bot`、`download-batch.py` / `fill_from_netease.py` / yt-dlp 指向网易云歌曲页。

网易云 API **仅允许**用于元数据/封面 enrichment（如 `enrich-manifest.py`、`tag_utils` 拉封面），不得拉取音轨媒体。

### 入库流程（整专 zip / FLAC 包）

1. zip 落到本机 Downloads（或指定路径），**勿提交**。
2. 用 `tools/music-downloader/import_album_zip.py`（或等价手工）：解压到 `_rt_test/` → 按 [`config.py`](../tools/music-downloader/config.py) `ALBUMS` 中文轨名映射 → **跳过已存在** MP3 → `ffmpeg` 320k + ID3/APIC → `deploy/music/周杰伦/{year} - {album}/`。
3. `python organizer.py --scan-only`（需 `ND_USER`/`ND_PASS` 或 `.admin-credentials`）。

**整理已有文件**：`embed-tags-covers.py` 补标签 → `sync-liked-all-to-vps.py`（若需同步 VPS）。

**禁止**：仅转码不写标签；仅依赖 Navidrome external 封面而不嵌 APIC（external 仅作兜底）。

## 工具与环境

- Python 脚本：`C:\Python313\python.exe`（uv 管理的 `python` 勿 pip；需 `mutagen`）
- 控制台：`PYTHONIOENCODING=utf-8`
- VPS 探针/ curl：`curl --noproxy '*'`
- Git：仓库根目录用 `git -C ...`，避免 `cd navidrome` 触发 nvm
- Soulseek：`tools/music-downloader/`（`docker compose up -d` → `downloader.py` → `organizer.py`）
- DoubleDouble 导入：`tools/music-downloader/import_album_zip.py`（见该目录 README）

## 勿提交

`music/`、`data/`、`playlist-enriched.json`（可本地再生）、`*-status.jsonl`、密钥与 `.admin-credentials`；  
`tools/music-downloader/_rt_test/`、`_dd_test/`、临时 FLAC、Downloads 中的专辑 zip。
