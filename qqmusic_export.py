#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQ音乐歌单导出(独立脚本,仅依赖 Python 标准库)。

对应 GoMusic/logic/qqmusic.go + misc/utils/qqmusic_sign.go + misc/models/qqmusic.go。
修复了 Go 版分页失败丢歌的 bug:每页失败重试 3 次,仍失败则记录并报告缺失数量,
不再静默 continue 跳过(原 Go 版 961→926 少 35 首的根因)。

用法:
    python qqmusic_export.py <歌单链接> [--detailed] [--format song-singer|singer-song|song]

示例:
    python qqmusic_export.py "https://i.y.qq.com/n2/m/share/details/taoge.html?id=123456"
    python qqmusic_export.py "https://c.y.qq.com/playlist/123456" --detailed --format song
"""

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse, parse_qs

API_URL = "https://u6.y.qq.com/cgi-bin/musics.fcg?sign=%s&_=%d"
PLATFORMS = ["-1", "android", "iphone",
             "h5", "wxfshare", "iphone_wx", "windows"]
ERROR_RESP_LENGTH = 108        # 响应恰为 108 字节视为错误,需换平台
MAX_SONGS_PER_PAGE = 30
MAX_TOTAL_SONGS = 10000
PAGE_RETRY = 3                 # ponytail: 单页失败重试次数,网络抖动时再调高
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


# ---------- 签名:复刻 misc/utils/qqmusic_sign.go 的 Encrypt ----------
_K1 = {c: i for i, c in enumerate("0123456789ABCDEF")}
_L1 = [212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]
_T = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="


def _select_chars(s, indices):
    return "".join(s[i] for i in indices)


def encrypt(param: str) -> str:
    md5_str = hashlib.md5(param.encode("utf-8")).hexdigest().upper()
    t1 = _select_chars(md5_str, [21, 4, 9, 26, 16, 20, 27, 30])
    t3 = _select_chars(md5_str, [18, 11, 3, 2, 1, 7, 6, 25])

    ls2 = []
    for i in range(16):
        x1 = _K1[md5_str[i * 2]]
        x2 = _K1[md5_str[i * 2 + 1]]
        x3 = ((x1 * 16) ^ x2) ^ _L1[i]
        ls2.append(x3)

    ls3 = []
    for i in range(6):
        if i == 5:
            ls3.append(_T[ls2[-1] >> 2])
            ls3.append(_T[(ls2[-1] & 3) << 4])
        else:
            x4 = ls2[i * 3] >> 2
            x5 = (ls2[i * 3 + 1] >> 4) ^ ((ls2[i * 3] & 3) << 4)
            x6 = (ls2[i * 3 + 2] >> 6) ^ ((ls2[i * 3 + 1] & 15) << 2)
            x7 = 63 & ls2[i * 3 + 2]
            ls3.append(_T[x4] + _T[x5] + _T[x6] + _T[x7])

    # ponytail: 字面替换 [\/],base64 输出不会含 [ ] \,此为忠实复刻 Go 的死代码,等价无操作
    t2 = "".join(ls3).replace("[\\/]", "")
    return "zzb" + (t1 + t2 + t3).lower()


# ---------- 请求参数:复刻 misc/models/qqmusic.go 的 QQMusicReq ----------
def build_param(tid: int, platform: str, song_begin: int, song_num: int) -> str:
    # 字段顺序与 Go 结构体一致,签名对字节敏感,勿改顺序
    return json.dumps({
        "req_0": {
            "module": "music.srfDissInfo.aiDissInfo",
            "method": "uniform_get_Dissinfo",
            "param": {
                "disstid": tid,
                "enc_host_uin": "",
                "tag": 1,
                "userinfo": 1,
                "song_begin": song_begin,
                "song_num": song_num,
            },
        },
        "comm": {"g_tk": 5381, "uin": 0, "format": "json", "platform": platform},
    }, separators=(",", ":"), ensure_ascii=False)


def _request_page(tid: int, platform: str, song_begin: int, song_num: int):
    """单次请求一页。返回 (data_bytes, code)。code 非 0 表示被 QQ 拒绝(如限流 code=2000)。"""
    param = build_param(tid, platform, song_begin, song_num)
    sign = encrypt(param)
    url = API_URL % (sign, int(time.time() * 1000))
    req = urllib.request.Request(
        url, data=param.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    try:
        code = json.loads(data).get("code", 0)
    except Exception:
        code = 0  # 非 JSON 视为正常(历史经验:正常响应是 JSON,这里兜底)
    return data, code


def fetch_page(tid: int, song_begin: int, song_num: int) -> bytes:
    """获取一页歌单数据。依次尝试各 platform,全部失败抛 RuntimeError。"""
    last_err = None
    for platform in PLATFORMS:
        try:
            data, code = _request_page(tid, platform, song_begin, song_num)
        except Exception as e:
            last_err = e
            continue
        if code == 0:
            return data
        last_err = f"code={code}"
    raise RuntimeError(f"所有 platform 均失败: {last_err}")


def fetch_page_resilient(tid: int, song_begin: int, song_num: int) -> list:
    """获取一页歌曲列表。整页失败(code!=0)时拆半重试,再失败抛 RuntimeError。

    QQ 接口对个别 (begin, num) 组合会确定性返回 code=2000(非网络错误,换 platform
    和等待均无效)。实测拆成更小的 num 即可绕过,故整页失败时二分拆分合并结果。
    """
    try:
        data = fetch_page(tid, song_begin, song_num)
        return json.loads(data)["req_0"]["data"]["songlist"]
    except RuntimeError:
        if song_num <= 1:
            raise
        half = song_num // 2
        print(f"  整页(begin={song_begin},num={song_num})被拒,拆分为 {half}+{song_num - half} 重试",
              file=sys.stderr)
        # ponytail: 确定性失败,无需退避;两半各自递归,仍失败再抛
        left = fetch_page_resilient(tid, song_begin, half)
        right = fetch_page_resilient(tid, song_begin + half, song_num - half)
        return left + right


def fetch_playlist(tid: int):
    """返回 (title, total, songlist, missing)。missing 为获取失败的 (begin, num) 列表。"""
    basic = json.loads(fetch_page(tid, 0, MAX_SONGS_PER_PAGE))
    data = basic["req_0"]["data"]
    title = data["dirinfo"].get("title", "") or "playlist"
    total = data["dirinfo"]["songnum"]
    songlist = list(data["songlist"])

    if total <= MAX_SONGS_PER_PAGE:
        return title, total, songlist, []

    if total > MAX_TOTAL_SONGS:
        print(f"警告: 歌单 {total} 首超过上限,只取前 {MAX_TOTAL_SONGS} 首", file=sys.stderr)
        total = MAX_TOTAL_SONGS

    page_count = (total + MAX_SONGS_PER_PAGE - 1) // MAX_SONGS_PER_PAGE
    missing = []
    for page in range(1, page_count):
        song_begin = page * MAX_SONGS_PER_PAGE
        song_num = min(MAX_SONGS_PER_PAGE, total - song_begin)
        page_songs = None
        for attempt in range(PAGE_RETRY):
            try:
                page_songs = fetch_page_resilient(tid, song_begin, song_num)
                break
            except Exception as e:
                print(f"第 {page + 1}/{page_count} 页失败(尝试 {attempt + 1}/{PAGE_RETRY}): {e}",
                      file=sys.stderr)
                time.sleep(0.5)
        if page_songs is None:
            missing.append((song_begin, song_num))
            continue
        songlist.extend(page_songs)
        print(f"已获取 {len(songlist)}/{total}", file=sys.stderr)

    return title, total, songlist, missing


# ---------- 链接解析:复刻 logic/qqmusic.go 的 extractPlaylistID ----------
_PLAYLIST_RE = re.compile(r'.*playlist/\d+$')
_ID_PARAM_RE = re.compile(r'id=\d+')
_SHORT_RE = re.compile(r'fcgi-bin')
_DETAILS_RE = re.compile(r'details')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get_redirect_location(link: str):
    req = urllib.request.Request(link, method="GET")
    req.add_header("User-Agent", USER_AGENT)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(req, timeout=15)
        return None
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.headers.get("Location")
        raise


def _extract_number_after_keyword(s: str, keyword: str):
    idx = s.find(keyword)
    if idx < 0:
        return None
    start = idx + len(keyword)
    end = start
    while end < len(s) and s[end].isdigit():
        end += 1
    if end == start:
        return None
    return int(s[start:end])


def extract_playlist_id(link: str):
    if _PLAYLIST_RE.match(link):
        return _extract_number_after_keyword(link, "playlist/")
    if _ID_PARAM_RE.search(link):
        return _extract_number_after_keyword(link, "id=")
    if _SHORT_RE.search(link):
        redirected = get_redirect_location(link)
        if not redirected:
            return None
        return extract_playlist_id(redirected)
    if _DETAILS_RE.search(link):
        tid_str = parse_qs(urlparse(link).query).get("id", [None])[0]
        return int(tid_str) if tid_str else None
    return None


# ---------- 歌名标准化与格式化:复刻 misc/utils/music.go ----------
def standard_song_name(name: str) -> str:
    name = name.replace("（", " (").replace("）", ")")
    name = re.sub(r'\s?【.*】', '', name)
    return name


def build_songs(songlist, detailed: bool):
    songs = []
    for song in songlist:
        name = song.get("name", "")
        if not detailed:
            name = standard_song_name(name)
        singers = " / ".join(s.get("name", "") for s in song.get("singer", []))
        songs.append(f"{name} - {singers}")
    return songs


def format_songs(songs, fmt: str):
    if fmt in ("", "song-singer"):
        return songs
    out = []
    for s in songs:
        parts = s.split(" - ")
        if fmt == "singer-song" and len(parts) == 2:
            out.append(f"{parts[1]} - {parts[0]}")
        elif fmt == "song":
            out.append(parts[0])
        else:
            out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser(description="QQ音乐歌单导出")
    parser.add_argument("link", help="QQ音乐歌单链接")
    parser.add_argument("--detailed", action="store_true", help="保留原始歌名(不去括号)")
    parser.add_argument("--format", choices=["song-singer", "singer-song", "song"],
                        default="song-singer", help="输出格式,默认 song-singer")
    args = parser.parse_args()

    # ponytail: 签名为非平凡逻辑,留运行时长度/前缀断言,算法被改坏会立刻暴露
    sample = encrypt('{"req_0":{"module":"x"}}')
    assert sample.startswith("zzb") and len(sample) == 41, f"签名自检失败: {sample}"

    tid = extract_playlist_id(args.link)
    if not tid:
        print("无法从链接提取歌单 ID,请检查链接格式", file=sys.stderr)
        sys.exit(1)

    print(f"歌单 ID: {tid},正在获取...", file=sys.stderr)
    title, total, songlist, missing = fetch_playlist(tid)
    songs = format_songs(build_songs(songlist, args.detailed), args.format)

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title) or "playlist"
    filename = f"{safe_title}.txt"
    with io.open(filename, "w", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write(f"导出 {len(songs)} 首(歌单声称 {total} 首)\n\n")
        for s in songs:
            f.write(s + "\n")

    print(f"\n歌单: {title}")
    print(f"导出 {len(songs)} 首(歌单声称 {total} 首) → {filename}")
    if missing:
        miss_total = sum(n for _, n in missing)
        print(f"警告: {len(missing)} 个分页获取失败,缺失约 {miss_total} 首:",
              file=sys.stderr)
        for begin, num in missing:
            print(f"  第 {begin + 1}-{begin + num} 首", file=sys.stderr)


if __name__ == "__main__":
    main()
