from urllib.parse import urlparse, parse_qs
from .exceptions import ParsingException


class LinkHandler:
    """Base class for URL parsing and ID extraction."""

    def accepts_url(self, url: str) -> bool:
        raise NotImplementedError

    def get_id(self, url: str) -> str:
        raise NotImplementedError

    def get_url(self, id_: str) -> str:
        raise NotImplementedError
