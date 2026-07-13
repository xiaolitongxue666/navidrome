# deploy/ — Agent 入口

会话优先读 [PROJECT_MEMORY.md](PROJECT_MEMORY.md) 与 [README.md](README.md)。

## 硬约束：获取音频

下载或迁移音频时**必须**同时保证元数据与封面，否则 Navidrome 会出现乱码、无专辑图。

| 项 | 要求 |
|----|------|
| **格式** | 曲库统一 **MP3**（`libmp3lame`，建议 `-b:a 192k`）；B站 M4A 等须 ffmpeg 转 MP3 |
| **标签** | ID3v2.4 **UTF-8**：`TIT2` 歌名、`TPE1` 歌手、`TALB` 专辑（网易云原始专辑名）、`TPE2` 专辑艺人（必填）；**禁止** `TCMP=1`（避免 Various Artists 合集） |
| **封面** | 嵌入 **APIC**（JPEG/PNG）；来源优先 manifest `albumPicUrl`，其次 yt-dlp thumbnail |
| **文件名** | `歌手 - 歌名.mp3`；非法字符 `/\|?*` 等替换为 `_`，最长 200 字符 |
| **清单** | 下载前/后对照 `playlist-enriched.json`（`enrich-manifest.py` 生成） |

**标准流程**：`enrich-manifest.py` → `download-batch.py`（含 `tag_utils.apply_tags_from_manifest`）→ 已有文件用 `embed-tags-covers.py` 补标签 → `sync-liked-all-to-vps.py`。

**禁止**：仅 yt-dlp 转 MP3 不写标签；仅依赖 Navidrome external 封面而不嵌 APIC（external 仅作兜底）。

## 工具与环境

- Python 脚本：`C:\Python313\python.exe`（uv 管理的 `python` 勿 pip；需 `mutagen`）
- 控制台：`PYTHONIOENCODING=utf-8`
- VPS 探针/ curl：`curl --noproxy '*'`
- Git：仓库根目录用 `git -C ...`，避免 `cd navidrome` 触发 nvm

## 勿提交

`music/`、`data/`、`playlist-enriched.json`（可本地再生）、`*-status.jsonl`、密钥与 `.admin-credentials`。
