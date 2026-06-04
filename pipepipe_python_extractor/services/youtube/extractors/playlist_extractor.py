"""
YoutubePlaylistExtractor — mirrors NewPipeExtractor's YoutubePlaylistExtractor.
"""
import re
from typing import Optional
from ....core.downloader import Downloader
from ....core.stream_info import Image, PlaylistInfo, StreamInfoItem
from ..innertube import InnerTubeClient
from ..link_handler import extract_playlist_id, playlist_id_to_url, video_id_to_url
from .search_extractor import _get_nested, _parse_thumbnails, _text_runs, _parse_duration


def _parse_playlist_video_renderer(r: dict) -> Optional[StreamInfoItem]:
    video_id = r.get("videoId", "")
    if not video_id:
        return None
    title = _text_runs(r.get("title", {}))
    duration_text = _text_runs(r.get("lengthText", {}))
    duration = _parse_duration(duration_text) if duration_text else -1
    thumbs = _parse_thumbnails(_get_nested(r, "thumbnail", "thumbnails", default=[]))
    uploader = _text_runs(r.get("shortBylineText", {}))
    return StreamInfoItem(
        id=video_id,
        url=video_id_to_url(video_id),
        name=title,
        thumbnails=thumbs,
        uploader=uploader,
        duration=duration,
    )


class YoutubePlaylistExtractor:
    def __init__(self, downloader: Downloader):
        self.downloader = downloader
        self._client = InnerTubeClient(downloader, "WEB")

    def get_playlist_info(self, url: str, continuation_token: str = "") -> tuple[PlaylistInfo, str]:
        playlist_id = extract_playlist_id(url)
        browse_id = "VL" + playlist_id

        if continuation_token:
            data = self._client.browse(browse_id, continuation=continuation_token)
        else:
            data = self._client.browse(browse_id)

        videos = []
        next_token = ""
        name = ""
        uploader = ""
        thumbs = []
        total_count = -1

        header = _get_nested(data, "header", "playlistHeaderRenderer", default={})
        if header:
            name = _text_runs(header.get("title", {}))
            uploader = _text_runs(header.get("ownerText", {}))
            count_text = _text_runs(header.get("numVideosText", {}))
            digits = re.sub(r"[^0-9]", "", count_text)
            if digits:
                total_count = int(digits)
            thumbs = _parse_thumbnails(
                _get_nested(header, "playlistHeaderBanner", "heroPlaylistThumbnailRenderer",
                            "thumbnail", "thumbnails", default=[])
            )

        # Parse video items
        def walk_items(items):
            nonlocal next_token
            for item in items:
                pvr = item.get("playlistVideoRenderer", {})
                if pvr:
                    parsed = _parse_playlist_video_renderer(pvr)
                    if parsed:
                        videos.append(parsed)
                ci = item.get("continuationItemRenderer", {})
                token = _get_nested(
                    ci, "continuationEndpoint", "continuationCommand", "token", default=""
                )
                if token:
                    next_token = token

        if not continuation_token:
            contents = _get_nested(
                data, "contents", "twoColumnBrowseResultsRenderer",
                "tabs", 0, "tabRenderer", "content", "sectionListRenderer",
                "contents", 0, "itemSectionRenderer", "contents", 0,
                "playlistVideoListRenderer", "contents",
                default=[]
            )
            walk_items(contents)
        else:
            for cmd in data.get("onResponseReceivedActions", []):
                items = _get_nested(
                    cmd, "appendContinuationItemsAction", "continuationItems", default=[]
                )
                walk_items(items)

        return PlaylistInfo(
            id=playlist_id,
            url=playlist_id_to_url(playlist_id),
            name=name,
            uploader=uploader,
            thumbnails=thumbs,
            stream_count=total_count,
            streams=videos,
        ), next_token
