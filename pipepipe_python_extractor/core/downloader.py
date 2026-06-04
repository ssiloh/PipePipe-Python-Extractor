from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None  # type: ignore


def _require_requests():
    if not HAS_REQUESTS:
        raise ImportError(
            "The 'requests' package is required. Install it with:\n"
            "    pip install requests"
        )


class Downloader:
    """HTTP client that mimics browser/app requests."""

    DEFAULT_TIMEOUT = 15

    BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    ANDROID_HEADERS = {
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
        "X-YouTube-Client-Name": "3",
        "X-YouTube-Client-Version": "19.09.37",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, proxy: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        _require_requests()
        self.session = requests.Session()
        self.timeout = timeout
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get(self, url: str, headers: Optional[dict] = None, params: Optional[dict] = None):
        h = {**self.BROWSER_HEADERS, **(headers or {})}
        resp = self.session.get(url, headers=h, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def post(self, url: str, json: dict, headers: Optional[dict] = None):
        h = {**self.BROWSER_HEADERS, **(headers or {})}
        resp = self.session.post(url, json=json, headers=h, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def get_text(self, url: str, headers: Optional[dict] = None) -> str:
        return self.get(url, headers=headers).text

    def get_json(self, url: str, headers: Optional[dict] = None) -> dict:
        return self.get(url, headers=headers).json()

    def post_json(self, url: str, json: dict, headers: Optional[dict] = None) -> dict:
        return self.post(url, json=json, headers=headers).json()
