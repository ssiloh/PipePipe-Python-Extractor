"""
YouTube InnerTube API client.
Supports WEB, ANDROID, TVHTML5 client contexts.
"""
import re
import json
from typing import Optional
from ...core.downloader import Downloader

INNERTUBE_BASE = "https://www.youtube.com/youtubei/v1"

# Client configurations that mirror NewPipeExtractor's client constants
CLIENTS = {
    "WEB": {
        "clientName": "WEB",
        "clientVersion": "2.20240101.00.00",
        "hl": "en",
        "gl": "US",
    },
    "ANDROID": {
        "clientName": "ANDROID",
        "clientVersion": "19.09.37",
        "androidSdkVersion": 30,
        "hl": "en",
        "gl": "US",
        "osName": "Android",
        "osVersion": "11",
        "platform": "MOBILE",
    },
    "ANDROID_TESTSUITE": {
        "clientName": "ANDROID_TESTSUITE",
        "clientVersion": "1.9",
        "androidSdkVersion": 30,
        "hl": "en",
        "gl": "US",
        "osName": "Android",
        "osVersion": "11",
        "platform": "MOBILE",
    },
    "TVHTML5": {
        "clientName": "TVHTML5",
        "clientVersion": "7.20240101.12.00",
        "hl": "en",
        "gl": "US",
    },
    "IOS": {
        "clientName": "IOS",
        "clientVersion": "19.09.3",
        "deviceModel": "iPhone16,2",
        "hl": "en",
        "gl": "US",
        "osName": "iPhone",
        "osVersion": "17.4.1.21E237",
        "platform": "MOBILE",
    },
}

ANDROID_API_KEY = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"
WEB_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"


class InnerTubeClient:
    def __init__(self, downloader: Downloader, client_name: str = "ANDROID"):
        self.downloader = downloader
        self.client_name = client_name
        self.client_ctx = CLIENTS[client_name]

    def _build_payload(self, extra: dict) -> dict:
        return {"context": {"client": self.client_ctx}, **extra}

    def _headers(self) -> dict:
        base = {
            "Content-Type": "application/json",
            "X-YouTube-Client-Name": self.client_ctx.get("clientName", ""),
            "X-YouTube-Client-Version": self.client_ctx.get("clientVersion", ""),
            "Origin": "https://www.youtube.com",
            "X-Origin": "https://www.youtube.com",
        }
        if self.client_name in ("ANDROID", "ANDROID_TESTSUITE"):
            base["User-Agent"] = (
                f"com.google.android.youtube/{self.client_ctx['clientVersion']} "
                "(Linux; U; Android 11) gzip"
            )
        elif self.client_name == "IOS":
            base["User-Agent"] = (
                f"com.google.ios.youtube/{self.client_ctx['clientVersion']} "
                "(iPhone16,2; U; CPU iPhone OS 17_4_1 like Mac OS X)"
            )
        return base

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{INNERTUBE_BASE}/{endpoint}?key={ANDROID_API_KEY}&prettyPrint=false"
        return self.downloader.post_json(url, json=payload, headers=self._headers())

    def player(self, video_id: str, sts: int = 0) -> dict:
        payload = self._build_payload({
            "videoId": video_id,
            "playbackContext": {
                "contentPlaybackContext": {
                    "html5Preference": "HTML5_PREF_WANTS",
                    "signatureTimestamp": sts,
                }
            },
            "racyCheckOk": True,
            "contentCheckOk": True,
        })
        return self._post("player", payload)

    def next(self, video_id: str) -> dict:
        payload = self._build_payload({"videoId": video_id})
        return self._post("next", payload)

    def search(self, query: str, continuation: str = "") -> dict:
        payload = self._build_payload({"query": query})
        if continuation:
            payload["continuation"] = continuation
        return self._post("search", payload)

    def browse(self, browse_id: str, continuation: str = "") -> dict:
        payload = self._build_payload({"browseId": browse_id})
        if continuation:
            payload["continuation"] = continuation
        return self._post("browse", payload)


def fetch_initial_data(downloader: Downloader, url: str) -> tuple[dict, dict, str]:
    """
    Fetch ytInitialData and ytInitialPlayerResponse from a YouTube page.
    Returns (initial_data, player_response, player_js_url).
    """
    html = downloader.get_text(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })

    initial_data = {}
    player_response = {}
    player_js_url = ""

    m = re.search(r"var ytInitialData\s*=\s*(\{.+?\});\s*</script>", html, re.DOTALL)
    if m:
        try:
            initial_data = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    m = re.search(r"var ytInitialPlayerResponse\s*=\s*(\{.+?\});\s*(?:var|</script>)", html, re.DOTALL)
    if m:
        try:
            player_response = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    m = re.search(r'"jsUrl"\s*:\s*"(/s/player/[^"]+/player_ias\.vflset/[^"]+/base\.js)"', html)
    if not m:
        m = re.search(r'src="(/s/player/[^"]+/base\.js)"', html)
    if m:
        player_js_url = "https://www.youtube.com" + m.group(1)

    return initial_data, player_response, player_js_url
