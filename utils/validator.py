import re


SUPPORTED_PATTERNS = [
    r"(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})",
    r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
    r"(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    r"(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    r"(?:youtube\.com/v/)([a-zA-Z0-9_-]{11})",
]


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from any valid YouTube URL format.
    Returns the 11-character video ID string, or None if not found.
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        return None

    for pattern in SUPPORTED_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def is_valid_youtube_url(url: str) -> bool:
    """Returns True if the URL is a valid YouTube video URL."""
    return extract_video_id(url) is not None
