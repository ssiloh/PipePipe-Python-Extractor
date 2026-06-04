"""
YoutubeChannelExtractor — mirrors NewPipeExtractor's YoutubeChannelExtractor.
"""
import re
from typing import Optional
from ....core.downloader import Downloader
from ....core.stream_info import Image, ChannelInfo, StreamInfoItem, PlaylistInfo
from ..innertube import InnerTubeClient, fetch_initial_data
from ..link_handler import extract_channel_id, channel_id_to_url, video_id_to_url
from .search_extractor import _get_nested, _parse_thumbnails, _text_runs, _parse_duration


def _resolve_channel_id(downloader: Downloader, url: str) -> str:
    """
    If URL uses @handle or /c/ form, we need to resolve to UC... channel ID.
    We do this by fetching the page and reading the browseId from ytInitialData.
    """
    import json, re as _re
    html = downloader.get_text(url)
    m = _re.search(r'"channelId"\s*:\s*"(UC[^"]+)"', html)
    if m:
        return m.group(1)
    m = _re.search(r'"browseId"\s*:\s*"(UC[^"]+)"', html)
    if m:
        return m.group(1)
    return extract_channel_id(url)


def _parse_video_renderer(r: dict) -> Optional[StreamInfoItem]:
    video_id = r.get("videoId", "")
    if not video_id:
        return None
    title = _text_runs(r.get("title", {}))
    duration_text = _text_runs(_get_nested(r, "lengthText", default={}))
    duration = _parse_duration(duration_text) if duration_text else -1
    thumbs = _parse_thumbnails(_get_nested(r, "thumbnail", "thumbnails", default=[]))
    published = _text_runs(r.get("publishedTimeText", {}))
    view_text = _text_runs(r.get("viewCountText", {}))
    view_count = int(re.sub(r"[^0-9]", "", view_text)) if re.sub(r"[^0-9]", "", view_text) else -1
    return StreamInfoItem(
        id=video_id,
        url=video_id_to_url(video_id),
        name=title,
        thumbnails=thumbs,
        duration=duration,
        view_count=view_count,
        upload_date=published,
    )


class YoutubeChannelExtractor:
    def __init__(self, downloader: Downloader):
        self.downloader = downloader
        self._client = InnerTubeClient(downloader, "WEB")

    def get_channel_info(self, url: str) -> ChannelInfo:
        channel_id = _resolve_channel_id(self.downloader, url)
        data = self._client.browse(channel_id)

        header = _get_nested(data, "header", "c4TabbedHeaderRenderer", default={})
        if not header:
            header = _get_nested(data, "header", "pageHeaderRenderer", default={})

        name = _text_runs(header.get("title", {})) or header.get("title", "")
        desc = _get_nested(
            data, "metadata", "channelMetadataRenderer", "description", default=""
        )
        thumbs = _parse_thumbnails(
            _get_nested(header, "avatar", "thumbnails", default=[])
        )
        banner_thumbs = _get_nested(header, "banner", "thumbnails", default=[])
        banner_url = banner_thumbs[-1].get("url", "") if banner_thumbs else ""
        sub_text = _text_runs(header.get("subscriberCountText", {}))
        subs = -1
        if sub_text:
            m = re.search(r"([\d.,]+)\s*([KMB]?)", sub_text, re.I)
            if m:
                n, suffix = m.group(1).replace(",", ""), m.group(2).upper()
                try:
                    n = float(n)
                    mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(suffix, 1)
                    subs = int(n * mult)
                except ValueError:
                    pass

        is_verified = any(
            _get_nested(b, "metadataBadgeRenderer", "style", default="") == "BADGE_STYLE_TYPE_VERIFIED"
            for b in header.get("badges", [])
        )

        return ChannelInfo(
            id=channel_id,
            url=channel_id_to_url(channel_id),
            name=name,
            description=desc,
            thumbnails=thumbs,
            banner_url=banner_url,
            subscriber_count=subs,
            verified=is_verified,
        )

    def get_videos(self, url: str, continuation_token: str = "") -> tuple[list[StreamInfoItem], str]:
        channel_id = _resolve_channel_id(self.downloader, url)
        videos_browse_id = channel_id + "/videos"

        if continuation_token:
            data = self._client.browse(videos_browse_id, continuation=continuation_token)
        else:
            data = self._client.browse(videos_browse_id)

        videos = []
        next_token = ""

        # Walk tabs to find the Videos tab
        tabs = _get_nested(data, "contents", "twoColumnBrowseResultsRenderer", "tabs", default=[])
        for tab in tabs:
            tr = tab.get("tabRenderer", {})
            if tr.get("selected") or tr.get("title", "").lower() == "videos":
                section_list = _get_nested(
                    tr, "content", "richGridRenderer", "contents", default=[]
                ) or _get_nested(
                    tr, "content", "sectionListRenderer", "contents", default=[]
                )
                for item in section_list:
                    # richItemRenderer (new layout)
                    ri = item.get("richItemRenderer", {})
                    vr = _get_nested(ri, "content", "videoRenderer", default={})
                    if vr:
                        parsed = _parse_video_renderer(vr)
                        if parsed:
                            videos.append(parsed)
                    # Continuation item
                    ci = item.get("continuationItemRenderer", {})
                    token = _get_nested(
                        ci, "continuationEndpoint", "continuationCommand", "token", default=""
                    )
                    if token:
                        next_token = token
                break

        # Continuation page layout
        if continuation_token and not videos:
            for cmd in data.get("onResponseReceivedActions", []):
                items = _get_nested(
                    cmd, "appendContinuationItemsAction", "continuationItems", default=[]
                )
                for item in items:
                    ri = item.get("richItemRenderer", {})
                    vr = _get_nested(ri, "content", "videoRenderer", default={})
                    if vr:
                        parsed = _parse_video_renderer(vr)
                        if parsed:
                            videos.append(parsed)
                    ci = item.get("continuationItemRenderer", {})
                    token = _get_nested(
                        ci, "continuationEndpoint", "continuationCommand", "token", default=""
                    )
                    if token:
                        next_token = token

        return videos, next_token
