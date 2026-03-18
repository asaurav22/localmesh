# LocalMesh 🏍️

LocalMesh is a locally-running service mesh that eliminates hardcoded IP/port pairs in microservice development. It introduces a sidecar proxy and a central service registry so that services can discover and communicate with each other by logical name — the same way they would in a production environment using Kubernetes or Consul — making local development a faithful simulation of real distributed systems.

> 🚧 Work in progress — built day by day over 30 days as a distributed systems learning project.

---

## The Problem

In local development, inter-service calls look like this:
```python
# Hardcoded. Fragile. Not how production works.
response = requests.get("http://127.0.0.1:9002/charge")
```

In production, a service mesh handles this transparently:
```python
# Location-agnostic. This is what LocalMesh enables locally.
response = requests.get("http://payment-service/charge")
```

The gap between these two causes bugs that only appear in staging,
onboarding friction, and zero resilience testing locally.

---

## How It Works

Every service registers itself with the Control Plane on startup using
a logical name. The sidecar proxy syncs this registry every 5 seconds.
When order-service needs to call payment-service, it sends the request
to the sidecar using the logical name. The sidecar resolves the name to
a real address and forwards the request transparently — preserving all
headers, the request body, and injecting a correlation ID for tracing.
If the destination is unreachable, the sidecar returns a clean 503
response instead of a raw OS-level connection error.

---

## Components

**Control Plane** runs on port 7000 and is responsible for the service
registry, TTL-based expiry, optimistic locking for concurrent writes,
and the live dashboard. It is the single source of truth for what
services are currently running and where.

**Sidecar Proxy** runs on port 8001 and is the data plane. It intercepts
all outbound service calls, resolves logical names to real addresses,
forwards requests with full header preservation, injects correlation IDs,
and syncs its routing table from the Control Plane every 5 seconds.

**order-service** runs on port 9001 and is a demo microservice that
auto-registers on startup, sends periodic heartbeats to stay alive in
the registry, and calls payment-service exclusively via the sidecar
using a logical name.

**payment-service** runs on port 9002 and is a demo microservice that
auto-registers on startup, sends periodic heartbeats, and acts as a
downstream destination for order-service calls.

---

## Project Structure
```
localmesh/
├── control_plane/
│   ├── main.py
│   ├── registry.py
│   ├── models.py
│   └── routers/
│       ├── registry_router.py
│       └── dashboard_router.py
├── data_plane/
│   ├── main.py
│   ├── routing_table.py
│   ├── resolver.py
│   ├── forwarder.py
│   └── syncer.py
├── services/
│   ├── order-service/
│   │   ├── main.py
│   │   └── models.py
│   └── payment-service/
│       ├── main.py
│       └── models.py
├── tests/
│   └── test_concurrent_register.py
├── docs/
│   ├── ADR-001.md
│   └── ADR-002.md
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Quick Start
```bash
# terminal 1 — start first
uvicorn control_plane.main:app --port 7000 --reload

# terminal 2
uvicorn data_plane.main:app --port 8001 --reload

# terminal 3
uvicorn services.order_service.main:app --port 9001 --reload

# terminal 4
uvicorn services.payment_service.main:app --port 9002 --reload
```

---

## Key Endpoints
```
Control Plane
  POST  localhost:7000/registry/register
  GET   localhost:7000/registry/lookup/{name}
  GET   localhost:7000/registry/services
  GET   localhost:7000/dashboard

Sidecar Proxy
  GET   localhost:8001/routing-table
  ANY   localhost:8001/{service-name}/{path}

order-service
  GET   localhost:9001/health
  GET   localhost:9001/orders
  GET   localhost:9001/orders/create

payment-service
  GET   localhost:9002/health
  GET   localhost:9002/payments
```

---

## Architecture Decision Records

- [ADR-001](./docs/ADR-001.md) — FastAPI vs Go for sidecar runtime
- [ADR-002](./docs/ADR-002.md) — In-memory registry vs persistent storage

--