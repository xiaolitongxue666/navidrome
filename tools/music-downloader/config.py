"""
music-downloader 配置
======================
本目录脚本默认服务 **Soulseek（slskd）** 通道（长尾兜底）。
主流整专优先走 DoubleDouble + import_album_zip.py，见 README。

所有可调参数集中在此，方便修改。
环境变量可覆盖路径与 API（便于本地 / VPS 切换）。
"""
import os
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOL_DIR.parents[1]
_DEFAULT_MUSIC_DIR = str(_REPO_ROOT / "deploy" / "music")

# ── slskd API ──────────────────────────────────────────────
SLSKD_API = os.environ.get("SLSKD_API", "http://127.0.0.1:5030/api/v0")

# ── 下载目录 ──────────────────────────────────────────────
# slskd 容器内的下载路径（由 docker-compose 映射）
DOWNLOAD_DIR = os.environ.get(
    "DOWNLOAD_DIR", str(_TOOL_DIR / "downloads")
)
INCOMPLETE_DIR = os.path.join(DOWNLOAD_DIR, "incomplete")

# ── Navidrome 音乐库路径 ──────────────────────────────────
# 默认: 仓库 deploy/music（本地）；VPS 设 MUSIC_DIR=/home/ubuntu/music
MUSIC_DIR = os.environ.get("MUSIC_DIR", _DEFAULT_MUSIC_DIR)

# ── Navidrome API（用于触发扫描）─────────────────────────
NAVIDROME_URL = os.environ.get("NAVIDROME_URL", "http://127.0.0.1:4533")
# 本地 compose 默认空；VPS 设 NAVIDROME_BASEURL=/music
NAVIDROME_BASEURL = os.environ.get("NAVIDROME_BASEURL", "")
# Subsonic startScan 凭证（可选）
NAVIDROME_USER = os.environ.get("ND_USER", os.environ.get("NAVIDROME_USER", ""))
NAVIDROME_PASS = os.environ.get("ND_PASS", os.environ.get("NAVIDROME_PASS", ""))

# ── 艺人名称 ──────────────────────────────────────────────
ARTIST = "周杰伦"
ARTIST_EN = "Jay Chou"
# 搜索时用的关键词（多种写法增加命中率）
SEARCH_KEYWORDS = [ARTIST, ARTIST_EN, "周杰倫"]

# ── 专辑列表（2000 ~ 2006）───────────────────────────────
# netease_album_id: 网易云官方专辑 ID（Soulseek 不可用时回退下载）
ALBUMS = [
    {
        "year": "2000",
        "name": "周杰伦",
        "name_en": "Jay",
        "netease_album_id": 18918,
        "netease_album_name": "Jay",
        "tracks": [
            "可爱女人", "完美主义", "星晴", "娘子", "斗牛",
            "黑色幽默", "伊斯坦堡", "印地安老斑鸠", "龙卷风", "反方向的钟",
        ],
    },
    {
        "year": "2001",
        "name": "范特西",
        "name_en": "Fantasy",
        "netease_album_id": 18915,
        "netease_album_name": "范特西",
        "tracks": [
            "爱在西元前", "爸我回来了", "简单爱", "忍者", "开不了口",
            "上海一九四三", "对不起", "威廉古堡", "双截棍", "安静",
        ],
    },
    {
        "year": "2002",
        "name": "八度空间",
        "name_en": "The Eight Dimensions",
        "netease_album_id": 18907,
        "netease_album_name": "八度空间",
        "tracks": [
            "半兽人", "半岛铁盒", "暗号", "龙拳", "火车叨位去",
            "分裂", "爷爷泡的茶", "回到过去", "米兰的小铁匠", "最后的战役",
        ],
    },
    {
        "year": "2003",
        "name": "叶惠美",
        "name_en": "Ye Hui Mei",
        "netease_album_id": 18905,
        "netease_album_name": "叶惠美",
        "tracks": [
            "以父之名", "懦夫", "晴天", "三年二班", "东风破",
            "你听得到", "同一种调调", "她的睫毛", "爱情悬崖", "梯田", "双刀",
        ],
    },
    {
        "year": "2004",
        "name": "七里香",
        "name_en": "Common Jasmine Orange",
        "netease_album_id": 18903,
        "netease_album_name": "七里香",
        "tracks": [
            "我的地盘", "七里香", "借口", "外婆", "将军",
            "搁浅", "乱舞春秋", "困兽之斗", "园游会", "止战之殇",
        ],
    },
    {
        "year": "2005",
        "name": "十一月的萧邦",
        "name_en": "November's Chopin",
        "netease_album_id": 18896,
        "netease_album_name": "11月的萧邦",
        "tracks": [
            "夜曲", "蓝色风暴", "发如雪", "黑色毛衣", "四面楚歌",
            "枫", "浪漫手机", "逆鳞", "麦芽糖", "珊瑚海", "漂移", "一路向北",
        ],
    },
    {
        "year": "2006",
        "name": "依然范特西",
        "name_en": "Still Fantasy",
        "netease_album_id": 18893,
        "netease_album_name": "依然范特西",
        "tracks": [
            "夜的第七章", "听妈妈的话", "千里之外", "本草纲目", "退后",
            "红模仿", "心雨", "白色风车", "迷迭香", "菊花台",
        ],
    },
]

# ── 下载选项 ──────────────────────────────────────────────
# 搜索等待时间（秒），越大越可能等到更多在线用户响应
SEARCH_TIMEOUT = int(os.environ.get("SEARCH_TIMEOUT", "90"))

# 无结果时的重试次数（含首次）
SEARCH_RETRIES = int(os.environ.get("SEARCH_RETRIES", "4"))

# 重试间隔（秒）
SEARCH_RETRY_DELAY = int(os.environ.get("SEARCH_RETRY_DELAY", "20"))

# 每个用户最多同时下载文件数
MAX_FILES_PER_USER = 25

# ── 文件格式偏好（按优先级排序）────────────────────────
# 只要普通音质 MP3，不下 FLAC / 无损
PREFERRED_FORMATS = [".mp3"]

# 曲名别名（简繁 / 标点差异），用于搜索结果匹配
TRACK_ALIASES = {
    "印地安老斑鸠": ["印第安老斑鸠"],
    "爸我回来了": ["爸，我回来了", "爸,我回来了"],
    "借口": ["藉口"],
    "将军": ["將軍"],
    "搁浅": ["擱淺"],
    "乱舞春秋": ["亂舞春秋"],
    "困兽之斗": ["困獸之鬥"],
    "园游会": ["園遊會"],
    "止战之殇": ["止戰之殤"],
    "我的地盘": ["我的地盤"],
    "漂移": ["飘移"],
    "分裂": ["分裂(离开)"],
}
