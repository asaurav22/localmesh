import logging
from data_plane.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


# one CircuitBreaker instance per upstream service name
_breakers: dict[str, CircuitBreaker] = {}

def get_breaker(service_name: str) -> CircuitBreaker:
    """
    Returns the CircuitBreaker for the given service.
    Creates one if it doesn't exist yet.
    """
    if service_name not in _breakers:
        _breakers[service_name] = CircuitBreaker(service_name)
        logger.info(f"[BREAKER REGISTRY] Created breaker for '{service_name}'")
    return _breakers[service_name]


def get_all_breakers() -> dict:
    """Returns state info for all breakers - used by /breakers endpoint."""
    return {name: cb.state_info for name, cb in _breakers.items()}
