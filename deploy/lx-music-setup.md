# LX Music 配置（一次性）

与 [网易云歌单迁移计划](https://xiaolitongxue.com.cn) 对齐：本机全量、VPS 最新 1000 首。

## 目录

| 用途 | 路径 |
|------|------|
| 本地下载目录 | `E:\Code\my_code\Go\navidrome\deploy\music\liked` |
| latest1000 清单 | `deploy/playlist-latest1000.json` |
| 全量清单 | `deploy/playlist-157658592.json` |

## LX Music GUI 设置

1. 启动 **LX Music** v2.12.2
2. **设置 → 基本设置 → 音乐来源**：加载当前可用社区自定义源
3. **设置 → 下载设置**：
   - 下载目录：`E:\Code\my_code\Go\navidrome\deploy\music\liked`
   - 音质：**标准**（128kbps）
   - 格式：**MP3**
   - 文件名：`歌手 - 歌曲名`
4. **歌单 → 导入链接**：
   ```
   https://music.163.com/playlist?id=157658592
   ```
   （网页端 liked 与 VPS 子集 latest1000 前 1000 首重合，可优先批量下载此导入结果）

## 命令行批量下载（推荐，可续传）

已安装 `yt-dlp`，使用仓库脚本按清单下载并重命名为 `歌手 - 歌曲名.mp3`：

```bash
# latest1000，每批 50 首
python deploy/scripts/download-batch.py --manifest deploy/playlist-latest1000.json --batch-size 50 --batch 0

# 全量 7269（在 latest1000 完成后）
python deploy/scripts/download-batch.py --manifest deploy/playlist-157658592.json --batch-size 50 --batch 0
```

日志：`deploy/download-status.jsonl`
