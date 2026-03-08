import time

registry = {}

def register_service(service_name: str, host: str, port: int) -> dict:
    registry[service_name] = {
        "service_name": service_name,
        "host": host,
        "port": port,
        "registered_at": time.time()
    }
    return registry[service_name]

def lookup_service(service_name: str) -> dict | None:
    return registry.get(service_name)

def get_all_services() -> dict:
    return registry
