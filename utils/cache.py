import time
import os
from collections import OrderedDict

CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", 100))
CACHE_TTL_SECONDS = 86400  # 24 hours


class VideoCache:
    """
    Simple in-memory LRU cache for processed video results.
    Keyed by video_id. Evicts oldest entries when full.
    Entries expire after 24 hours.

    This is critical for cost management:
    Same video requested twice = zero additional Gemini API calls.
    """

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: int = CACHE_TTL_SECONDS):
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()  # { video_id: (timestamp, result) }

    def get(self, video_id: str) -> dict | None:
        """Return cached result or None if not found / expired."""
        if video_id not in self._cache:
            return None

        timestamp, result = self._cache[video_id]

        # Check expiry
        if time.time() - timestamp > self.ttl:
            del self._cache[video_id]
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(video_id)
        return result

    def set(self, video_id: str, result: dict) -> None:
        """Store result in cache. Evict oldest if at capacity."""
        if video_id in self._cache:
            self._cache.move_to_end(video_id)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)  # remove oldest

        self._cache[video_id] = (time.time(), result)

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


# Global cache instance (shared across requests in same process)
video_cache = VideoCache()
