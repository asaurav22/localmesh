import asyncio
import logging
import httpx
from control_plane.registry import registry, registry_lock

logger = logging.getLogger(__name__)

HEALTH_CHECK_INTERVAL = 10  # seconds between check
FAILURE_THRESHOLD = 3  # consecutive failures before eviction
HEALTH_CHECK_TIMEOUT = 3.0  # seconds before health check times out


async def health_loop() -> None:
    """
    Background task - polls /health on every registered service every
    HEALTH_CHECK_INTERVAL seconds. Marks services unhealthy after
    consecutive failures and evicts after FAILURE_THRESHOLD misses.

    This is active health monitoring - the Control plane reaches out
    rather than waiting for TTL expiry. Equivalent to k8s liveness probes.
    """
    logger.info(
        f"[HEALTH] Monitor started - "
        f"interval={HEALTH_CHECK_INTERVAL}s "
        f"threshold={FAILURE_THRESHOLD} failures"
    )
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            await _check_all_services(client)


async def _check_all_services(client: httpx.AsyncClient) -> None:
    with registry_lock:
        services_snapshot = list(registry.items())

    for name, entry in services_snapshot:
        url = f"http://{entry['host']}:{entry['port']}/health"
        try:
            response = await client.get(url, timeout=HEALTH_CHECK_TIMEOUT)
            if response.status_code == 200:
                _mark_healthy(name)
            else:
                logger.warning(
                    f"[HEALTH] '{name}' returned {response.status_code} "
                    f"from /health - treating as failure"
                )
                _record_failure(name)
        except httpx.ConnectError:
            logger.warning(f"[HEALTH] '{name}' - connection refused on /health")
            _record_failure(name)
        except httpx.TimeoutException:
            logger.warning(f"[HEALTH] '{name}' - /health timed out after {HEALTH_CHECK_INTERVAL}s")
            _record_failure(name)
        except Exception as e:
            logger.error(f"[HEALTH] '{name}' - unexpected error: {e}")
            _record_failure(name)


def _mark_healthy(name: str) -> None:
    with registry_lock:
        entry = registry.get(name)
        if not entry:
            return
        if entry.get("consecutive_failures", 0) > 0:
            logger.info(f"[HEALTH] '{name}' recovered - marking healthy")
        entry["consecutive_failures"] = 0
        entry["health"] = "healthy"


def _record_failure(name: str) -> None:
    with registry_lock:
        entry = registry.get(name)
        if not entry:
            return
        entry["consecutive_failure"] = entry.get("consecutive_failures", 0) + 1
        entry["health"] = "unhealthy"
        failures = entry["consecutive_failures"]

        logger.warning(
            f"[HEALTH] '{name}' failure "
            f"{failures}/{FAILURE_THRESHOLD}"
        )

        if failures >= FAILURE_THRESHOLD:
            del registry[name]
            logger.warning(
                f"[HEALTH] '{name}' evicted after "
                f"{FAILURE_THRESHOLD} consecutive failures"
            )
