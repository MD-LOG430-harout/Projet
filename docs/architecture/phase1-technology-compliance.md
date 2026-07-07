# Phase 1 Technology Compliance

This checklist maps the current implementation to the official LOG430 Phase 1 technology expectations. It is intentionally limited to the retained use cases: UC-01, UC-02, UC-03, UC-05, and UC-06.

## Implemented

| Requirement | Evidence |
|---|---|
| DDD bounded contexts and service-based architecture | Six report services in `docker-compose.yml`; service boundary summary in `phase1-scope-and-grading.md` |
| REST `/v1` APIs through API Gateway | `infra/nginx/nginx.conf`, `docs/api/openapi.yaml`, Postman collection |
| Hexagonal layering / repositories | `domain`, `application`, `adapters/inbound`, `adapters/outbound` folders per service |
| MySQL persistence and init scripts | `infra/mysql/init/*.sql` |
| Seed/demo data | `infra/mysql/init/900-seed-demo-data.sql` and service repository demo invoice creation |
| Idempotency-Key for UC-03 and UC-05 | `svc-commandes-activations` activation/order repositories and tests |
| Exactly-once style payment safeguard for UC-06 | payment idempotency key plus unique successful payment per invoice |
| Append-only audit log | `svc-conformite-audit` and audit tests |
| NGINX gateway header propagation | `Authorization`, `TraceId`, `Idempotency-Key` in `infra/nginx/nginx.conf` |
| Docker Compose deployment | `docker-compose.yml`; one-command startup with `docker compose up -d --build` |
| Multi-stage service containers | Dockerfiles under `services/svc-*/Dockerfile` use a dependency `builder` stage and a slim `runtime` stage |
| `/health` and `/metrics` endpoints | Flask services and Prometheus config; Compose healthchecks cover the six services and API Gateway `/health` |
| Prometheus/Grafana 4 Golden Signals | `infra/prometheus/prometheus.yml`, `infra/grafana/dashboards/cantelcox-golden-signals.json`; latency, traffic, errors, and process-level CPU/RAM are instrumented |
| Structured logs with TraceId | shared logging middleware and Docker log evidence |
| Load testing | `tests/load/locustfile.py` targeting UC-02 setup plus UC-03 and UC-05 through the gateway. UC-04 and UC-08 are out of scope; UC-06 is covered by functional/payment tests, not the official Golden Signals Locust scenario. |
| Load balancing | NGINX `least_conn` upstreams with Docker DNS resolution; N=1..4 evidence is produced by scaling `svc-catalogue-offres`, `svc-commandes-activations`, and `svc-lignes-services` with Docker Compose |
| Redis catalogue cache | Redis-backed TTL cache for `GET /v1/offers` and `GET /v1/offers/{offerId}` with `X-Cache` evidence and `OFFER_CACHE_TTL_SECONDS` |
| Test pyramid and security checks | `docs/architecture/test-strategy-security.md`; service tests, adapter-boundary integration tests, gateway E2E smoke test, 87% measured coverage on `application` + `domain`, normalized-error checks |
| CI | `.github/workflows/phase1-ci.yml`; lint, contract validation, unit tests, Docker build, Compose startup, integration tests, E2E gateway test, and artifacts under a 10-minute job timeout |
| Scripted CD and rollback | `scripts/deploy-vm.sh` for VM deploy/status/logs/rollback; `docs/runbooks/deploiement-vm.md` documents operation and evidence |

## Documented But Limited

| Topic | Phase 1 position |
|---|---|
| Redis/cache | Implemented for catalogue read endpoints only. UC-04 usage cache is out of scope. Catalogue invalidation is TTL-based in Phase 1 because offers are seeded/read-only; explicit invalidation on catalogue writes is future work. |
| Saturation metrics | Partial support. Prometheus exposes process CPU/RAM for the Flask services; cAdvisor/node-exporter container or host saturation is documented as future observability hardening. |
| Load balancing N=1..4 | NGINX upstreams are scale-aware. Default compose uses one instance per service; scaling is documented with `docker compose up --scale ...` for evidence and kill-instance availability tests. |
| Direct vs Gateway comparison | Documented as an evidence exercise using one safe read endpoint. Official demo requests remain gateway-only. |
| free5GC | Used for UC-03 provisioning through the `svc-lignes-services` adapter when `HLR_ENABLED=true`; UDM or GUI evidence should be captured. |

## Explicitly Out of Scope

UC-04 usage consultation, UC-07 full fraud detection, UC-08 monthly billing cycle, delete/deprovision subscriber, saga orchestration, Outbox, Kafka, event sourcing, Jaeger tracing, distributed locks, and distributed database resilience are not implemented as Phase 1 features. They may appear only as future work or source-material references.
