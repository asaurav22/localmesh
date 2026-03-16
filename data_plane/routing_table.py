import asyncio
import logging

logger = logging.getLogger(__name__)

routing_table: dict = {}
routing_table_lock = asyncio.Lock()


def get_route(service_name: str) -> dict | None:
    return routing_table.get(service_name)


def get_all_routes() -> dict:
    return dict(routing_table)


async def update_routes(new_routes: dict) -> None:
    async with routing_table_lock:
        routing_table.clear()
        routing_table.update(new_routes)
        logger.info(f"[ROUTING TABLE] Updated - {len(routing_table)} services registered")


def seed_route(service_name: str, host: str, port: int) -> None:
    """Manually add a route - used for local testing only"""
    routing_table[service_name] = {"host": host, "port": port}
    logger.info(f"[ROUTING TABLE] Seeded '{service_name}' -> {host}:{port}")
