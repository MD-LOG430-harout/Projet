# CanTelcoX Phase 1 Scope and Grading Alignment

This document aligns the repository with the official LOG430 Phase 1 statement and evaluation rubric. It complements the Word/PDF project report and keeps the implementation plan traceable to the grading criteria. The detailed technology checklist is maintained in [Phase 1 Technology Compliance](phase1-technology-compliance.md).

## Phase 1 Functional Scope

The Phase 1 implementation scope is limited to these Must use cases:

| UC | Scope | Owning services | Status |
|---|---|---|---|
| UC-01 Inscription & verification d'identite | Register a customer, perform simulated identity/risk decision, audit the registration | `svc-clients-identite`, `svc-conformite-audit` | Implemented first slice |
| UC-02 Authentification & MFA | Login, generate MFA challenge, verify OTP, audit login/MFA outcomes | `svc-clients-identite`, `svc-conformite-audit` | Implemented first slice |
| UC-03 Activation d'une ligne | Idempotent activation orchestration, customer validation, offer validation, line/SIM/MSISDN state, HLR/free5GC adapter boundary, audit | `svc-commandes-activations`, `svc-catalogue-offres`, `svc-lignes-services`, `svc-clients-identite`, `svc-conformite-audit` | Implemented with mock HLR by default; free5GC adapter available |
| UC-05 Prise de commande | Active offer consultation, `NEW_PLAN` order creation, eligibility checks, risk placeholder, simple compatibility validation, order idempotency, audit, simulated confirmation | `svc-commandes-activations`, `svc-catalogue-offres`, `svc-clients-identite`, `svc-conformite-audit` | Implemented as controlled Phase 1 slice; full change/option execution remains future work |
| UC-06 Paiement de facture | Idempotent invoice payment with simulated payment gateway, exactly-once safeguards for billing writes, audit | `svc-usage-facturation`, `svc-conformite-audit` | Implemented with payment idempotency |

The following use cases are intentionally not implemented as full Phase 1 features:

| UC | Decision |
|---|---|
| UC-04 Consultation usage / factures | Out of official report scope for this Phase 1 implementation. No official `/v1/usage` API is exposed. |
| UC-07 Detection de fraude | Not implemented as a full use case. Only minimal audit/risk placeholders are kept where required by UC-01, UC-02, UC-03, UC-05, or UC-06. |
| UC-08 Cycle de facturation mensuel | Not implemented. Billing work is limited to invoice lookup/payment paths required by UC-06. |

