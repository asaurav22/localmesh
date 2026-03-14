import logging

logger = logging.getLogger(__name__)

routing_table: dict = {}


def get_route(service_name: str) -> dict | None:
    return routing_table.get(service_name)


def get_all_routes() -> dict:
    return routing_table


def update_routes(new_routes: dict) -> None:
    routing_table.clear()
    routing_table.update(new_routes)
    logger.info(f"[ROUTING TABLE] Updated - {len(routing_table)} services registered")


def seed_route(service_name: str, host: str, port: int) -> None:
    """Manually add a route - used for local testing only"""
    routing_table[service_name] = {"host": host, "port": port}
    logger.info(f"[ROUTING TABLE] Seeded '{service_name}' -> {host}:{port}")
