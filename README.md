# LocalMesh 🏍️

LocalMesh is a locally-running service mesh built from scratch to solve
a real problem every microservice developer faces — hardcoded ports,
fragile inter-service calls, and zero resilience testing in local
development.

In production, services talk to each other by logical name through a
mesh that handles discovery, routing, and failure automatically. Locally,
developers hardcode IP addresses and ports directly in code and hope
nothing breaks. LocalMesh closes that gap.

---

## What It Does

When order-service needs to call payment-service, instead of this:

```python
# fragile — breaks if port changes, crashes silently, untestable
response = requests.get("http://127.0.0.1:9002/charge")
```

It does this:

```python
# location-agnostic — exactly how production works
response = requests.get("http://localhost:8001/payment-service/charge")
```

The sidecar proxy intercepts the call, resolves the logical name
payment-service to its real address, and forwards the request
transparently. If payment-service is down, the circuit breaker trips
and returns a clean 503. If it recovers, traffic resumes automatically.
No code changes. No manual intervention.

---

## How It Works

**Service Registration** — Every service registers itself with the
Control Plane on startup using its logical name, host, and port. It
sends a heartbeat every 20 seconds to renew its TTL and stay alive in
the registry. The Control Plane polls each service's /health endpoint
every 10 seconds independently. A service that misses 3 consecutive
health checks is evicted automatically.

**Traffic Routing** — The sidecar proxy syncs the registry every 5
seconds. When a request arrives for /payment-service/charge, the sidecar
splits the path, looks up payment-service in its local routing table,
constructs the real URL, and forwards the request with full header
preservation. Authorization tokens, content-type, cookies, and
custom headers all pass through unchanged.

**Circuit Breaking** — Each upstream service gets its own circuit
breaker inside the sidecar. It tracks the last 10 requests in a sliding
window. When 5 consecutive failures occur, the breaker trips to OPEN and
immediately rejects all further requests with 503 — no upstream attempts.
After 30 seconds it enters HALF_OPEN and allows one probe request. If
the probe succeeds, traffic resumes. If it fails, the breaker resets.

**Distributed Tracing** — The sidecar injects an X-Correlation-ID
header on every request that doesn't already have one. This ID flows
through every service in the call chain. Searching logs for one UUID
shows the complete journey of a request across all services.

**Observability** — The sidecar tracks per-service metrics in a rolling
window of the last 100 requests — total calls, error count, error rate,
p50, p95, and p99 latency. The Control Plane serves a live HTML
dashboard that aggregates registry state, sidecar metrics, and circuit
breaker states in one view with auto-refresh every 5 seconds.

---

## Components

**Control Plane** (port 7000) is the brain. It runs the service
registry with TTL-based expiry, optimistic locking for concurrent
registrations, active health monitoring, and the live dashboard.

**Sidecar Proxy** (port 8001) is the data plane. It handles traffic
routing, health-aware request rejection, circuit breaking, metrics
collection, and correlation ID injection.

**order-service** (port 9001) and **payment-service** (port 9002) are
demo microservices that auto-register on startup and demonstrate the
full mesh in action.

---

## Running Locally

```bash
# install dependencies
pip install -r requirements.txt

# terminal 1 — start first
uvicorn control_plane.main:app --port 7000 --reload

# terminal 2 — no --reload
uvicorn data_plane.main:app --port 8001

# terminal 3
uvicorn services.order_service.main:app --port 9001 --reload

# terminal 4
uvicorn services.payment_service.main:app --port 9002 --reload
```

Open the live dashboard at `http://localhost:7000/dashboard/ui`

---

## Useful Endpoints

```
# see all registered services
GET localhost:7000/registry/services

# live dashboard
GET localhost:7000/dashboard/ui

# sidecar routing table
GET localhost:8001/routing-table

# circuit breaker states
GET localhost:8001/breakers

# per-route latency metrics
GET localhost:8001/metrics

# route traffic through the mesh
GET localhost:8001/{service-name}/{path}

# trigger a full chain call
GET localhost:9001/orders/create
```

---

## Testing Resilience

```bash
# send traffic through the mesh
curl http://localhost:8001/payment-service/payments

# kill payment-service and watch the circuit breaker trip
# send 5 requests — breaker trips to OPEN after threshold
curl http://localhost:8001/payment-service/payments

# check breaker state
curl http://localhost:8001/breakers

# restart payment-service — wait 30s — breaker self-heals
curl http://localhost:8001/payment-service/payments
```

---

## What This Project Covers

Building LocalMesh from scratch covers service discovery, dynamic
address translation, reverse proxy mechanics, header forwarding,
eventual consistency, optimistic locking, circuit breaker state
machines, sliding window algorithms, active health monitoring,
distributed tracing primitives, per-route observability, and chaos
engineering — all implemented without any external mesh infrastructure.

Every component maps directly to a production equivalent. The Control
Plane is what Consul or etcd does. The sidecar is what Envoy does. The
circuit breaker is what Hystrix or Resilience4j does. The health monitor
is what Kubernetes liveness probes do. The difference is LocalMesh does
all of it in plain Python so every line of it is readable and learnable.
