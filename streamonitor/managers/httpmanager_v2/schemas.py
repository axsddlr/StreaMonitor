from dataclasses import dataclass
from typing import Any


@dataclass
class StreamerDTO:
    username: str
    site: str
    siteslug: str
    running: bool
    recording: bool
    status_code: int
    status_text: str
    url: str
    gender: Any
    country: Any
    country_flag: str
    country_name: str
    video_count: int
    video_total_size: int


@dataclass
class RecordingDTO:
    filename: str
    filesize: int
    filesize_human: str
    abs_path: str


@dataclass
class DiskSpaceDTO:
    free: int
    total: int
    free_human: str
    total_human: str
    percentage_free: float


@dataclass
class StreamersResponse:
    streamers: list[StreamerDTO]
    disk: DiskSpaceDTO


@dataclass
class TokenResponse:
    token: str


@dataclass
class MessageResponse:
    message: str


@dataclass
class AddStreamerRequest:
    username: str
    site: str
