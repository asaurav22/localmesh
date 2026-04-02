import logging
from data_plane import routing_table as routing_store

logger = logging.getLogger(__name__)


class ServiceNotFoundError(Exception):
    """Raised when a logical service name has no entry in the routing table."""
    pass


class ServiceUnhealthyError(Exception):
    """Raised when a service exists in routing table but is marked unhealthy."""
    def __init__(self, service_name: str, health: str):
        self.service_name = service_name
        self.health = health
        super().__init__(f"Service '{service_name}' is unhealthy: {health}")


def parse_path(path: str) -> tuple[str, str]:
    """
    Split incoming path into service name and real path.
    '/payment-service/charge' -> ('payment-service', '/charge')
    '/order-service/orders/99' -> ('order-service', '/orders/99')
    """
    parts = path.strip("/").split("/", 1)
    service_name = parts[0]
    real_path = "/" + parts[1] if len(parts) > 1 else "/"
    return service_name, real_path


def resolve(service_name: str, real_path: str) -> str:
    """
    Resolve a logical service name to a real URL.

    Raises ServiceNotFoundError if service is not in routing table.
    Raises ServiceUnhealthyError if service is marked unhealthy.
    """
    entry = routing_store.get_route(service_name)
    if not entry:
        logger.warning(f"[RESOLVE] Service '{service_name}' not found in routing table.")
        raise ServiceNotFoundError(service_name)

    # health check - unhealthy service gets rejected before forwarding
    health = entry.get("health", "healthy")
    if health != "healthy":
        logger.warning(
            f"[RESOLVE] Service '{service_name}' is unhealthy "
            f"(health={health}) - rejecting request"
        )
        raise ServiceUnhealthyError(service_name, health)

    real_url = f"http://{entry['host']}:{entry['port']}{real_path}"
    logger.info(f"[RESOLVE] {service_name} -> {real_url}")
    return real_url
