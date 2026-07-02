"""QQ音乐 HTTP 客户端：构造请求体、签名、分页拉取。"""
import json
import time

import httpx

from ..log import logger
from .sign import encrypt

# API 入口
API_URL = "https://u6.y.qq.com/cgi-bin/musics.fcg?sign=%s&_=%d"

# 依次尝试的平台参数
PLATFORMS = ["-1", "android", "iphone", "h5", "wxfshare", "iphone_wx", "windows"]


def build_request_body(tid: int, platform: str, song_begin: int, song_num: int) -> str:
    """构造 QQ 音乐请求体（紧凑 JSON，与 Go 版字段顺序一致）。"""
    body = {
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
    }
    return json.dumps(body, separators=(",", ":"))


async def fetch_page(
    client: httpx.AsyncClient, tid: int, song_begin: int, song_num: int
) -> dict:
    """拉取歌单指定页。依次尝试各平台参数，响应 code==0 视为成功。"""
    last_err: Exception | None = None
    for platform in PLATFORMS:
        body = build_request_body(tid, platform, song_begin, song_num)
        sign = encrypt(body)
        url = API_URL % (sign, int(time.time() * 1000))
        try:
            resp = await client.post(
                url,
                content=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as e:
            logger.error("HTTP 请求失败(平台:%s): %s", platform, e)
            last_err = e
            continue
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError as e:
            last_err = e
            continue
        if data.get("code", 0) == 0:
            return data
        last_err = f"code={data.get('code')}"
    raise RuntimeError(f"尝试所有平台参数均失败: {last_err}")


async def fetch_page_resilient(
    client: httpx.AsyncClient, tid: int, song_begin: int, song_num: int
) -> list:
    """获取一页歌曲列表。整页失败时拆半重试；单首仍失败则放弃该首。

    QQ 接口对个别 (begin, num) 组合会确定性返回 code!=0（非网络错误，换 platform
    和等待均无效）。实测拆成更小的 num 即可绕过，故整页失败时二分拆分合并结果。
    若拆到单首仍失败，说明该位置歌曲被 QQ 下架/区域限制，任何粒度都取不到——
    此时放弃这一首而非抛错，避免一页 30 首被级联丢弃（丢 1 而非丢 30）。
    """
    try:
        data = await fetch_page(client, tid, song_begin, song_num)
    except RuntimeError:
        if song_num <= 1:
            logger.warning("歌曲位置 #%d 取不到，跳过（可能已下架/区域限制）", song_begin)
            return []
        half = song_num // 2
        logger.warning(
            "整页(begin=%d,num=%d)被拒，拆分为 %d+%d 重试",
            song_begin, song_num, half, song_num - half,
        )
        left = await fetch_page_resilient(client, tid, song_begin, half)
        right = await fetch_page_resilient(client, tid, song_begin + half, song_num - half)
        return left + right
    return data.get("req_0", {}).get("data", {}).get("songlist", [])


async def get_redirect_location(client: httpx.AsyncClient, link: str) -> str:
    """获取短链重定向目标（不跟随跳转）。"""
    resp = await client.get(link, follow_redirects=False)
    return resp.headers.get("Location", "")
