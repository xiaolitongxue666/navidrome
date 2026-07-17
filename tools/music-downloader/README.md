# music-downloader

周杰伦专辑获取与整理工具：**DoubleDouble 为主渠道**，本目录的 Soulseek（slskd）为**长尾兜底**。

**禁止从网易云下载音频**（含 `@Music163bot`）。网易云 API 仅可用于元数据/封面。

## 渠道策略

| 优先级 | 渠道 | 用途 |
|--------|------|------|
| 1 主 | DoubleDouble（Qobuz / iTunes） | 主流整专 zip，直链快 |
| 2 兜底 | Soulseek（本目录 slskd） | DD 无源或单曲补缺 |
| 3 人工 | RuTracker / Telegram（非网易云 bot） | 需本机已登录；Agent 不默认 |

详见 [`deploy/AGENTS.md`](../../deploy/AGENTS.md)。

## 依赖

- Docker + Docker Compose（Soulseek / slskd）
- Python 3 + `requests`（`pip install -r requirements.txt`）
- `ffmpeg`（DoubleDouble FLAC/M4A → MP3）

## DoubleDouble 导入（主路径）

1. 在 [us.doubledouble.top](https://us.doubledouble.top/) 粘贴 Qobuz 专辑 URL，或用 iTunes 搜索专辑后下载。
2. 浏览器将 zip 存到例如 `C:\Users\Administrator\Downloads\xxxx.zip`。
3. 导入（跳过已有轨，转 MP3 320k + 基础标签）：

```bash
cd tools/music-downloader
PYTHONIOENCODING=utf-8 C:/Python313/python.exe import_album_zip.py \
  --zip "/c/Users/Administrator/Downloads/isyO1Qs.zip" \
  --album 范特西

# 预览
PYTHONIOENCODING=utf-8 C:/Python313/python.exe import_album_zip.py \
  --zip "..." --album 八度空间 --dry-run
```

4. 触发扫描：`python organizer.py --scan-only`。

临时解压目录为 `_rt_test/`（已 gitignore，勿提交）。Downloads 中的 zip / FLAC 原包勿提交。

## Soulseek 使用（兜底）

### 1. 启动 slskd

```bash
docker compose up -d
# 等待约 15 秒让 slskd 连接 Soulseek 网络
```

### 2. 搜索并下载

```bash
# 下载周杰伦全部专辑（2000-2006）
python3 downloader.py

# 只下载指定专辑
python3 downloader.py --album 七里香
python3 downloader.py --album 2004

# 仅搜索预览
python3 downloader.py --search-only

# 查看下载进度
python3 downloader.py --status
```

> Soulseek 是 P2P，需等待在线用户；一次搜不到可多试。  
> 默认只下载 **MP3**（`PREFERRED_FORMATS = [".mp3"]`）。

可将 `liked/` 中已有周杰伦曲目整理进专辑目录（不下载）：

```bash
python sync_from_liked.py
python sync_from_liked.py --dry-run
```

### 3. 整理到 Navidrome

```bash
# 将已完成文件移动到音乐库（默认 deploy/music/周杰伦/）
python3 organizer.py

# 预览模式（不实际移动）
python3 organizer.py --dry-run

# 仅触发 Navidrome 扫描
python3 organizer.py --scan-only
```

> 曲库路径默认 `../../deploy/music`，可用环境变量 `MUSIC_DIR` 覆盖（VPS: `/home/ubuntu/music`）。  
> 本地 `NAVIDROME_BASEURL` 默认为空；VPS 设 `NAVIDROME_BASEURL=/music`。  
> 扫描需设置 `ND_USER` / `ND_PASS`（或 `deploy/data/.admin-credentials`）。  
> 扫描前文件应为 **MP3 + ID3/APIC**（`import_album_zip.py` 或 `embed-tags-covers.py`）。

### 4. 清理

```bash
bash cleanup.sh          # 停止容器，询问是否删下载文件
bash cleanup.sh --force  # 含曲库周杰伦目录
bash cleanup.sh --soft   # 仅停容器
```

## 目录结构

```
tools/music-downloader/
├── docker-compose.yml    # slskd 服务定义
├── slskd.yml             # slskd 配置
├── config.py             # 专辑列表、路径、搜索参数
├── downloader.py         # Soulseek 搜索 → 排队下载
├── organizer.py          # Soulseek 完成文件 → 曲库；可 --scan-only
├── import_album_zip.py   # DoubleDouble zip → 曲库（主路径）
├── sync_from_liked.py    # liked/ → 专辑目录
├── cleanup.sh
├── requirements.txt
├── downloads/            # slskd volume（gitignore）
├── _rt_test/             # zip 解压临时目录（gitignore，勿提交）
└── README.md
```

## 专辑列表（2000-2006）

| 年份 | 专辑 | 曲目数 |
|------|------|--------|
| 2000 | 周杰伦 (Jay) | 10 |
| 2001 | 范特西 (Fantasy) | 10 |
| 2002 | 八度空间 (The Eight Dimensions) | 10 |
| 2003 | 叶惠美 (Ye Hui Mei) | 11 |
| 2004 | 七里香 (Common Jasmine Orange) | 10 |
| 2005 | 十一月的萧邦 (November's Chopin) | 12 |
| 2006 | 依然范特西 (Still Fantasy) | 10 |

## 架构

```
[主] DoubleDouble zip ──→ import_album_zip.py ──→ MUSIC_DIR/周杰伦/
                                                      │
[兜] downloader.py ──→ slskd ──→ downloads/ ──→ organizer.py ──┘
                                                      │
                                              Navidrome startScan
```
