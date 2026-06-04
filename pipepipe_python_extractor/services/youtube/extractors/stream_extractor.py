"""
YoutubeStreamExtractor — mirrors NewPipeExtractor's YoutubeStreamExtractor.
Uses ANDROID + WEB InnerTube clients to extract all stream data.
"""
import re
from typing import Optional
from urllib.parse import parse_qs

from ....core.downloader import Downloader
from ....core.exceptions import (
    ParsingException,
    ContentNotAvailableException,
    AgeRestrictedContentException,
    PrivateContentException,
    GeographicRestrictionException,
    PaidContentException,
)
from ....core.media_format import MediaFormat
from ....core.stream_info import (
    Image, VideoStream, AudioStream, SubtitleStream, StreamInfo
)
from ..innertube import InnerTubeClient, fetch_initial_data
from ..cipher import SignatureCipher
from ..link_handler import extract_video_id, video_id_to_url

# itag → (resolution label, width, height, fps, format, codec, is_video_only)
ITAG_MAP: dict[int, dict] = {
    # Combined (video + audio)
    18:  {"res": "360p",  "w": 640,  "h": 360,  "fps": 30, "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": False},
    22:  {"res": "720p",  "w": 1280, "h": 720,  "fps": 30, "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": False},
    37:  {"res": "1080p", "w": 1920, "h": 1080, "fps": 30, "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": False},
    43:  {"res": "360p",  "w": 640,  "h": 360,  "fps": 30, "fmt": MediaFormat.WEBM,    "codec": "vp8",   "vo": False},
    # Video-only
    137: {"res": "1080p", "w": 1920, "h": 1080, "fps": 30,  "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": True},
    248: {"res": "1080p", "w": 1920, "h": 1080, "fps": 30,  "fmt": MediaFormat.WEBM,    "codec": "vp9",   "vo": True},
    136: {"res": "720p",  "w": 1280, "h": 720,  "fps": 30,  "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": True},
    247: {"res": "720p",  "w": 1280, "h": 720,  "fps": 30,  "fmt": MediaFormat.WEBM,    "codec": "vp9",   "vo": True},
    135: {"res": "480p",  "w": 854,  "h": 480,  "fps": 30,  "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": True},
    244: {"res": "480p",  "w": 854,  "h": 480,  "fps": 30,  "fmt": MediaFormat.WEBM,    "codec": "vp9",   "vo": True},
    134: {"res": "360p",  "w": 640,  "h": 360,  "fps": 30,  "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": True},
    243: {"res": "360p",  "w": 640,  "h": 360,  "fps": 30,  "fmt": MediaFormat.WEBM,    "codec": "vp9",   "vo": True},
    133: {"res": "240p",  "w": 426,  "h": 240,  "fps": 30,  "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": True},
    242: {"res": "240p",  "w": 426,  "h": 240,  "fps": 30,  "fmt": MediaFormat.WEBM,    "codec": "vp9",   "vo": True},
    160: {"res": "144p",  "w": 256,  "h": 144,  "fps": 30,  "fmt": MediaFormat.MPEG_4,  "codec": "avc1",  "vo": True},
    278: {"res": "144p",  "w": 256,  "h": 144,  "fps": 30,  "fmt": MediaFormat.WEBM,    "codec": "vp9",   "vo": True},
    # 60fps
    298: {"res": "720p60",  "w": 1280, "h": 720,  "fps": 60, "fmt": MediaFormat.MPEG_4, "codec": "avc1",  "vo": True},
    302: {"res": "720p60",  "w": 1280, "h": 720,  "fps": 60, "fmt": MediaFormat.WEBM,   "codec": "vp9",   "vo": True},
    299: {"res": "1080p60", "w": 1920, "h": 1080, "fps": 60, "fmt": MediaFormat.MPEG_4, "codec": "avc1",  "vo": True},
    303: {"res": "1080p60", "w": 1920, "h": 1080, "fps": 60, "fmt": MediaFormat.WEBM,   "codec": "vp9",   "vo": True},
    # Audio only
    139: {"bitrate": 48000,  "fmt": MediaFormat.M4A,   "codec": "aac",  "sr": 22050},
    140: {"bitrate": 128000, "fmt": MediaFormat.M4A,   "codec": "aac",  "sr": 44100},
    141: {"bitrate": 256000, "fmt": MediaFormat.M4A,   "codec": "aac",  "sr": 44100},
    249: {"bitrate": 50000,  "fmt": MediaFormat.WEBMA, "codec": "opus", "sr": 48000},
    250: {"bitrate": 70000,  "fmt": MediaFormat.WEBMA, "codec": "opus", "sr": 48000},
    251: {"bitrate": 160000, "fmt": MediaFormat.WEBMA, "codec": "opus", "sr": 48000},
}

