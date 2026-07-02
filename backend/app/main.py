"""FastAPI 入口：QQ 音乐歌单解析 Web 服务。"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .log import logger
from .qqmusic.service import QQMusicError, parse_playlist
from .schemas import PlaylistRequest, PlaylistResponse

app = FastAPI(title="qqplaylist-export API", version="1.0.0")


def _client_ip(request: Request) -> str:
    """限流 key：优先取反代 X-Forwarded-For 首段，回退到直连 IP。

    ponytail: 云部署必有反向代理，slowapi 默认 get_remote_address 会把
    所有请求记成代理 IP 而误伤全局；取 XFF 首段即可，不处理多级链信任问题。
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_ip, default_limits=[])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 前端构建产物目录（由 Dockerfile 或 yarn build 生成）
DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _format_songs(songs: list[str], fmt: str) -> list[str]:
    """按 format 调整 "歌名 - 歌手" 顺序。"""
    if fmt in ("", "song-singer"):
        return songs
    result = []
    for song in songs:
        parts = song.split(" - ")
        if fmt == "singer-song":
            result.append(f"{parts[1]} - {parts[0]}" if len(parts) == 2 else song)
        elif fmt == "song":
            result.append(parts[0] if parts else song)
        else:
            result.append(song)
    return result


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/playlist", response_model=PlaylistResponse)
@limiter.limit(settings.rate_limit)
async def playlist(request: Request, req: PlaylistRequest) -> PlaylistResponse:
    logger.info("歌单请求：%s，详细：%s，格式：%s，顺序：%s",
                req.url, req.detailed, req.format, req.order)
    try:
        result = await parse_playlist(req.url, req.detailed)
    except QQMusicError as e:
        raise HTTPException(status_code=400, detail=str(e))

    songs = _format_songs(result["songs"], req.format)
    if req.order == "reverse":
        songs = songs[::-1]
    return PlaylistResponse(
        name=result["name"],
        songs=songs,
        songs_count=result["songs_count"],
        total_count=result["total_count"],
    )


# 以下为前端静态托管，仅在 frontend/dist 存在时启用。
# 必须放在 API 路由之后：API 路径优先匹配，其余落到静态文件。
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
else:
    logger.warning("前端构建产物 %s 不存在，仅提供 API", DIST)
