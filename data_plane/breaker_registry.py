import logging
from typing import Dict
from data_plane.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# module-level dict - one CircuitBreaker per upstream service
# this lives for the entire lifetime of the sidecar process
breakers: Dict[str, CircuitBreaker] = {}


def get_breaker(service_name: str) -> CircuitBreaker:
    """
    Returns existing CircuitBreaker for service_name.
    Creates a new one with default thresholds if not found.
    """
    if service_name not in breakers:
        breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            failure_threshold=5,
            window_size=10,
            open_duration=30.0,
            half_open_max=1
        )
        logger.info(f"[BREAKER REGISTRY] Created breaker for '{service_name}'")
    return breakers[service_name]


def get_all_breakers() -> dict:
    """Returns state_info for all breakers - used by GET /breakers."""
    return {name: cb.state_info for name, cb in breakers.items()}
