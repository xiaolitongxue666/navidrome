# Navidrome deploy — 项目记忆

> 仅 `deploy/`；勿写入密钥、Cookie、`.admin-credentials`。

## 架构与策略

1. VPS：Navidrome `127.0.0.1:4533`，`ND_BASEURL=/music`，曲库 `/home/ubuntu/music/liked/`；compose 在 `/home/ubuntu/Code/Go/navidrome/deploy/`。
2. Nginx：`music.conf.tpl` 反代 `/music/` → `:4533`。
3. 本地全量 **7269** 首；VPS 当前 **762** MP3（含 ~50 首 B 站 extra，不在网易云歌单）。
4. Navidrome **按 ID3 元数据分组专辑**（`TALB`+`TPE2`+`AlbumID`），不按文件夹；禁止 `TCMP=1` 合集标记。

## 音频获取（必守）

5. **格式**：统一 MP3（`libmp3lame`，建议 `-b:a 192k`）。
6. **标签**：ID3v2.4 UTF-8：`TIT2`/`TPE1`/`TALB`（网易云原始专辑名）/`TPE2`（专辑艺人，必填）；**禁止** `TCMP=1`。
7. **封面**：嵌入 APIC；来源 `albumPicUrl`；`ND_COVERARTPRIORITY: embedded,external,...`。
8. **文件名**：`歌手 - 歌名.mp3`，`sanitize_filename`（`/`→`_`，≤200 字符）。
9. **流程**：`enrich-manifest.py`（含 `albumArtist`）→ `embed-tags-covers.py` → B 站 extra 用 `fix-unmatched.py` + `data/jay-chou-canonical.json` → `sync-liked-all-to-vps.py`。

## UI / Navidrome

10. `ND_DEFAULTTHEME: Tokyo Night`；localStorage 可覆盖。
11. `ND_ENABLEEXTERNALSERVICES: true`；external 封面仅兜底。

## 清单与脚本

| 文件 | 说明 |
|------|------|
| `playlist-157658592.json` | 全量 7269 元数据 |
| `playlist-enriched.json` | +albumName/albumPicUrl/albumArtist（本地生成，勿提交） |
| `playlist-latest1000.json` | VPS 子集清单 |
| `enrich-manifest.py` | 网易云 `song/detail` 富化；`--only-ids` + `--force` |
| `embed-tags-covers.py` | 批量 ID3+APIC |
| `audit-tags.py` | 诊断 TALB/TPE2/TCMP/APIC（输出 `audit-tags-report.json`） |
| `fix-unmatched.py` | B 站 extra：canonical 映射 + 网易云搜索 |
| `build-jay-chou-map.py` | 生成 `data/jay-chou-canonical.json` |
| `tag_utils.py` | 共享标签/封面；禁用 proxy 环境变量 |
| `sync-liked-all-to-vps.py` | 全部 liked MP3 → VPS（scp + SSH 密钥） |

## 状态 (2026-07-13)

12. 本地/VPS：**762** MP3；元数据已全量重写（`TPE2`/清 `TCMP`/原始专辑名）并重同步。
13. 周杰伦 B 站 extra **46/48** 已按原始专辑归组；《等你下课》等 4 首仍无可靠网易云匹配。
14. `enrich-manifest --only-ids playlist-latest1000.json --force` 已跑通 999/1000。

## 问题与解法

| 问题 | 解法 |
|------|------|
| 无专辑名/假合集 | 写 `TALB`+`TPE2`，清 `TCMP`；勿用歌手名回退作专辑名 |
| 乱码/无封面 | embed APIC；勿只 yt-dlp 不写标签 |
| 网易云 API 失败 | `tag_utils` 清除 proxy 环境变量；`NO_PROXY=*` |
| scp 无进度/像卡死 | 762 首串行 ~40min；每 10 首打印；非卡住 |
| SSH `Host key verification failed` | sync 脚本加 `-o StrictHostKeyChecking=accept-new` |
| SSH `Permission denied (publickey)` | scp/ssh 加 `-i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes` |
| B 站周杰伦搜错专辑 | 用 `jay-chou-canonical.json` 官方专辑 ID，勿盲信 cloudsearch |
| `mutagen` 找不到 | `C:\Python313\python.exe -m pip install mutagen` |
| VPS curl 502 | `curl --noproxy '*'` |
| navidrome 目录 cd 触发 nvm | `git -C ...` |

## 约束

- 歌单 JSON 可进私有仓；勿公开传播 MP3。
- 同步勿 `--delete`（保留 SoundHelix）。
- 勿提交：`music/`、`data/`、`*-status.jsonl`、`playlist-enriched.json`、报告/日志。

_更新：2026-07-13_
