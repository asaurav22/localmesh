import time
import asyncio
import logging

logger = logging.getLogger(__name__)

registry: dict = {}

def register_service(service_name: str, host: str, port: int, ttl: int) -> dict:
    now = time.time()
    registry[service_name] = {
        "service_name": service_name,
        "host": host,
        "port": port,
        "registered_at": now,
        "ttl": ttl,
        "expires_at": now + ttl
    }
    logger.info(f"[REGISTRY] Registered '{service_name}' at {host}:{port} with ttl={ttl}s")
    return registry[service_name]

def lookup_service(service_name: str) -> dict | None:
    entry = registry.get(service_name)
    if not entry:
        return None
    if time.time() > entry["expires_at"]:
        logger.warning(f"[REGISTRY] Lookup hit stale entry for '{service_name}' - evicting")
        del registry[service_name]
        return None
    return entry

def get_all_services() -> dict:
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
        now = time.time()
        expired = [k for k, v in registry.items() if v["expires_at"] < now]
        for k in expired:
            del registry[k]
            logger.info(f"[SWEEP] Evicted expired service '{k}'")
        if expired:
            logger.info(f"[SWEEP] Removed {len(expired)} service(s). Active: {len(registry)}")
