import re
from urllib.parse import urlparse, parse_qs
from ...core.link_handler import LinkHandler
from ...core.exceptions import ParsingException


VIDEO_URL_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?.*v=|youtu\.be/)([a-zA-Z0-9_-]{11})"),
    re.compile(r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
    re.compile(r"youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    re.compile(r"youtube\.com/v/([a-zA-Z0-9_-]{11})"),
    re.compile(r"youtube\.com/live/([a-zA-Z0-9_-]{11})"),
]

CHANNEL_URL_PATTERNS = [
    re.compile(r"youtube\.com/channel/([^/?&]+)"),
    re.compile(r"youtube\.com/@([^/?&]+)"),
    re.compile(r"youtube\.com/c/([^/?&]+)"),
    re.compile(r"youtube\.com/user/([^/?&]+)"),
]

PLAYLIST_URL_PATTERNS = [
    re.compile(r"youtube\.com/playlist\?.*list=([a-zA-Z0-9_-]+)"),
]


def extract_video_id(url: str) -> str:
    for pattern in VIDEO_URL_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    # bare ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
        return url
    raise ParsingException(f"Cannot extract video ID from URL: {url}")


def extract_channel_id(url: str) -> str:
    for pattern in CHANNEL_URL_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    raise ParsingException(f"Cannot extract channel ID from URL: {url}")


def extract_playlist_id(url: str) -> str:
    for pattern in PLAYLIST_URL_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    raise ParsingException(f"Cannot extract playlist ID from URL: {url}")


def is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in (
        "www.youtube.com", "youtube.com", "youtu.be",
        "m.youtube.com", "music.youtube.com",
    )


def video_id_to_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def channel_id_to_url(channel_id: str) -> str:
    if channel_id.startswith("UC"):
        return f"https://www.youtube.com/channel/{channel_id}"
    return f"https://www.youtube.com/@{channel_id}"


def playlist_id_to_url(playlist_id: str) -> str:
    return f"https://www.youtube.com/playlist?list={playlist_id}"
