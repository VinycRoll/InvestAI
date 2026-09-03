import os
import statistics
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import requests

BASE_URL = "http://localhost:8000"


def _is_backend_available():
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


BACKEND_AVAILABLE = _is_backend_available()

pytestmark = pytest.mark.skipif(
    not BACKEND_AVAILABLE,
    reason="Backend não está rodando em http://localhost:8000",
)


def _health_request():
    start = time.monotonic()
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=10)
        elapsed = time.monotonic() - start
        return r.status_code, elapsed
    except Exception:
        elapsed = time.monotonic() - start
        return 0, elapsed


def test_concurrent_health_checks():
    num_requests = 50
    results = []

    barrier = threading.Barrier(num_requests)

    def worker():
        barrier.wait()
        status, elapsed = _health_request()
        results.append((status, elapsed))

    threads = [threading.Thread(target=worker) for _ in range(num_requests)]
    start_time = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = time.monotonic() - start_time

    assert len(results) == num_requests, f"Expected {num_requests} results, got {len(results)}"

    statuses = [s for s, _ in results]
    elapsed_times = [e for _, e in results]

    assert all(s == 200 for s in statuses), f"Not all requests returned 200: {statuses}"

    avg_time = statistics.mean(elapsed_times)
    max_time = max(elapsed_times)
    p95_time = sorted(elapsed_times)[int(len(elapsed_times) * 0.95)]

    assert avg_time < 2.0, f"Average response time {avg_time:.3f}s exceeds 2s threshold"

    print("\n--- Stress Test Results ---")
    print(f"Total requests:  {num_requests}")
    print("All returned 200: True")
    print(f"Avg response:    {avg_time:.3f}s")
    print(f"Max response:    {max_time:.3f}s")
    print(f"P95 response:    {p95_time:.3f}s")
    print(f"Total wall time: {total_time:.3f}s")


def test_concurrent_health_rps():
    num_requests = 50
    results = []
    barrier = threading.Barrier(num_requests)

    def worker():
        barrier.wait()
        status, elapsed = _health_request()
        results.append((status, elapsed))

    threads = [threading.Thread(target=worker) for _ in range(num_requests)]
    start_time = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = time.monotonic() - start_time

    assert total_time > 0
    rps = num_requests / total_time
    assert rps > 0

    print("\n--- Throughput ---")
    print(f"RPS: {rps:.1f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