AUDIO_ITAGS = {139, 140, 141, 249, 250, 251}


def _get_nested(d: dict, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, {})
    return d if d != {} else default


def _parse_thumbnails(thumbs_data) -> list[Image]:
    images = []
    if isinstance(thumbs_data, list):
        for t in thumbs_data:
            url = t.get("url", "")
            if url:
                images.append(Image(
                    url=url.lstrip("//") if url.startswith("//") else url,
                    width=t.get("width", 0),
                    height=t.get("height", 0),
                ))
    return images


def _parse_view_count(text: str) -> int:
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else -1


def _parse_subscribe_count(text: str) -> int:
    text = text.upper().replace(",", "").strip()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return -1
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else -1


class YoutubeStreamExtractor:
    def __init__(self, downloader: Downloader):
        self.downloader = downloader
        self._android_client = InnerTubeClient(downloader, "ANDROID")
        self._web_client = InnerTubeClient(downloader, "WEB")
        self._player_js: Optional[str] = None
        self._cipher: Optional[SignatureCipher] = None

    def _get_cipher(self, player_js_url: str) -> SignatureCipher:
        if self._player_js is None and player_js_url:
            self._player_js = self.downloader.get_text(player_js_url)
            self._cipher = SignatureCipher(self._player_js)
        return self._cipher

    def _check_playability(self, player_response: dict):
        ps = player_response.get("playabilityStatus", {})
        status = ps.get("status", "")
        reason = ps.get("reason", "")

        if status == "OK":
            return
        elif status == "LOGIN_REQUIRED":
            if "age" in reason.lower() or "mature" in reason.lower():
                raise AgeRestrictedContentException(reason)
            raise PrivateContentException(reason)
        elif status == "UNPLAYABLE":
            if "rental" in reason.lower() or "purchase" in reason.lower():
                raise PaidContentException(reason)
            raise ContentNotAvailableException(reason)
        elif status == "ERROR":
            if "not found" in reason.lower() or "doesn't exist" in reason.lower():
                from ....core.exceptions import NotFoundException
                raise NotFoundException(reason)
            raise ContentNotAvailableException(reason)
        elif status == "LIVE_STREAM_OFFLINE":
            raise ContentNotAvailableException("Live stream is offline: " + reason)

    def _parse_stream_url(self, fmt: dict, player_js_url: str) -> str:
        url = fmt.get("url", "")
        sc = fmt.get("signatureCipher") or fmt.get("cipher", "")
        if not url and sc:
            cipher = self._get_cipher(player_js_url)
            if cipher:
                url = cipher.decode_stream_url(f"?signatureCipher={sc}")
        elif url and player_js_url:
            cipher = self._get_cipher(player_js_url)
            if cipher:
                url = cipher.decode_stream_url(url)
        return url

    def _parse_formats(self, streaming_data: dict, player_js_url: str) -> tuple:
        video_streams = []
        audio_streams = []
        video_only_streams = []

        all_formats = (
            streaming_data.get("formats", []) +
            streaming_data.get("adaptiveFormats", [])
        )

        for fmt in all_formats:
            itag = fmt.get("itag", 0)
            url = self._parse_stream_url(fmt, player_js_url)
            if not url:
                continue

            mime_type = fmt.get("mimeType", "")
            bitrate = fmt.get("bitrate", 0) or fmt.get("averageBitrate", 0)

            if itag in AUDIO_ITAGS or mime_type.startswith("audio/"):
                info = ITAG_MAP.get(itag, {})
                # Parse codec from mimeType
                codec = ""
                cm = re.search(r'codecs="([^"]+)"', mime_type)
                if cm:
                    codec = cm.group(1)
                audio_streams.append(AudioStream(
                    url=url,
                    format=info.get("fmt", MediaFormat.M4A if "mp4" in mime_type else MediaFormat.WEBMA),
                    bitrate=info.get("bitrate", bitrate),
                    sample_rate=int(fmt.get("audioSampleRate", info.get("sr", 44100))),
                    channels=fmt.get("audioChannels", 2),
                    itag=itag,
                    codec=codec or info.get("codec", ""),
                ))
            elif mime_type.startswith("video/"):
                info = ITAG_MAP.get(itag, {})
                width = fmt.get("width", info.get("w", 0))
                height = fmt.get("height", info.get("h", 0))
                fps = fmt.get("fps", info.get("fps", 30))
                # Detect video-only: adaptive formats without audioChannels
                is_video_only = "audioChannels" not in fmt and itag not in {18, 22, 37, 43}
                res_label = info.get("res", f"{height}p")
                if fps and fps > 30:
                    res_label = f"{height}p{fps}"

                codec = ""
                cm = re.search(r'codecs="([^"]+)"', mime_type)
                if cm:
                    codec = cm.group(1).split(",")[0].strip()

                fmt_type = info.get("fmt", MediaFormat.MPEG_4 if "mp4" in mime_type else MediaFormat.WEBM)
                vs = VideoStream(
                    url=url,
                    format=fmt_type,
                    resolution=res_label,
                    bitrate=bitrate,
                    fps=fps,
                    width=width,
                    height=height,
                    itag=itag,
                    is_video_only=is_video_only,
                    codec=codec or info.get("codec", ""),
                )
                if is_video_only:
                    video_only_streams.append(vs)
                else:
                    video_streams.append(vs)

        return video_streams, audio_streams, video_only_streams

    def _parse_subtitles(self, captions_data: dict) -> list[SubtitleStream]:
        subs = []
        tracks = _get_nested(captions_data, "playerCaptionsTracklistRenderer", "captionTracks", default=[])
        for track in tracks:
            base_url = track.get("baseUrl", "")
            lang = _get_nested(track, "languageCode", default="")
            is_auto = track.get("kind", "") == "asr"
            if base_url:
                subs.append(SubtitleStream(
                    url=base_url + "&fmt=vtt",
                    language=lang,
                    format="vtt",
                    is_auto_generated=is_auto,
                ))
        return subs

    def _parse_video_details(self, player_response: dict) -> dict:
        vd = player_response.get("videoDetails", {})
        return {
            "id": vd.get("videoId", ""),
            "name": vd.get("title", ""),
            "description": vd.get("shortDescription", ""),
            "uploader": vd.get("author", ""),
            "uploader_id": vd.get("channelId", ""),
            "duration": int(vd.get("lengthSeconds", -1)),
            "view_count": int(vd.get("viewCount", -1)),
            "is_live": vd.get("isLive", False) or vd.get("isLiveContent", False),
            "keywords": vd.get("keywords", []),
            "thumbnails": _parse_thumbnails(
                _get_nested(vd, "thumbnail", "thumbnails", default=[])
            ),
        }

    def _parse_microformat(self, player_response: dict) -> dict:
        mf = _get_nested(player_response, "microformat", "playerMicroformatRenderer", default={})
        return {
            "upload_date": mf.get("uploadDate", mf.get("publishDate", "")),
            "category": mf.get("category", ""),
            "age_limit": 18 if mf.get("isFamilySafe") is False else 0,
        }

    def extract(self, url: str) -> StreamInfo:
        video_id = extract_video_id(url)

        # Fetch initial page for player JS URL
        _, page_player_resp, player_js_url = fetch_initial_data(
            self.downloader, video_id_to_url(video_id)
        )

        # Primary: ANDROID client (gives direct stream URLs)
        android_resp = self._android_client.player(video_id)
        self._check_playability(android_resp)

        # Secondary: WEB client (gives microformat, captions, better metadata)
        try:
            web_resp = self._web_client.player(video_id)
        except Exception:
            web_resp = android_resp

        # Parse video details (prefer android_resp which usually has full data)
        details = self._parse_video_details(android_resp)
        microformat = self._parse_microformat(web_resp)

        # Thumbnails — merge from both
        thumbs = details["thumbnails"]
        if not thumbs:
            thumbs = _parse_thumbnails(
                _get_nested(web_resp, "videoDetails", "thumbnail", "thumbnails", default=[])
            )

        # Uploader channel URL
        uploader_id = details.get("uploader_id", "")
        uploader_url = f"https://www.youtube.com/channel/{uploader_id}" if uploader_id else ""

        # Streams from ANDROID response
        streaming_data = android_resp.get("streamingData", {})
        video_streams, audio_streams, video_only_streams = self._parse_formats(
            streaming_data, player_js_url
        )

        # Subtitles from WEB response (has captions)
        captions = web_resp.get("captions", {})
        subtitle_streams = self._parse_subtitles(captions)

        hls_url = streaming_data.get("hlsManifestUrl", "")
        dash_url = streaming_data.get("dashManifestUrl", "")

        return StreamInfo(
            id=video_id,
            url=video_id_to_url(video_id),
            name=details["name"],
            description=details["description"],
            uploader=details["uploader"],
            uploader_url=uploader_url,
            thumbnails=thumbs,
            duration=details["duration"],
            view_count=details["view_count"],
            is_live=details["is_live"],
            tags=details["keywords"],
            upload_date=microformat.get("upload_date", ""),
            category=microformat.get("category", ""),
            age_limit=microformat.get("age_limit", 0),
            video_streams=video_streams,
            audio_streams=audio_streams,
            video_only_streams=video_only_streams,
            subtitle_streams=subtitle_streams,
            hls_url=hls_url,
            dash_mpd_url=dash_url,
        )
