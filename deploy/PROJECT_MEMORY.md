# Navidrome deploy — 项目记忆

> 仅 `deploy/`；勿写入密钥、Cookie、`.admin-credentials`。

## 架构与策略

1. VPS：`docker-compose.yml`，Navidrome `127.0.0.1:4533`，`ND_BASEURL=/music`，曲库 `/home/ubuntu/music`（含 `liked/`）。
2. Nginx：vps_nginx `music.conf.tpl` 反代 `/music/` → `:4533`。
3. 本地全量 **7269** 首；VPS 子集 **latest1000**（`trackIds` 前 1000，新收藏在前）。
4. VPS compose：`/home/ubuntu/Code/Go/navidrome/deploy/docker-compose.yml`。

## 音频获取（必守）

5. **格式**：统一 MP3（yt-dlp `-x --audio-format mp3` 或 ffmpeg `libmp3lame -b:a 192k`）。
6. **元数据**：ID3v2.4 UTF-8 `TIT2`/`TPE1`/`TALB`；权威来源 manifest/`playlist-enriched.json`。
7. **封面**：嵌入 APIC；`albumPicUrl` → `tag_utils.download_cover_bytes`；下载脚本 `--embed-thumbnail` + `apply_tags_from_manifest`。
8. **文件名**：`歌手 - 歌名.mp3`，`sanitize_filename`（`/`→`_`，≤200 字符）。
9. 流程：`enrich-manifest.py` → 下载/embed → `sync-liked-all-to-vps.py`；禁止裸 MP3 无标签进库。

## UI / Navidrome 配置

10. `ND_DEFAULTTHEME: "Tokyo Night"`（0.63.2 内置）；localStorage 可覆盖 → 个人设置手动选。
11. `ND_COVERARTPRIORITY: embedded,external,cover.*,folder.*,front.*`；`ND_ENABLEEXTERNALSERVICES: true`。

## 清单与脚本

| 文件 | 说明 |
|------|------|
| `playlist-157658592.json` | 全量 7269 元数据 |
| `playlist-enriched.json` | +albumName/albumPicUrl（本地生成，勿提交） |
| `playlist-latest1000.json` | VPS 子集 |
| `enrich-manifest.py` | 无登录 `song/detail` 富化 |
| `embed-tags-covers.py` | 批量 ID3+APIC |
| `tag_utils.py` | 共享标签/封面逻辑 |
| `sync-liked-all-to-vps.py` | 全部 liked MP3 → VPS（逐文件 scp，~40min/762 首） |

## 导出要点

- 登录态 `playlist/detail` 得完整 `trackIds`（网页仅 1000）。
- `music-get` CLI 已失效（-447）。

## 状态 (2026-07-13)

- 本地 liked：**762** MP3（含 ~50 首 B站 extra，embed 时 `unmatched`）。
- embed：**712 ok** + 50 unmatched；VPS **762** 已重同步；Navidrome 已 restart。
- latest1000 下载：636 ok/skip，82 fail，282 preview_only。

## 问题与解法

| 问题 | 解法 |
|------|------|
| 乱码/无封面 | embed + `ND_COVERARTPRIORITY`；勿只 yt-dlp 不写字标签 |
| `mutagen` 找不到 | `C:\Python313\python.exe -m pip install mutagen` |
| uv `python` 禁 pip | 脚本统一用 Python313 |
| VPS curl 502 | `curl --noproxy '*'`（本机代理劫持 127.0.0.1） |
| defaultTheme 探针失败 | 加 `-L` 跟随 301；VPS 上 `--noproxy` |
| scp 无进度像卡死 | 762 首串行 ~40min；脚本已每 10 首 print |
| Windows 控制台乱码 | `safe_print`；`PYTHONIOENCODING=utf-8` |
| navidrome 目录 cd/nvm | `git -C ...` |
| scp Unicode 文件名 | Python subprocess 逐个 scp |

## 约束

- 歌单 JSON 可进私有仓；勿公开传播 MP3。
- 全量 ~30GB 仅本地；VPS 子集 ~4–5GB。
- 同步勿 `--delete`（保留 SoundHelix）。

_更新：2026-07-13_
