# music-downloader

从 **Soulseek P2P 网络**搜索下载音乐，自动整理到 **Navidrome** 音乐库。

## 依赖

- Docker + Docker Compose（运行 slskd）
- Python 3 + `requests`（`pip install -r requirements.txt`）

## 使用

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

> **注意**: Soulseek 是 P2P 网络，需要等待有资源的用户在线。一次搜不到就多试几次。

### 3. 整理到 Navidrome

```bash
# 将已完成文件移动到 /home/ubuntu/music/周杰伦/
python3 organizer.py

# 预览模式（不实际移动）
python3 organizer.py --dry-run

# 仅触发 Navidrome 扫描
python3 organizer.py --scan-only
```

### 4. 清理

```bash
# 停止容器，询问是否删下载文件
bash cleanup.sh

# 全部清理（含 Navidrome 音乐库中的周杰伦目录）
bash cleanup.sh --force

# 仅停容器
bash cleanup.sh --soft
```

## 目录结构

```
tools/music-downloader/
├── docker-compose.yml    # slskd 服务定义（资源限制 512MB / 0.5 CPU）
├── slskd.yml             # slskd 配置
├── config.py             # 专辑列表、路径、搜索参数
├── downloader.py         # 搜索 → 实时捕获 → 排队下载
├── organizer.py          # 完成文件 → 整理到音乐库
├── cleanup.sh            # 一键清理
├── requirements.txt      # Python 依赖
├── downloads/            # 下载文件目录（docker volume）
│   └── incomplete/       # 未完成文件
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
downloader.py  ──→  slskd API  ──→  Soulseek P2P 网络
                      │
                      ▼
                 downloads/  (容器内 /app/downloads)
                      │
organizer.py  ──→  扫描完成文件  ──→  /home/ubuntu/music/周杰伦/
                      │
                      ▼
                Navidrome 自动扫描（每 15 分钟）
```
