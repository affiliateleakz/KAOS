"""Small per-process sliding-window limiters for expensive provider calls.

Single-instance only: the counters live in this process, so a multi-worker
deployment needs a shared store (Redis) for a global limit. This is still the
authoritative per-member guard for one API process and is tested offline.
"""
import time
from collections import defaultdict, deque
from math import ceil


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, clock=time.monotonic):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = int(limit)
        self.window = float(window_seconds)
        self.clock = clock
        self._hits = defaultdict(deque)

    def check(self, key: str):
        """Record an attempt. Returns (allowed, retry_after_seconds)."""
        now = self.clock()
        bucket = self._hits[str(key)]
        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False, max(1, ceil(bucket[0] + self.window - now))
        bucket.append(now)
        if len(self._hits) > 4096:
            self._prune(now)
        return True, 0

    def _prune(self, now):
        stale = [key for key, bucket in self._hits.items()
                 if not bucket or bucket[-1] <= now - self.window]
        for key in stale:
            self._hits.pop(key, None)

    def reset(self, key: str = None):
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(str(key), None)
