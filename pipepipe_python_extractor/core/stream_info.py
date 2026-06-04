from dataclasses import dataclass, field
from typing import Optional
from .media_format import MediaFormat


@dataclass
class Image:
    url: str
    width: int = 0
    height: int = 0


@dataclass
class VideoStream:
    url: str
    format: MediaFormat
    resolution: str          # e.g. "1080p", "720p"
    bitrate: int = 0
    fps: int = 0
    width: int = 0
    height: int = 0
    itag: int = 0
    is_video_only: bool = False
    codec: str = ""

    def __repr__(self):
        return f"VideoStream({self.resolution}, {self.format.format_name}, video_only={self.is_video_only})"


@dataclass
class AudioStream:
    url: str
    format: MediaFormat
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 0
    itag: int = 0
    codec: str = ""
    language: str = ""
    audio_track_name: str = ""

    def __repr__(self):
        return f"AudioStream({self.format.format_name}, {self.bitrate}bps)"


@dataclass
class SubtitleStream:
    url: str
    language: str
    format: str = "vtt"
    is_auto_generated: bool = False


@dataclass
class StreamInfo:
    id: str
    url: str
    name: str
    description: str = ""
    uploader: str = ""
    uploader_url: str = ""
    uploader_avatars: list[Image] = field(default_factory=list)
    thumbnails: list[Image] = field(default_factory=list)
    duration: int = -1
    view_count: int = -1
    like_count: int = -1
    upload_date: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    age_limit: int = 0
    is_live: bool = False

    video_streams: list[VideoStream] = field(default_factory=list)
    audio_streams: list[AudioStream] = field(default_factory=list)
    video_only_streams: list[VideoStream] = field(default_factory=list)
    subtitle_streams: list[SubtitleStream] = field(default_factory=list)

    hls_url: str = ""
    dash_mpd_url: str = ""

    errors: list[Exception] = field(default_factory=list)

    @property
    def thumbnail_url(self) -> str:
        if self.thumbnails:
            return max(self.thumbnails, key=lambda t: t.width * t.height).url
        return ""

    @property
    def best_video_stream(self) -> Optional[VideoStream]:
        streams = [s for s in self.video_streams if not s.is_video_only]
        if not streams:
            return None
        return max(streams, key=lambda s: s.height)

    @property
    def best_audio_stream(self) -> Optional[AudioStream]:
        if not self.audio_streams:
            return None
        return max(self.audio_streams, key=lambda s: s.bitrate)

    def __repr__(self):
        return (
            f"StreamInfo(id={self.id!r}, name={self.name!r}, "
            f"duration={self.duration}s, "
            f"video_streams={len(self.video_streams)}, "
            f"audio_streams={len(self.audio_streams)})"
        )


@dataclass
class StreamInfoItem:
    id: str
    url: str
    name: str
    thumbnails: list[Image] = field(default_factory=list)
    uploader: str = ""
    uploader_url: str = ""
    duration: int = -1
    view_count: int = -1
    upload_date: str = ""
    is_live: bool = False
    short_description: str = ""

    @property
    def thumbnail_url(self) -> str:
        if self.thumbnails:
            return max(self.thumbnails, key=lambda t: t.width * t.height).url
        return ""

    def __repr__(self):
        return f"StreamInfoItem({self.name!r}, {self.uploader!r})"


@dataclass
class ChannelInfo:
    id: str
    url: str
    name: str
    description: str = ""
    thumbnails: list[Image] = field(default_factory=list)
    banner_url: str = ""
    subscriber_count: int = -1
    verified: bool = False


@dataclass
class PlaylistInfo:
    id: str
    url: str
    name: str
    uploader: str = ""
    thumbnails: list[Image] = field(default_factory=list)
    stream_count: int = -1
    streams: list[StreamInfoItem] = field(default_factory=list)


@dataclass
class SearchResult:
    query: str
    streams: list[StreamInfoItem] = field(default_factory=list)
    channels: list[ChannelInfo] = field(default_factory=list)
    playlists: list[PlaylistInfo] = field(default_factory=list)
    next_page_token: str = ""
