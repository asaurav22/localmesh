# LocalMesh 🏍️

LocalMesh is a locally-running service mesh that eliminates hardcoded IP/port pairs in microservice development. It introduces a sidecar proxy and a central service registry so that services can discover and communicate with each other by logical name — the same way they would in a production environment using Kubernetes or Consul — making local development a faithful simulation of real distributed systems.

## Architecture — Week 1
```
┌─────────────────────────────────────────────┐
│           CONTROL PLANE  :7000              │
│                                             │
│  POST /registry/register                    │
│  GET  /registry/lookup/{name}               │
│  GET  /registry/services                    │
│  GET  /dashboard                            │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │         In-Memory Registry          │    │
│  │  {service_name: {host, port, ttl,   │    │
│  │   expires_at, version}}             │    │
│  │                                     │    │
│  │  threading.Lock() — thread safe     │    │
│  │  sweep_loop() — evicts every 5s     │    │
│  └─────────────────────────────────────┘    │
└──────────────┬──────────────────────────────┘
               │ auto-register on startup
       ┌───────┴────────┐
       ▼                ▼
  order-service    payment-service
     :9001              :9002
  GET /orders       GET /payments
  GET /health       GET /health
```

### Week 1 Components

| Component       | Port | Responsibility                            |
|-----------------|------|-------------------------------------------|
| Control Plane   | 7000 | Service registry, TTL eviction, dashboard |
| order-service   | 9001 | Demo microservice A                       |
| payment-service | 9002 | Demo microservice B                       |