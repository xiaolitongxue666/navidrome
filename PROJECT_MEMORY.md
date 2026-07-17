# Project Memory (Compact)

1) Deploy agent entry: `deploy/AGENTS.md` + `deploy/PROJECT_MEMORY.md` (detailed); root this file is Compact SSOT for `/summary-memory`.
2) **禁止网易云下载音频**（含 `@Music163bot` / `download-batch.py` 拉 music.163.com）；网易云 API 仅元数据/封面 enrichment。
3) **音频渠道优先级**：DoubleDouble（Qobuz/iTunes 整专 zip）主 → Soulseek `tools/music-downloader` 兜底 → RuTracker/Telegram（非网易云）仅人工已登录 → Lucida.to 不可用（403）。
4) 曲库统一 **MP3**（新导入建议 320k，≥192k）+ ID3v2.4 UTF-8（TIT2/TPE1/TALB/TPE2）+ APIC；禁止 TCMP=1；路径 `deploy/music/周杰伦/{year} - {album}/{nn} - {track}.mp3`。
5) DoubleDouble 入库：`import_album_zip.py --zip ... --album ...`（跳过已有轨）→ `organizer.py --scan-only`；临时目录 `_rt_test/`/`_dd_test`/FLAC gitignore，勿提交 Downloads zip。
6) Soulseek：`docker compose up -d` → `downloader.py`（默认仅 .mp3）→ `organizer.py`；P2P 慢/超时属常态，勿当主流专辑首选。
7) 周杰伦 2000–2006 进度：七里香/范特西 10/10；其余缺（周杰伦 4、八度空间 1、叶惠美 4、十一月的萧邦 6、依然范特西 4）。
8) RuTracker 强制登录、Telegram Web 需扫码：本机无会话则 Agent 不默认依赖。
9) 本地 Python：`C:\Python313\python.exe` + `PYTHONIOENCODING=utf-8`；VPS curl 用 `--noproxy '*'`；git 用 `git -C` 避免 nvm。
10) VPS：Navidrome `127.0.0.1:4533`，`ND_BASEURL=/music`；曲库曾同步 liked ~762 MP3；主题 Tokyo Night。
11) 勿提交：`deploy/music/`、`deploy/data/`、密钥、`.admin-credentials`、`playlist-enriched.json`、music-downloader downloads/临时解压。
12) slskd.yml 含 Soulseek 账号口令（历史已入库）；改口令时同步本地 compose，勿贴到公开文档。
