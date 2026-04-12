import time
import logging
from collections import deque
from typing import Dict

logger = logging.getLogger(__name__)

class RouteMetrics:
    """
    Tracks per-upstream-service request metrics using a rolling
    window of the last 100 requests. Lightweight - no external
    dependencies, lives in memory for the sidecar process lifetime.
    """
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.total = 0
        self.errors = 0
        self.created_at = time.time()
        self.latencies: deque[float] = deque(maxlen=100)  # last 100 requests

    def record(self, success: bool, latency_ms: float) -> None:
        self.total += 1
        if not success:
            self.errors += 1
        self.latencies.append(latency_ms)
        logger.debug(
            f"[METRICS:{self.service_name}] "
            f"{'OK' if success else 'ERR'} "
            f"{round(latency_ms, 2)}ms | "
            f"total={self.total} errors={self.errors}"
        )

    @property
    def error_rate(self) -> float:
        return round(self.errors / self.total, 4) if self.total else 0.0
    
    @property
    def p50(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        return round(s[len(s) // 2], 3)
    
    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        return round(s[int(0.99 * len(s))], 3)
    
    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        return round(s[int(0.95 * len(s))], 3)
    
    def to_dict(self) -> dict:
        return {
            "service": self.service_name,
            "total": self.total,
            "errors": self.errors,
            "error_rate": self.error_rate,
            "p50_ms": self.p50,
            "p95_ms": self.p95,
            "p99_ms": self.p99,
            "window_size": len(self.latencies)
        }
    

# module-level registry - one RouteMetrics per upstream service
route_metrics: Dict[str, RouteMetrics] = {}


def get_metrics(service_name: str) -> RouteMetrics:
    """Returns existing RouteMetrics or creates one for this service."""
    if service_name not in route_metrics:
        route_metrics[service_name] = RouteMetrics(service_name)
        logger.info(f"[METRICS] Created metrics tracker for '{service_name}'")
    return route_metrics[service_name]


def get_all_metrics() -> dict:
    """Returns metrics summary for all tracked services."""
    return {name: m.to_dict() for name, m in route_metrics.items()}
