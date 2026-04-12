import time
import statistics
import httpx

TARGET_URL = "http://localhost:9002/payments"
TOTAL_REQUEST = 1000


def run() -> dict:
    latencies = []

    print(f"[DIRECT] Sending {TOTAL_REQUEST} requests to {TARGET_URL}...")

    with httpx.Client(timeout=10.0) as client:
        # warmup - 10 requests not counted
        for _ in range(10):
            client.get(TARGET_URL)

        start_total = time.perf_counter()
        for i in range(TOTAL_REQUEST):
            start = time.perf_counter()
            response = client.get(TARGET_URL)
            elapsed = (time.perf_counter() - start) * 1000  # ms

            if response.status_code == 200:
                latencies.append(elapsed)
            else:
                print(f"[DIRECT] Unexpected status: {response.status_code}")

        total_seconds = time.perf_counter() - start_total

    if not latencies:
        print(f"[DIRECT] No successful requests recorded")
        return {}
    
    sorted_latencies = sorted(latencies)

    return {
        "label": "Direct",
        "url": TARGET_URL,
        "requests": len(latencies),
        "p50": round(statistics.median(latencies), 3),
        "p95": round(sorted_latencies[int(0.95 * len(sorted_latencies))], 3),
        "p99": round(sorted_latencies[int(0.99 * len(sorted_latencies))], 3),
        "throughput": round(TOTAL_REQUEST / total_seconds, 1),
        "total_time": round(total_seconds, 2)
    }

if __name__ == "__main__":
    result = run()
    print(f"\n[DIRECT] Results:")
    for k, v in result.items():
        print(f"  {k}: {v}")
