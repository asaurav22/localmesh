import time
import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

registry: dict = {}
registry_lock = threading.Lock()


def register_service(
    service_name: str,
    host: str,
    port: int,
    ttl: int,
    expected_version: int = 0
) -> dict:
    with registry_lock:
        now = time.time()
        existing = registry.get(service_name)

        # optimistic locking - reject if version mismatch
        if existing:
            if existing["version"] != expected_version:
                logger.warning(
                    f"[REGISTRY] Conflict on '{service_name}' - "
                    f"expected version {expected_version}, found {existing['version']}"
                )
                raise ConflictError(
                    f"Concurrent write detected for '{service_name}'. "
                    f"Current version is {existing['version']}, retry with correct version"
                )
            new_version = (existing["version"] + 1)
        else:
            if expected_version != 0:
                raise ConflictError(
                    f"Service '{service_name}' does not exist. "
                    f"Use expected_version=0 for first registration."
                )
            new_version = 0

        registry[service_name] = {
            "service_name": service_name,
            "host": host,
            "port": port,
            "registered_at": now,
            "ttl": ttl,
            "expires_at": now + ttl,
            "version": new_version
        }
        logger.info(
            f"[REGISTRY] Registered '{service_name}' at {host}:{port} "
            f"ttl={ttl}s version={new_version}"
        )
        return registry[service_name]


def lookup_service(service_name: str) -> dict | None:
    with registry_lock:
        entry = registry.get(service_name)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            logger.warning(f"[REGISTRY] Stale entry for '{service_name}' - evicting")
            del registry[service_name]
            return None
        return entry


def get_all_services() -> list[dict]:
    with registry_lock:
        now = time.time()
        result = []
        for entry in registry.values():
            result.append({
                **entry,
                "expires_in": round(entry["expires_at"] - now, 2)
            })
        return result


async def sweep_loop() -> None:
    """Background task - runs every 5s and evicts expired entries."""
    while True:
        await asyncio.sleep(5)
        with registry_lock:
            now = time.time()
            expired = [k for k, v in registry.items() if v["expires_at"] < now]
            for k in expired:
                del registry[k]
                logger.info(f"[SWEEP] Evicted expired service '{k}'")
            if expired:
                logger.info(f"[SWEEP] Removed {len(expired)} service(s). Active: {len(registry)}")


def get_dashboard_data() -> dict:
    with registry_lock:
        now = time.time()
        services = []

        for entry in registry.values():
            expires_in = round(entry["expires_at"] - now)
            status = "expiring_soon" if expires_in < 10 else "healthy"
            services.append({
                "name": entry["service_name"],
                "host": entry["host"],
                "port": entry["port"],
                "version": entry["version"],
                "expires_in_seconds": expires_in,
                "status": status
            })

        services.sort(key=lambda s: s["name"])

        healthy = sum(1 for s in services if s["status"] == "healthy")
        expiring_soon = sum(1 for s in services if s["status"] == "expiring_soon")

        return {
            "mesh_summary": {
                "total_services": len(services),
                "healthy": healthy,
                "expiring_soon": expiring_soon
            },
            "services": services
        }


class ConflictError(Exception):
    """Raised when an optimistic lock conflict is detected."""
    pass
