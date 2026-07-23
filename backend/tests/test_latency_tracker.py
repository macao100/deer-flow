"""Tests for LatencyTracker."""
import threading
from deerflow.routing.latency_tracker import LatencyTracker


class TestLatencyTracker:
    def test_record_and_p50_single(self):
        lt = LatencyTracker(window_size=10)
        lt.record("m1", 100.0)
        assert lt.p50("m1") == 100.0

    def test_p50_multiple_values(self):
        lt = LatencyTracker(window_size=10)
        for v in [300, 100, 200]:
            lt.record("m1", float(v))
        assert lt.p50("m1") == 200.0

    def test_p95(self):
        lt = LatencyTracker(window_size=100)
        for i in range(100):
            lt.record("m1", float(i))
        p95 = lt.p95("m1")
        assert p95 is not None
        assert p95 >= 94.0  # 95th percentile of 0..99 approx 94+

    def test_window_overflow(self):
        lt = LatencyTracker(window_size=3)
        lt.record("m1", 100.0)
        lt.record("m1", 200.0)
        lt.record("m1", 300.0)
        lt.record("m1", 400.0)  # kicks out 100
        assert lt.p50("m1") == 300.0  # median of [200,300,400]

    def test_unknown_model_returns_none(self):
        lt = LatencyTracker()
        assert lt.p50("unknown") is None
        assert lt.p95("unknown") is None

    def test_stats_returns_dict(self):
        lt = LatencyTracker(window_size=5)
        for v in [100.0, 200.0, 300.0, 400.0, 500.0]:
            lt.record("m1", v)
        stats = lt.stats("m1")
        assert stats["p50"] == 300.0
        assert "p95" in stats
        assert stats["count"] == 5

    def test_all_stats(self):
        lt = LatencyTracker(window_size=5)
        lt.record("m1", 100.0)
        lt.record("m2", 200.0)
        all_s = lt.all_stats()
        assert "m1" in all_s
        assert "m2" in all_s

    def test_thread_safety(self):
        lt = LatencyTracker(window_size=1000)
        errors = []

        def record_many(model: str, base: float):
            try:
                for i in range(500):
                    lt.record(model, base + i)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=record_many, args=("m1", 0.0))
        t2 = threading.Thread(target=record_many, args=("m1", 500.0))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        stats = lt.stats("m1")
        assert stats["count"] == 1000
