"""Thread-safe sliding-window latency tracker."""
from __future__ import annotations

import statistics
import threading
from collections import deque


class LatencyTracker:
    """Thread-safe per-model latency tracking with sliding window.

    Records call latency per model and computes p50/p95 percentiles
    for use by routing strategies.
    """

    def __init__(self, window_size: int = 50) -> None:
        self._window_size = max(1, window_size)
        self._buffers: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def record(self, model_name: str, latency_ms: float) -> None:
        """Record a latency measurement for *model_name*."""
        if latency_ms < 0:
            return
        with self._lock:
            buf = self._buffers.get(model_name)
            if buf is None:
                buf = deque(maxlen=self._window_size)
                self._buffers[model_name] = buf
            buf.append(latency_ms)

    def p50(self, model_name: str) -> float | None:
        """Median latency for *model_name*, or None if no data."""
        buf = self._buffers.get(model_name)
        if not buf:
            return None
        return statistics.median(buf)

    def p95(self, model_name: str) -> float | None:
        """95th percentile latency for *model_name*, or None if no data."""
        buf = self._buffers.get(model_name)
        if not buf:
            return None
        sorted_values = sorted(buf)
        n = len(sorted_values)
        if n == 0:
            return None
        idx = int(n * 0.95)
        # Clamp: at least index 0, at most n-1
        idx = max(0, min(idx, n - 1))
        return sorted_values[idx]

    def stats(self, model_name: str) -> dict[str, float]:
        """Per-model statistics: p50, p95, count, min, max."""
        buf = self._buffers.get(model_name)
        if not buf:
            return {"p50": 0, "p95": 0, "count": 0, "min": 0, "max": 0}
        return {
            "p50": self.p50(model_name) or 0,
            "p95": self.p95(model_name) or 0,
            "count": len(buf),
            "min": min(buf),
            "max": max(buf),
        }

    def all_stats(self) -> dict[str, dict[str, float]]:
        """Stats for all tracked models."""
        with self._lock:
            return {name: self.stats(name) for name in self._buffers}
