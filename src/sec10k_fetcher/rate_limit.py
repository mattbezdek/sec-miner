from __future__ import annotations

import random
import threading
import time


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second
        self._last_called = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_called
            jitter = random.uniform(0.0, 0.05)
            remaining = self._min_interval - elapsed + jitter
            if remaining > 0:
                time.sleep(remaining)
            self._last_called = time.monotonic()
