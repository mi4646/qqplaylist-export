from typing import Literal

from pydantic import BaseModel


class PlaylistRequest(BaseModel):
    url: str
    detailed: bool = False
    format: Literal["song-singer", "singer-song", "song"] = "song-singer"
    order: Literal["normal", "reverse"] = "normal"


class PlaylistResponse(BaseModel):
    name: str
    songs: list[str]
    songs_count: int
    total_count: int
