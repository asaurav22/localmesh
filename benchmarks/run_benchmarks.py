import time
import os
from benchmarks.direct_test import run as run_direct
from benchmarks.proxy_test import run as run_proxy

def format_row(metric, direct, proxy):
    overhead = round(proxy - direct, 3)
    sign     = "+" if overhead > 0 else ""
    return f"| {metric:<10} | {direct:>10}ms | {proxy:>10}ms | {sign}{overhead:>10}ms |"

def print_table(direct: dict, proxy: dict):
    print("\n" + "=" * 58)
    print("  LocalMesh Benchmark Results — Direct vs Via Proxy")
    print("=" * 58)
    print(f"| {'Metric':<10} | {'Direct':>10}   | {'Via Proxy':>10}   | {'Overhead':>10}   |")
    print("|" + "-" * 12 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|")
    print(format_row("p50",        direct["p50"],        proxy["p50"]))
    print(format_row("p95",        direct["p95"],        proxy["p95"]))
    print(format_row("p99",        direct["p99"],        proxy["p99"]))
    print("|" + "-" * 12 + "|" + "-" * 13 + "|" + "-" * 13 + "|" + "-" * 13 + "|")
    print(f"| {'throughput':<10} | {direct['throughput']:>9}/s | {proxy['throughput']:>9}/s | {'n/a':>11} |")
    print(f"| {'total_time':<10} | {direct['total_time']:>10}s | {proxy['total_time']:>10}s | {'n/a':>11} |")
    print("=" * 58)

def save_results(direct: dict, proxy: dict):
    os.makedirs("benchmarks", exist_ok=True)
    content = f"""# Benchmark Results

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Configuration
- Requests: 1000 per test
- Warmup: 10 requests (not counted)
- Direct target: {direct['url']}
- Proxy target: {proxy['url']}

## Results

| Metric     |     Direct |  Via Proxy |   Overhead |
|------------|------------|------------|------------|
| p50        | {direct['p50']:>8}ms | {proxy['p50']:>8}ms | +{round(proxy['p50'] - direct['p50'], 3):>7}ms |
| p95        | {direct['p95']:>8}ms | {proxy['p95']:>8}ms | +{round(proxy['p95'] - direct['p95'], 3):>7}ms |
| p99        | {direct['p99']:>8}ms | {proxy['p99']:>8}ms | +{round(proxy['p99'] - direct['p99'], 3):>7}ms |
| throughput | {direct['throughput']:>7}/s | {proxy['throughput']:>7}/s |        n/a |
| total_time | {direct['total_time']:>9}s | {proxy['total_time']:>9}s |        n/a |

## Interpretation

The LocalMesh sidecar proxy adds approximately {round(proxy['p50'] - direct['p50'], 1)}ms
of overhead at the p50 (median) level. For a local development environment
this is completely acceptable — a developer sending tens of requests per
second will never notice a 2-5ms difference. The overhead exists because
every request passes through an additional FastAPI application, an httpx
async client, and the routing table lookup before reaching the upstream
service. In production this sidecar would be replaced by Envoy (written
in C++) which adds under 1ms of overhead and handles millions of requests
per second. The throughput reduction from {direct['throughput']}/s to
{proxy['throughput']}/s is irrelevant for local development but would be
unacceptable in production — further validating the production redesign
decision documented in docs/production-redesign.md.

## Raw Numbers
- Direct successful requests: {direct['requests']}
- Proxy successful requests:  {proxy['requests']}
"""
    with open("benchmarks/results.md", "w") as f:
        f.write(content)
    print("\n[BENCHMARK] Results saved to benchmarks/results.md")

if __name__ == "__main__":
    print("[BENCHMARK] Starting — make sure all services are running\n")
    print("[BENCHMARK] Running direct test...")
    direct = run_direct()

    print("\n[BENCHMARK] Running proxy test...")
    proxy = run_proxy()

    if direct and proxy:
        print_table(direct, proxy)
        save_results(direct, proxy)
    else:
        print("[BENCHMARK] One or both tests failed — check services are running")
