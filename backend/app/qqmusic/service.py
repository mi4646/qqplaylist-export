"""QQ音乐歌单解析业务编排：链接解析 → 分页拉取 → 构建歌曲列表。"""
import asyncio
import re
from urllib.parse import urlparse, parse_qs

import httpx

from ..log import logger
from .client import fetch_page, fetch_page_resilient, get_redirect_location

# 分页参数
MAX_SONGS_PER_PAGE = 30
MAX_TOTAL_SONGS = 10000
PAGE_RETRY = 3  # ponytail: 单页失败重试次数，网络抖动时再调高

# 链接形态正则
_PLAYLIST_RE = re.compile(r".*playlist/\d+$")
_ID_PARAM_RE = re.compile(r"id=\d+")

# 已知的无效链接
_INVALID_LINK = "https://i.y.qq.com/v8/playsong.html"


class QQMusicError(Exception):
    """QQ音乐解析错误，向用户返回中文提示。"""


def _extract_number(s: str, keyword: str) -> int:
    idx = s.find(keyword)
    if idx < 0:
        raise QQMusicError(f"未找到关键词: {keyword}")
    start = idx + len(keyword)
    end = start
    while end < len(s) and s[end].isdigit():
        end += 1
    if end == start:
        raise QQMusicError(f"数字转换失败: {keyword}")
    return int(s[start:end])


async def _extract_playlist_id(client: httpx.AsyncClient, link: str) -> int:
    # 1. playlist/数字 格式
    if _PLAYLIST_RE.match(link):
        return _extract_number(link, "playlist/")
    # 2. id=数字 格式
    if _ID_PARAM_RE.search(link):
        return _extract_number(link, "id=")
    # 3. 短链，需重定向后递归
    if "fcgi-bin" in link:
        redirected = await get_redirect_location(client, link)
        if not redirected:
            raise QQMusicError("处理短链接失败")
        return await _extract_playlist_id(client, redirected)
    # 4. details 页链接，从 query 取 id
    if "details" in link:
        tid_str = parse_qs(urlparse(link).query).get("id", [""])[0]
        if not tid_str:
            raise QQMusicError("提取歌单ID失败")
        return int(tid_str)
    raise QQMusicError("无效的歌单链接格式")


def _standard_song_name(name: str) -> str:
    """标准化歌名：中文括号转英文括号（左括号前补空格），去除【...】。"""
    s = name.replace("（", " (").replace("）", ")")
    return re.sub(r"\s?【.*?】", "", s)


def _build_song_list(response: dict, detailed: bool) -> tuple[str, list[str], int]:
    req0 = response.get("req_0", {})
    data = req0.get("data", {})
    dirinfo = data.get("dirinfo", {})
    title = dirinfo.get("title", "")
    songnum = dirinfo.get("songnum", 0)

    songs: list[str] = []
    for song in data.get("songlist", []):
        name = song.get("name", "")
        name = name if detailed else _standard_song_name(name)
        singers = " / ".join(s.get("name", "") for s in song.get("singer", []))
        songs.append(f"{name} - {singers}")
    return title, songs, songnum


async def _fetch_playlist_data(client: httpx.AsyncClient, tid: int) -> tuple[dict, int]:
    # 先取第一页，同时得到总数
    basic = await fetch_page(client, tid, 0, MAX_SONGS_PER_PAGE)
    total = basic.get("req_0", {}).get("data", {}).get("dirinfo", {}).get("songnum", 0)
    # 原始歌单总数（截断前），供前端展示「解析数/总数」
    original_total = total
    if total <= MAX_SONGS_PER_PAGE:
        return basic, original_total

    logger.info("歌单包含 %d 首歌曲，需要分页获取", total)
    if total > MAX_TOTAL_SONGS:
        logger.warning(
            "歌单歌曲数量(%d)超过最大支持数量(%d)，将只获取前 %d 首",
            total, MAX_TOTAL_SONGS, MAX_TOTAL_SONGS,
        )
        total = MAX_TOTAL_SONGS

    # 合并所有页的 songlist；单页失败重试，仍失败才计入 missing
    merged_songlist = list(basic.get("req_0", {}).get("data", {}).get("songlist", []))
    page_count = (total + MAX_SONGS_PER_PAGE - 1) // MAX_SONGS_PER_PAGE
    missing = 0
    for page in range(1, page_count):
        song_begin = page * MAX_SONGS_PER_PAGE
        song_num = min(MAX_SONGS_PER_PAGE, total - song_begin)
        page_songs: list | None = None
        for attempt in range(PAGE_RETRY):
            try:
                page_songs = await fetch_page_resilient(client, tid, song_begin, song_num)
                break
            except Exception as e:
                logger.error(
                    "第 %d/%d 页失败(尝试 %d/%d): %s",
                    page + 1, page_count, attempt + 1, PAGE_RETRY, e,
                )
                await asyncio.sleep(0.5)
        if page_songs is None:
            missing += song_num
            continue
        merged_songlist.extend(page_songs)

    if missing:
        logger.warning("分页获取失败，缺失约 %d 首", missing)
    basic.setdefault("req_0", {}).setdefault("data", {})["songlist"] = merged_songlist
    basic["req_0"]["data"].setdefault("dirinfo", {})["songnum"] = len(merged_songlist)
    logger.info("成功获取全部 %d 首歌曲", len(merged_songlist))
    return basic, original_total


async def parse_playlist(link: str, detailed: bool) -> dict:
    """解析 QQ 音乐歌单，返回 {name, songs, songs_count, total_count}。

    songs_count 为实际解析出的歌曲数；total_count 为 QQ 音乐 API 返回的歌单原始总数。
    """
    if link == _INVALID_LINK:
        raise QQMusicError("无效歌单链接，请检查是否正确")

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        tid = await _extract_playlist_id(client, link)
        if tid == 0:
            raise QQMusicError("无效的歌单链接")
        try:
            response, total_count = await _fetch_playlist_data(client, tid)
        except Exception as e:
            logger.error("获取QQ音乐歌单数据失败: %s", e)
            raise QQMusicError(f"获取歌单数据失败: {e}")

    name, songs, songs_count = _build_song_list(response, detailed)
    return {
        "name": name,
        "songs": songs,
        "songs_count": songs_count,
        "total_count": total_count,
    }
