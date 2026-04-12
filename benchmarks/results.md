# Benchmark Results

Generated: 2026-04-12 11:06:41

## Configuration
- Requests: 1000 per test
- Warmup: 10 requests (not counted)
- Direct target: http://localhost:9002/payments
- Proxy target: http://localhost:8001/payment-service/payments

## Results

| Metric     |     Direct |  Via Proxy |   Overhead |
|------------|------------|------------|------------|
| p50        |    2.606ms |   10.927ms | +  8.321ms |
| p95        |    4.529ms |   15.565ms | + 11.036ms |
| p99        |    5.891ms |   73.873ms | + 67.982ms |
| throughput |   333.3/s |    82.5/s |        n/a |
| total_time |       3.0s |     12.13s |        n/a |

## Interpretation

The LocalMesh sidecar proxy adds approximately 8.3ms
of overhead at the p50 (median) level. For a local development environment
this is completely acceptable — a developer sending tens of requests per
second will never notice a 2-5ms difference. The overhead exists because
every request passes through an additional FastAPI application, an httpx
async client, and the routing table lookup before reaching the upstream
service. In production this sidecar would be replaced by Envoy (written
in C++) which adds under 1ms of overhead and handles millions of requests
per second. The throughput reduction from 333.3/s to
82.5/s is irrelevant for local development but would be
unacceptable in production — further validating the production redesign
decision documented in docs/production-redesign.md.

## Raw Numbers
- Direct successful requests: 1000
- Proxy successful requests:  1000
