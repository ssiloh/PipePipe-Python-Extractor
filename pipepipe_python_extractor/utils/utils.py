import re
from urllib.parse import urlparse


def is_url(text: str) -> bool:
    try:
        r = urlparse(text)
        return r.scheme in ("http", "https") and bool(r.netloc)
    except Exception:
        return False


def format_duration(seconds: int) -> str:
    if seconds < 0:
        return "Unknown"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_count(n: int) -> str:
    if n < 0:
        return "Unknown"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def clean_url(url: str) -> str:
    """Strip tracking params from YouTube URLs."""
    url = re.sub(r"[?&](utm_\w+|si|pp|feature)=[^&]*", "", url)
    return url
