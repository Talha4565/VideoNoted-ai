import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

MAX_TRANSCRIPT_CHARS = int(os.getenv("MAX_TRANSCRIPT_CHARS", 25000))

# Shared API instance
_ytt = YouTubeTranscriptApi()


def fetch_transcript(video_id: str) -> dict:
    """
    Fetch and return the transcript for a given YouTube video ID.

    Returns:
        { "success": True, "text": "...", "timestamps": [...] }
        or
        { "success": False, "error": "human-readable message" }
    """
    try:
        transcript = _ytt.fetch(video_id)
        snippets = transcript.snippets

        timestamps = []
        texts = []
        for snippet in snippets:
            minutes = int(snippet.start) // 60
            seconds = int(snippet.start) % 60
            timestamps.append({
                "time": f"{minutes:02d}:{seconds:02d}",
                "text": snippet.text
            })
            texts.append(snippet.text)

        full_text = " ".join(texts)

        if len(full_text) > MAX_TRANSCRIPT_CHARS:
            full_text = full_text[:MAX_TRANSCRIPT_CHARS]

        return {
            "success": True,
            "text": full_text,
            "timestamps": timestamps[:30],
        }

    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "This video doesn't have a transcript. Try a video with subtitles enabled.",
        }
    except NoTranscriptFound:
        return {
            "success": False,
            "error": "No transcript found for this video. It may not have captions available.",
        }
    except VideoUnavailable:
        return {
            "success": False,
            "error": "This video is private or unavailable.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch transcript: {type(e).__name__}: {str(e)}",
        }
