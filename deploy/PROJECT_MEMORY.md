# Navidrome deploy — 项目记忆

> 仅 `deploy/` 工作区；勿写入密钥、Cookie、`.admin-credentials` 内容。

## 架构

1. **VPS**：`docker-compose.yml`，Navidrome `127.0.0.1:4533`，`ND_BASEURL=/music`，曲库 `/home/ubuntu/music`（含 `liked/` 子目录）。
2. **Nginx**：vps_nginx 仓 `music.conf.tpl` 反代 `/music/` → `:4533`（见 vps_nginx 仓）。
3. **策略**：本地全量 liked **7269** 首；VPS 仅 **latest1000**（`trackIds` 前 1000，新收藏在前）。

## 清单文件

| 文件 | 说明 |
|------|------|
| `playlist-157658592-ids.json` | 7269 ID，顺序=收藏新旧 |
| `playlist-157658592.json` | 全量元数据 |
| `playlist-latest1000.json` | VPS 子集（`build-latest1000.py`） |

## 导出（已完成）

- 登录态 `GET /api/v3/playlist/detail?id=157658592&n=0&s=0` → 完整 `trackIds`（网页 DOM 仅 1000）。
- 分批 `GET /api/song/detail/?ids=[...]`（每批 200）→ `merge-cdp-songs.py`。
- `music-get` CLI API 已失效（-447）；勿依赖。

## 下载

- **工具**：本机 `yt-dlp` + `scripts/download-batch.py`（LX Music 可选，同目录 `music/liked/`）。
- **续传**：已存在且 >500KB 的 MP3 自动 skip。
- **失败**：`preview_only`（<500KB 试听）、VIP/无源 → `download-status.jsonl`；可 LX 换源补下。

## 同步 VPS

- `scripts/sync-latest1000-to-vps.py`：仅清单内已有 MP3；同步前 `df -h`（<3GB 中止）。
- **勿** `scp *.mp3` 全量、**勿** `--delete`（保留 SoundHelix 测试曲）。

## 问题与解法

| 问题 | 解法 |
|------|------|
| Windows 控制台 `UnicodeEncodeError` | `download-batch.py` 用 `safe_print`；`PYTHONIOENCODING=utf-8` |
| `INVALID_CHARS` NameError | 已修复；续跑前确认脚本含 `INVALID_CHARS = re.compile(...)` |
| bash sync 路径乱码 | 改用 `sync-latest1000-to-vps.py` |
| navidrome 目录 `cd` 触发 nvm v24 错误 | 用 `git -C ...` 绕过 |

## 约束

- 歌单 JSON 含个人曲目与网易云昵称，可进私有仓，勿公开传播 MP3。
- 全量 ~30GB 仅本地；VPS 子集约 4–5GB。

_更新：2026-07-13_