UC-03 alternative paths are not removed from the architecture documentation. Their Phase 1 coverage is classified in [UC-03 - Activation d'une ligne: Phase 1 Coverage](uc03-activation-scope.md).

## Service Boundaries

The six service names from the project report are fixed:

| Service | Bounded context | Phase 1 responsibility |
|---|---|---|
| `svc-clients-identite` | Clients & Identite | UC-01, UC-02, and customer validation for UC-03 |
| `svc-lignes-services` | Lignes & Services | UC-03 line, MSISDN, SIM/eSIM, and network provisioning state |
| `svc-commandes-activations` | Commandes & Activations | UC-03 activation orchestration, UC-05 controlled order creation/validation, and idempotency |
| `svc-catalogue-offres` | Catalogue & Offres | Active offer consultation for UC-05 and offer/forfait validation for UC-03 |
| `svc-usage-facturation` | Usage / Facturation | UC-06 invoice lookup and payments; official Phase 1 does not expose UC-04 usage consultation |
| `svc-conformite-audit` | Conformite & Audit | Append-only audit events across implemented use cases |

## Current Implementation Evidence

| Rubric area | Current evidence in repository | Remaining evidence needed |
|---|---|---|
| Business analysis & DDD | `docs/Gabarit_LOG430_Phase1_Architecture_v3_1.txt`, this scope file | Complete final report sections with implemented evidence paths |
| Architecture, decisions & REST API | `docs/api/openapi.yaml`, `docs/adr/*`, `infra/nginx/nginx.conf` | Validate Swagger/Postman evidence during final demo |
| Persistence & integrity | `infra/mysql/init/*.sql`, repository adapters under `services/*/adapters/outbound/persistence` | Record database screenshots/evidence for activation, invoices, and payments |
| Microservices & API Gateway | `docker-compose.yml`, NGINX gateway, six report services | Demonstrate all public API calls through gateway |
| Observability & load testing | `/metrics` support, Prometheus/Grafana config, `tests/load/locustfile.py` | Run and record load campaigns with screenshots/results |
| Load balancing & caching | NGINX foundation and service-level routing | Demonstrate N=1..4 service replicas for command/billing paths |
| Quality, tests & security | Service tests under `services/*/tests`, MFA, normalized errors, activation/payment idempotency tests | Add coverage evidence and final failure-path screenshots |
| CI/CD, documentation & demo | Docker Compose, README, architecture docs, `.github/workflows/phase1-ci.yml` | Capture the CI run and final demo evidence |

## Vertical Slice Order

1. First slice, already implemented:
   - NGINX API Gateway
   - `svc-clients-identite`
   - `svc-conformite-audit`
   - MySQL schemas for customers, MFA challenges, audit events
   - Prometheus/Grafana basics
   - OpenAPI draft
   - tests for registration, login/MFA, customer validation, append-only audit

2. UC-03 activation slice, implemented:
   - `svc-catalogue-offres`: minimal `GET /v1/offers/{offerId}` and seeded active offers
   - `svc-lignes-services`: line/MSISDN/SIM state and free5GC adapter
   - `svc-commandes-activations`: `POST /v1/activations` with required `Idempotency-Key`
   - audit events for activation request, provisioning result, activation success/failure

3. UC-06 facturation/payment slice, implemented:
   - `svc-usage-facturation`: invoice reads and payment command
   - `Idempotency-Key` for payments
   - exactly-once safeguards using unique constraints and transactions

4. UC-05 controlled order slice, implemented:
   - `GET /v1/offers` for active offer consultation
   - `POST /v1/orders` with required `Idempotency-Key`
   - validates customer eligibility, risk placeholder, active offer, and simple compatibility rules
   - creates an accepted `NEW_PLAN` order without automatically triggering activation
   - returns `orchestrationStatus=READY_FOR_ACTIVATION` and `confirmationStatus=SIMULATED_SENT`
   - audit events for requested, validated, risk checked, accepted, replayed, rejected, and simulated confirmation paths

5. NFR demonstration slice:
   - Locust scenarios for UC-02 setup plus UC-03 and UC-05 through the gateway. UC-04 and UC-08 are out of scope, and UC-06 is tested functionally rather than used as an official Golden Signals load path.
   - Gateway vs direct measurements
   - NGINX load balancing evidence with N=1..4 replicas where local resources allow
   - Redis cache evidence for catalogue reads (`GET /v1/offers`, `GET /v1/offers/{offerId}`)
   - Payment/order idempotency and database integrity evidence
   - Prometheus/Grafana screenshots for 4 Golden Signals

## NFR Evidence Plan

The official targets are:

| Metric | Target | Planned evidence |
|---|---|---|
| Latency | P95 <= 500 ms under nominal load | Locust HTML/CSV reports and Grafana latency panels |
| Throughput | >= 600 operations/s before saturation, or justified gap | Locust staged load results |
| Availability | 95% during failure demonstration | Kill one replicated service instance under load, record successful requests/errors |
| Errors | Controlled 4xx/5xx with normalized JSON | API tests and Grafana error-rate panels |
| Saturation | CPU/RAM/thread pressure visible | Current Grafana evidence covers process CPU/RAM; Docker stats, cAdvisor, or node-exporter can be added as supplemental host/container evidence |

If the local VM cannot reach a target, document the measured gap and the bottleneck instead of claiming success.
