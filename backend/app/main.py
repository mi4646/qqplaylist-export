"""FastAPI 入口：QQ 音乐歌单解析 Web 服务。"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .log import logger
from .qqmusic.service import QQMusicError, parse_playlist
from .schemas import PlaylistRequest, PlaylistResponse

app = FastAPI(title="QQMusic Playlist API", version="1.0.0")

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
async def playlist(req: PlaylistRequest) -> PlaylistResponse:
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
