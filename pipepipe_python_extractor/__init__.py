"""
pipepipe_python_extractor
=========================
A Python port of NewPipeExtractor (the core library behind PipePipe / NewPipe).

Supported services
------------------
- YouTube: stream info, search, channel, playlist

Quick start
-----------
    from pipepipe_python_extractor import PipePipe

    pp = PipePipe()

    # Get video info
    info = pp.get_stream_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(info.name, info.duration)

    # Search
    results = pp.search("python tutorial")
    for item in results.streams:
        print(item.name, item.uploader)

    # Channel videos
    channel_info = pp.get_channel_info("https://www.youtube.com/@PewDiePie")
    videos, _ = pp.get_channel_videos("https://www.youtube.com/@PewDiePie")

    # Playlist
    playlist, _ = pp.get_playlist("https://www.youtube.com/playlist?list=PLxxxxxx")
"""

from .core import (
    Downloader,
    StreamInfo, StreamInfoItem, ChannelInfo, PlaylistInfo, SearchResult,
    VideoStream, AudioStream, SubtitleStream, Image,
    MediaFormat,
    ExtractionException, ContentNotAvailableException,
    AgeRestrictedContentException, PrivateContentException,
    GeographicRestrictionException, PaidContentException,
    ParsingException, NotFoundException,
)
from .services.youtube import (
    YoutubeStreamExtractor,
    YoutubeSearchExtractor,
    YoutubeChannelExtractor,
    YoutubePlaylistExtractor,
    is_youtube_url,
)
from .utils import format_duration, format_count


class PipePipe:
    """
    High-level facade — the main entry point, analogous to NewPipe.java.

    Parameters
    ----------
    proxy : str, optional
        HTTP/HTTPS proxy URL, e.g. "http://127.0.0.1:8080"
    timeout : int
        Request timeout in seconds (default 15)
    """

    def __init__(self, proxy: str = None, timeout: int = 15):
        self._downloader = Downloader(proxy=proxy, timeout=timeout)
        self._stream = YoutubeStreamExtractor(self._downloader)
        self._search = YoutubeSearchExtractor(self._downloader)
        self._channel = YoutubeChannelExtractor(self._downloader)
        self._playlist = YoutubePlaylistExtractor(self._downloader)

    # ── Stream ────────────────────────────────────────────────────────────────

    def get_stream_info(self, url: str) -> StreamInfo:
        """Extract full metadata and stream URLs for a video."""
        if is_youtube_url(url) or len(url) == 11:
            return self._stream.extract(url)
        raise ExtractionException(f"Unsupported URL: {url}")

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, next_page_token: str = "") -> SearchResult:
        """Search YouTube. Pass `next_page_token` to paginate."""
        return self._search.search(query, next_page_token=next_page_token)

    # ── Channel ───────────────────────────────────────────────────────────────

    def get_channel_info(self, url: str) -> ChannelInfo:
        """Get channel metadata (name, subscriber count, etc.)."""
        return self._channel.get_channel_info(url)

    def get_channel_videos(
        self, url: str, continuation_token: str = ""
    ) -> tuple[list[StreamInfoItem], str]:
        """
        Get videos uploaded by a channel.
        Returns (videos, next_page_token). Pass next_page_token to paginate.
        """
        return self._channel.get_videos(url, continuation_token=continuation_token)

    # ── Playlist ──────────────────────────────────────────────────────────────

    def get_playlist(
        self, url: str, continuation_token: str = ""
    ) -> tuple[PlaylistInfo, str]:
        """
        Get playlist metadata and videos.
        Returns (PlaylistInfo, next_page_token). Pass next_page_token to paginate.
        """
        return self._playlist.get_playlist_info(url, continuation_token=continuation_token)


__version__ = "1.0.0"
__all__ = [
    "PipePipe",
    "StreamInfo", "StreamInfoItem", "ChannelInfo", "PlaylistInfo", "SearchResult",
    "VideoStream", "AudioStream", "SubtitleStream", "Image",
    "MediaFormat",
    "ExtractionException", "ContentNotAvailableException",
    "AgeRestrictedContentException", "PrivateContentException",
    "GeographicRestrictionException", "PaidContentException",
    "ParsingException", "NotFoundException",
    "format_duration", "format_count",
]
