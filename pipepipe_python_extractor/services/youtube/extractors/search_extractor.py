"""
YoutubeSearchExtractor — mirrors NewPipeExtractor's YoutubeSearchExtractor.
"""
import re
from typing import Optional
from ....core.downloader import Downloader
from ....core.stream_info import Image, StreamInfoItem, ChannelInfo, PlaylistInfo, SearchResult
from ..innertube import InnerTubeClient
from ..link_handler import video_id_to_url, channel_id_to_url, playlist_id_to_url


def _get_nested(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, {})
    return d if d != {} else default


def _parse_thumbnails(thumbs) -> list[Image]:
    images = []
    if isinstance(thumbs, list):
        for t in thumbs:
            url = t.get("url", "")
            if url and not url.startswith("data:"):
                images.append(Image(
                    url=url.lstrip("//") if url.startswith("//") else url,
                    width=t.get("width", 0),
                    height=t.get("height", 0),
                ))
    return images


def _text_runs(obj) -> str:
    if isinstance(obj, dict):
        if "simpleText" in obj:
            return obj["simpleText"]
        if "runs" in obj:
            return "".join(r.get("text", "") for r in obj["runs"])
    return ""


def _parse_duration(text: str) -> int:
    """Parse 'H:MM:SS' or 'M:SS' into seconds."""
    parts = text.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except ValueError:
        pass
    return -1


def _parse_view_count(text: str) -> int:
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else -1


def _parse_video_renderer(r: dict) -> Optional[StreamInfoItem]:
    video_id = r.get("videoId", "")
    if not video_id:
        return None
    title = _text_runs(r.get("title", {}))
    uploader = _text_runs(_get_nested(r, "ownerText", default={}))
    uploader_id = ""
    owner_text = r.get("ownerText", {})
    for run in owner_text.get("runs", []):
        nav = run.get("navigationEndpoint", {})
        cid = _get_nested(nav, "browseEndpoint", "browseId", default="")
        if cid:
            uploader_id = cid
            break

    duration_text = _text_runs(_get_nested(r, "lengthText", default={}))
    duration = _parse_duration(duration_text) if duration_text else -1

    view_text = _text_runs(_get_nested(r, "viewCountText", default={}))
    view_count = _parse_view_count(view_text)

    published = _text_runs(r.get("publishedTimeText", {}))
    thumbs = _parse_thumbnails(_get_nested(r, "thumbnail", "thumbnails", default=[]))
    is_live = "LIVE" in _text_runs(r.get("badges", [{}][0]) if r.get("badges") else {})

    return StreamInfoItem(
        id=video_id,
        url=video_id_to_url(video_id),
        name=title,
        thumbnails=thumbs,
        uploader=uploader,
        uploader_url=channel_id_to_url(uploader_id) if uploader_id else "",
        duration=duration,
        view_count=view_count,
        upload_date=published,
        is_live=is_live,
    )


def _parse_channel_renderer(r: dict) -> Optional[ChannelInfo]:
    channel_id = r.get("channelId", "")
    if not channel_id:
        return None
    name = _text_runs(r.get("title", {}))
    desc = _text_runs(r.get("descriptionSnippet", {}))
    thumbs = _parse_thumbnails(_get_nested(r, "thumbnail", "thumbnails", default=[]))
    sub_text = _text_runs(r.get("subscriberCountText", {}))
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
    return ChannelInfo(
        id=channel_id,
        url=channel_id_to_url(channel_id),
        name=name,
        description=desc,
        thumbnails=thumbs,
        subscriber_count=subs,
    )


def _parse_playlist_renderer(r: dict) -> Optional[PlaylistInfo]:
    playlist_id = r.get("playlistId", "")
    if not playlist_id:
        return None
    title = _text_runs(r.get("title", {}))
    uploader = _text_runs(r.get("shortBylineText", {}))
    count_text = _text_runs(r.get("videoCountText", {}))
    count = -1
    digits = re.sub(r"[^0-9]", "", count_text)
    if digits:
        count = int(digits)
    thumbs = _parse_thumbnails(_get_nested(r, "thumbnails", 0, "thumbnails", default=[]))
    return PlaylistInfo(
        id=playlist_id,
        url=playlist_id_to_url(playlist_id),
        name=title,
        uploader=uploader,
        thumbnails=thumbs,
        stream_count=count,
    )


def _walk_contents(contents: list) -> SearchResult:
    result = SearchResult(query="")
    for item in contents:
        vr = item.get("videoRenderer") or item.get("reelItemRenderer")
        if vr:
            parsed = _parse_video_renderer(vr)
            if parsed:
                result.streams.append(parsed)
            continue
        cr = item.get("channelRenderer")
        if cr:
            parsed = _parse_channel_renderer(cr)
            if parsed:
                result.channels.append(parsed)
            continue
        pr = item.get("playlistRenderer")
        if pr:
            parsed = _parse_playlist_renderer(pr)
            if parsed:
                result.playlists.append(parsed)
    return result


class YoutubeSearchExtractor:
    def __init__(self, downloader: Downloader):
        self.downloader = downloader
        self._client = InnerTubeClient(downloader, "WEB")

    def search(self, query: str, next_page_token: str = "") -> SearchResult:
        data = self._client.search(query, continuation=next_page_token)

        contents = []
        continuation_token = ""

        if not next_page_token:
            # First page: nested under estimatedResults / contents
            section_list = _get_nested(
                data,
                "contents", "twoColumnSearchResultsRenderer",
                "primaryContents", "sectionListRenderer", "contents",
                default=[]
            )
            for section in section_list:
                items = _get_nested(section, "itemSectionRenderer", "contents", default=[])
                contents.extend(items)
                # Grab continuation token for next page
                for cont in _get_nested(section, "itemSectionRenderer", "continuations", default=[]):
                    token = _get_nested(cont, "nextContinuationData", "continuation", default="")
                    if token:
                        continuation_token = token
        else:
            # Continuation page
            for cr in data.get("onResponseReceivedCommands", []):
                items = _get_nested(
                    cr, "appendContinuationItemsAction", "continuationItems", default=[]
                )
                for it in items:
                    ic = it.get("itemSectionRenderer", {}).get("contents", [])
                    contents.extend(ic)
                    for cont in it.get("itemSectionRenderer", {}).get("continuations", []):
                        token = _get_nested(cont, "nextContinuationData", "continuation", default="")
                        if token:
                            continuation_token = token

        result = _walk_contents(contents)
        result.query = query
        result.next_page_token = continuation_token
        return result
