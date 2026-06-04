from dataclasses import dataclass
from enum import Enum


class MediaFormat(Enum):
    # Video + Audio
    MPEG_4 = ("MPEG-4", "mp4", "video/mp4")
    WEBM = ("WebM", "webm", "video/webm")
    v3GPP = ("3GPP", "3gp", "video/3gpp")

    # Audio only
    M4A = ("m4a", "m4a", "audio/mp4")
    WEBMA = ("WebM Audio", "webm", "audio/webm")
    MP3 = ("MP3", "mp3", "audio/mpeg")
    OGG = ("OGG", "ogg", "audio/ogg")
    OPUS = ("Opus", "opus", "audio/opus")

    def __init__(self, name: str, suffix: str, mime_type: str):
        self._name = name
        self.suffix = suffix
        self.mime_type = mime_type

    @property
    def format_name(self) -> str:
        return self._name

    @staticmethod
    def from_mime_type(mime_type: str) -> "MediaFormat":
        for fmt in MediaFormat:
            if fmt.mime_type == mime_type:
                return fmt
        raise ValueError(f"Unknown mime type: {mime_type}")

    @staticmethod
    def from_suffix(suffix: str) -> "MediaFormat":
        for fmt in MediaFormat:
            if fmt.suffix == suffix:
                return fmt
        raise ValueError(f"Unknown suffix: {suffix}")
