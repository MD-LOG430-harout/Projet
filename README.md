# CanTelcoX LOG430 Project

[![Phase 1 CI](https://github.com/MD-LOG430-harout/Projet/actions/workflows/phase1-ci.yml/badge.svg)](https://github.com/MD-LOG430-harout/Projet/actions/workflows/phase1-ci.yml)

## Project Overview

CanTelcoX is a LOG430 software architecture project for designing and implementing a modern Business Support System (BSS) for a fictional Canadian mobile operator.

The platform supports the commercial lifecycle of mobile subscribers and SMEs, including customer identity, mobile line management, product catalog, subscriptions, orders, activations, billing/payment interactions, notifications, compliance, and auditability.

The project emphasizes architecture as much as implementation. The target solution is a service-based / microservices-oriented system using Domain-Driven Design, REST APIs, an API Gateway, observability, containerized deployment, and documented architectural decisions.

## Architectural Goals

The system should be designed around the following goals:

- Clear service boundaries aligned with business capabilities.
- Domain-Driven Design and bounded contexts.
- Hexagonal architecture inside services.
- RESTful APIs documented with OpenAPI/Swagger.
- API Gateway for external access and routing.
- Idempotent command handling for orders and activations.
- Practical exactly-once safeguards for billing-sensitive writes.
- Append-only audit logging for compliance.
- Structured logs, metrics, traces, and dashboards.
- Load balancing, caching, and fault-tolerance demonstrations.
- Containerized multi-service deployment.
- CI/CD-ready development workflow.

## Domain Assumptions

The project is based on a Canadian telecom context. The system should account for:

- CRTC and Canadian telecom obligations.
- Law 25 and privacy expectations.
- PIPEDA/LPRPDE privacy principles.
- SIM swap and identity fraud risks.
- Mobile line lifecycle: subscription, activation, suspension, termination.
- Prepaid and postpaid customer models.
- Product catalog, offers, plans, options, and roaming.
- Usage mediation, rating, billing, and payment flows.
- Simulated integrations such as HLR/HSS/UDM, portability hub, and payment gateway.

## How to Use the Assistant / Coding Agent

Use the coding agent as an architecture-aware development assistant. It can help with:

- Understanding the repository.
- Designing service boundaries.
- Implementing endpoints and use cases.
- Refactoring toward hexagonal architecture.
- Writing tests.
- Reviewing code.
- Producing ADRs.
- Updating OpenAPI documentation.
- Improving observability.
- Preparing Docker/CI/CD support.
- Aligning implementation with LOG430 deliverables.

The agent should preserve existing conventions and make small, targeted changes. It should not redesign the entire system unless explicitly asked.


## Relationship to the Project Report

The project report is the architectural baseline for this repository. Development work should reflect the decisions, diagrams, use cases, quality goals, ADRs, and evidence already documented by the team.

When implementing or modifying the system, contributors and coding agents should:

- Keep service boundaries consistent with the report.
- Keep REST APIs and OpenAPI/Swagger documentation aligned with the report’s endpoint catalogue.
- Update ADRs when a structural decision changes.
- Update diagrams or explanatory text when code changes affect architecture.
- Keep NFR evidence current, including performance, availability, observability, caching, load balancing, and fault-tolerance results.
- Preserve team-specific decisions and rationale rather than replacing them with generic examples.
- Maintain traceability between requirements, implemented use cases, tests, and documentation.

The report should not be treated as a separate deliverable created only at the end. It should evolve with the code.

## Implemented Phase 1 Slices

This repository currently implements the Phase 1 functional slices selected from the project report:

- `svc-clients-identite` for UC-01 registration and UC-02 login/MFA.
- `svc-conformite-audit` for append-only audit events.
- `svc-catalogue-offres` for minimal UC-03 offer validation.
- `svc-lignes-services` for UC-03 line/MSISDN/SIM/eSIM state and HLR/free5GC adapter boundary.
- `svc-commandes-activations` for UC-03 activation orchestration, UC-05 controlled order creation/validation, and `Idempotency-Key`.
- `svc-usage-facturation` for UC-06 invoice lookup and invoice payment.
- NGINX API Gateway routing public `/v1` endpoints.
- MySQL schemas for customers, MFA challenges, audit events, catalogue offers, lines, activations, orders, invoices, and payments.
- Prometheus and Grafana basics for `/metrics`.
- OpenAPI draft at `docs/api/openapi.yaml`.

UC-04 usage consultation, UC-07 full fraud detection, and UC-08 monthly billing are intentionally excluded from this Phase 1 implementation. UC-05 is implemented for Phase 1 as a controlled order creation and validation workflow: offer consultation, customer validation, active offer validation, simple eligibility checks, risk placeholder, simple compatibility validation, order persistence, idempotency, auditability, and simulated confirmation. Full plan change execution, option lifecycle, notification retry, and advanced fraud/compatibility rules are documented as future work.

## Phase 1 Scope and Grading Evidence

The official Phase 1 scope is tracked in [docs/architecture/phase1-scope-and-grading.md](docs/architecture/phase1-scope-and-grading.md). The implemented and planned use cases are:

| UC | Phase 1 decision |
|---|---|
| UC-01 Inscription & verification d'identite | Implemented in `svc-clients-identite` with audit events |
| UC-02 Authentification & MFA | Implemented in `svc-clients-identite` with MFA challenge verification |
| UC-03 Activation d'une ligne | Implemented as activation orchestration using `svc-commandes-activations`, `svc-catalogue-offres`, `svc-lignes-services`, the HLR/free5GC adapter port, and audit |
| UC-05 Prise de commande | Implemented as Phase 1 order validation with offer consultation, eligibility/risk placeholders, accepted order persistence, idempotency, audit, and simulated confirmation |
| UC-06 Paiement de facture | Implemented in `svc-usage-facturation` with simulated gateway and payment idempotency |

UC-03 is implemented as activation orchestration. UC-05 creates the accepted order as a separate Phase 1 command with `orchestrationStatus=READY_FOR_ACTIVATION`; full automatic order-to-activation orchestration is documented as a future improvement. UC-04 is out of official report scope and is not exposed as an official API. UC-07 is limited to audit/risk placeholders required by implemented flows. UC-08 is out of scope for implementation.

The detailed UC-03 alternative-path coverage matrix is documented in [docs/architecture/uc03-activation-scope.md](docs/architecture/uc03-activation-scope.md).

The Phase 1 test pyramid, coverage evidence, E2E gateway scenario, normalized-error checks, and security/risk controls are documented in [docs/architecture/test-strategy-security.md](docs/architecture/test-strategy-security.md).

Architecture decision records are available under [docs/adr](docs/adr):

- [ADR-001 - Service-Based Architecture and Bounded Contexts](docs/adr/ADR-001-service-style-and-boundaries.md)
- [ADR-002 - Persistence, Idempotency, Exactly-Once Safeguards, and Audit](docs/adr/ADR-002-persistence-idempotency-audit.md)
- [ADR-003 - API Versioning, Normalized Errors, and Observability](docs/adr/ADR-003-api-errors-versioning-observability.md)
- [ADR-004 - free5GC as the UC-03 Network Simulator Adapter Target](docs/adr/ADR-004-free5gc-network-adapter.md)

The free5GC simulator integration notes are in [docs/runbooks/free5gc-simulator.md](docs/runbooks/free5gc-simulator.md). The simulator is currently provided as `docs/free5gc-udm-min-max (2).zip` and should be reused for UC-03 instead of replacing it with a new fake HLR/HSS/UDM.

By default, Docker Compose runs UC-03 with `HLR_ENABLED=false`, which uses `MockHlrAdapter` through the same outbound port as the real network adapter. To call the provided free5GC WebConsole instead, extract/start the simulator, set `HLR_ENABLED=true`, and configure `FREE5GC_WEBUI_URL`.

## Pinned Architecture Diagrams

The official PlantUML diagrams for the Phase 1 report are grouped under [docs/architecture/diagrams](docs/architecture/diagrams). They are pinned here so the architecture views, sequence flows, persistence models, and deployment topology are easy to find during correction.

### Context and DDD

- [Business context - CanTelcoX](docs/architecture/diagrams/context-business-cantelcox.puml)
- [System context - CanTelcoX](docs/architecture/diagrams/context-system-cantelcox.puml)
- [DDD context map - CanTelcoX](docs/architecture/diagrams/context-map-ddd-cantelcox.puml)

### Building Blocks

- [Level 1 whitebox - service decomposition](docs/architecture/diagrams/building-blocks-level1-cantelcox.puml)
- [Level 2 hexagonal structure - svc-commandes-activations](docs/architecture/diagrams/building-blocks-level2-commandes-activations.puml)

### Runtime Sequences

- [E2E Phase 1 gateway flow](docs/architecture/diagrams/sequence-e2e-phase1-gateway-flow.puml)
- [UC-01 registration](docs/architecture/diagrams/sequence-uc01-registration.puml)
- [UC-02 authentication and MFA](docs/architecture/diagrams/sequence-uc02-auth-mfa.puml)
- [UC-03 activation](docs/architecture/diagrams/sequence-uc03-activation.puml)
- [UC-05 order creation](docs/architecture/diagrams/sequence-uc05-order.puml)
- [UC-06 invoice payment](docs/architecture/diagrams/sequence-uc06-payment.puml)
- [Order idempotency replay](docs/architecture/diagrams/sequence-idempotency-order.puml)
- [Payment exactly-once safeguard](docs/architecture/diagrams/sequence-exactly-once-payment.puml)

### Deployment

- [Docker Compose deployment topology](docs/architecture/diagrams/deployment-docker-compose-cantelcox.puml)

### Persistence / Annexe B

- [Global persistence view](docs/architecture/diagrams/persistence-er-global.puml)
- [Clients & Identite persistence](docs/architecture/diagrams/persistence-er-clients-identite.puml)
- [Catalogue & Offres persistence](docs/architecture/diagrams/persistence-er-catalogue-offres.puml)
- [Commandes & Activations persistence](docs/architecture/diagrams/persistence-er-commandes-activations.puml)
- [Lignes & Services persistence](docs/architecture/diagrams/persistence-er-lignes-services.puml)
- [Usage / Facturation persistence](docs/architecture/diagrams/persistence-er-usage-facturation.puml)
- [Conformite & Audit persistence](docs/architecture/diagrams/persistence-er-conformite-audit.puml)

## Setup Instructions

## Lancement rapide

### Prerequisites

- Docker Desktop with Docker Compose
- Git
- Python 3.12+ only if running tests outside Docker
- Postman for the official demo flow

### Environment file

Create the local `.env` file from the tracked template:

```bash
cp .env.example .env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
```

The repository tracks `.env.example` only. The local `.env` file contains development/demo values for MySQL, Grafana, ports, free5GC adapter settings, and the simulated payment gateway. Do not commit real secrets.

If `.env` already exists from an older run, either copy `.env.example` again or add any missing variables from the template before starting Docker Compose.

### Start

From the repository root:

```bash
docker compose up --build
```

Expected result: MySQL becomes healthy, the bootstrap job creates the service schemas, all six Flask services become healthy, and NGINX exposes the API Gateway on `http://localhost:8080`.

### Stop and Reset

Stop without deleting data:

```bash
docker compose down
```

Reset volumes for a clean demo:

```bash
docker compose down -v
```

### Expected Ports

| Component | URL |
|---|---|
| API Gateway | `http://localhost:8080` |
| Swagger UI | `http://localhost:8081` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Locust, profile only | `http://localhost:8089` |
| MySQL | `localhost:3306` |

### Health Checks

Gateway health:

```bash
curl -i http://localhost:8080/health
```

Container/service health:

```bash
docker compose ps
```

Each Flask service exposes `/health`; Docker Compose healthchecks call those endpoints directly inside the Docker network.

### Swagger and Postman

Swagger UI:

```text
http://localhost:8081
```

Postman collection:

```text
docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json
```

Set or keep:

```text
baseUrl = http://localhost:8080
```

### Run Tests

```bash
python -m pytest -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

### Demo Data and Seeds

- Active offers are seeded by `infra/mysql/init/030-svc-catalogue-offres.sql`, including `forfait-5g-20gb`.
- UC-06 demo invoices are created deterministically by `svc-usage-facturation` when invoices are first requested for a valid customer.
- UC-03 uses `MockHlrAdapter` by default with `HLR_ENABLED=false`.
- To use the teacher free5GC simulator for UC-03, start the simulator separately, set `HLR_ENABLED=true` in `.env`, and keep `FREE5GC_WEBUI_URL=http://host.docker.internal:5050`.

### Démo officielle

Run every request through the API Gateway with `baseUrl=http://localhost:8080`:

1. UC-01 register
2. UC-02 login
3. UC-02 MFA verify
4. UC-05 consult offers
5. UC-05 create order
6. UC-05 idempotency replay
7. UC-03 activate line
8. UC-03 idempotency replay
9. UC-06 consult invoice, then pay invoice
10. UC-06 payment idempotency replay
11. Audit by `TraceId`

### Validation rapide pour le correcteur

```bash
cp .env.example .env
docker compose up -d --build
bash scripts/wait-compose-health.sh 300
curl -i http://localhost:8080/health
docker compose ps
python -m pytest -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Then import the Postman collection, keep `baseUrl=http://localhost:8080`, run the official demo flow, and verify logs by TraceId:

```bash
docker compose logs api-gateway svc-clients-identite svc-commandes-activations svc-lignes-services svc-usage-facturation svc-conformite-audit
```

### CI/CD et deploiement VM

La workflow GitHub Actions [Phase 1 CI](.github/workflows/phase1-ci.yml) est limitee a 10 minutes et execute la chaine attendue: lint rapide, validation OpenAPI/Postman/Compose, tests unitaires, build Docker, demarrage Compose, tests d'integration, test E2E gateway et artefacts JUnit/logs.

Deploiement VM en une commande depuis la racine du depot:

```bash
bash scripts/deploy-vm.sh deploy
```

Rollback simple vers le commit precedent enregistre:

```bash
bash scripts/deploy-vm.sh rollback
```

Runbook d'exploitation complet: [docs/runbooks/deploiement-vm.md](docs/runbooks/deploiement-vm.md).

### Prerequisites

- Git
- Docker and Docker Compose
- Python 3.12 if running tests outside Docker

### Local Installation

```bash
git clone <repository-url>
cd <repository-name>
```

Create a local environment file:

```bash
cp .env.example .env
```

### Run Locally

Start the full Phase 1 stack:

```bash
docker compose up --build
```

Stop the stack without deleting data:

```bash
docker compose down
```

Reset local database/dashboard volumes for a clean demo:

```bash
docker compose down -v
```

Default local URLs:

```text
API Gateway: http://localhost:8080
Swagger UI:  http://localhost:8081
Prometheus:  http://localhost:9090
Grafana:     http://localhost:3000  (admin/admin)
OpenAPI:     docs/api/openapi.yaml
Postman:     docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json
```

Open Swagger UI in a browser and use **Try it out** to call the API through the gateway. The OpenAPI server URL points to `http://localhost:8080`.

The Postman collection is also gateway-only and grouped by UC/service. Use it for demo evidence of UC-01 registration, UC-02 MFA, UC-05 order creation, UC-03 activation, UC-06 invoice/payment, idempotency replay, line lookup, and audit trace lookup.

Health checks:

```bash
curl -i http://localhost:8080/health
bash scripts/wait-compose-health.sh 300
docker compose ps
```

All official demo API requests must use the NGINX gateway at `http://localhost:8080`. Direct service calls are reserved only for the direct-vs-gateway comparison evidence.

### Implemented Endpoint Examples

Register a customer:

```bash
curl -i -X POST http://localhost:8080/v1/customers/register \
  -H "Content-Type: application/json" \
  -H "TraceId: demo-register-1" \
  -d "{\"email\":\"alice@example.test\",\"password\":\"Stronger123\",\"displayName\":\"Alice Test\",\"legalName\":\"Alice Test\",\"address\":{\"line1\":\"123 Rue Exemple\",\"city\":\"Montreal\",\"province\":\"QC\",\"postalCode\":\"H1A1A1\"},\"identityDocument\":{\"type\":\"driver_license\",\"number\":\"SIM-QC-123456\"},\"customerType\":\"individual\"}"
```

Login and create an MFA challenge:

```bash
curl -i -X POST http://localhost:8080/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "TraceId: demo-login-1" \
  -d "{\"email\":\"alice@example.test\",\"password\":\"Stronger123\"}"
```

For the Phase 1 demo, the login response includes a development-only `devOtp` value.
The login endpoint also accepts optional simulated `riskSignals` such as `newDevice`, `roaming`, `unusualLocation`, or `simSwapRecent`; high-risk contexts return `mfaStrength: STEP_UP`.

Verify MFA:

```bash
curl -i -X POST http://localhost:8080/v1/auth/mfa/verify \
  -H "Content-Type: application/json" \
  -H "TraceId: demo-mfa-1" \
  -d "{\"challengeId\":\"<challenge-id>\",\"otp\":\"123456\"}"
```

Validate a customer for the future activation slice:

```bash
curl -i http://localhost:8080/v1/customers/<customer-id> \
  -H "Authorization: Bearer <session-token>"
```

Append an audit event directly:

```bash
curl -i -X POST http://localhost:8080/v1/audit-events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session-token>" \
  -H "TraceId: demo-audit-1" \
  -d "{\"eventType\":\"DEMO_EVENT\",\"actorId\":\"demo\",\"customerId\":\"demo\",\"resourceId\":\"demo\",\"sourceService\":\"manual-demo\",\"result\":\"SUCCESS\",\"metadata\":{}}"
```

The `sessionToken` is returned by `POST /v1/auth/mfa/verify`. Protected endpoints use `Authorization: Bearer <session-token>` and the NGINX API Gateway validates the token through `svc-clients-identite`.

Retrieve an active offer for UC-03:

```bash
curl -i http://localhost:8080/v1/offers/forfait-5g-20gb \
  -H "Authorization: Bearer <session-token>"
```

Consult active offers for UC-05:

```bash
curl -i http://localhost:8080/v1/offers \
  -H "Authorization: Bearer <session-token>"
```

Create a Phase 1 UC-05 order with idempotency:

```bash
curl -i -X POST http://localhost:8080/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session-token>" \
  -H "Idempotency-Key: demo-order-1" \
  -H "TraceId: demo-order-1" \
  -d "{\"customerId\":\"<customer-id>\",\"offerId\":\"forfait-5g-20gb\",\"quantity\":1,\"orderType\":\"NEW_PLAN\"}"
```

Repeat the exact same order request with the same `Idempotency-Key`; it returns the same `orderId` and does not create another order. UC-05 returns `orchestrationStatus=READY_FOR_ACTIVATION` and `confirmationStatus=SIMULATED_SENT`. UC-03 activation remains a separate command in this Phase 1 implementation.

Activate a line with idempotency:

```bash
curl -i -X POST http://localhost:8080/v1/activations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session-token>" \
  -H "Idempotency-Key: demo-activation-1" \
  -H "TraceId: demo-activation-1" \
  -d "{\"customerId\":\"<customer-id>\",\"offerId\":\"forfait-5g-20gb\",\"simType\":\"ESIM\"}"
```

Repeat the exact same request with the same `Idempotency-Key`; it returns the same activation body and does not create another line.

For UC-03, `numberMode` controls the number choice. `NEW` assigns or accepts a non-portability MSISDN, while `PORT_IN` simulates keeping an existing number by requiring `msisdn` and recording `portabilityStatus=ACCEPTED`. This is a Phase 1 portability simulation, not a full portability hub with refusal or pending flows.

Retrieve the activated line:

```bash
curl -i http://localhost:8080/v1/lines/<line-id> \
  -H "Authorization: Bearer <session-token>"
```

List invoices for UC-06 and keep the returned `invoiceId`:

```bash
curl -i "http://localhost:8080/v1/invoices?customerId=<customer-id>" \
  -H "Authorization: Bearer <session-token>" \
  -H "TraceId: demo-invoices-1"
```

Pay an invoice for UC-06:

```bash
curl -i -X POST http://localhost:8080/v1/invoices/<invoice-id>/payments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session-token>" \
  -H "Idempotency-Key: demo-payment-1" \
  -H "TraceId: demo-payment-1" \
  -d "{\"customerId\":\"<customer-id>\",\"paymentMethod\":\"SIMULATED_CARD\",\"amount\":49.99,\"currency\":\"CAD\"}"
```

Repeat the exact same payment request with the same `Idempotency-Key`; it returns the same `paymentId` and does not create a duplicate payment.

Find audit events for a demo trace:

```bash
curl -i "http://localhost:8080/v1/audit-events?traceId=demo-payment-1" \
  -H "Authorization: Bearer <session-token>" \
  -H "TraceId: demo-payment-1"
```

UC-06 uses a simulated payment gateway adapter and database unique constraints for practical exactly-once behavior.

### Postman Demo Flow

Import [docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json](docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json), keep `baseUrl` as `http://localhost:8080`, and run the requests in this order:

Start each official demo run from **UC-01 register**. That request has a pre-request script that automatically generates a fresh `email`, `TraceId`, identity document number, activation/order/payment idempotency keys, port-in MSISDN, and clears stale IDs from previous runs.

1. UC-01 register
2. UC-02 login
3. UC-02 MFA verify
4. Protected customer lookup
5. UC-05 create order
6. UC-05 idempotency replay
7. UC-03 activation
8. UC-03 idempotency replay
9. UC-06 consult invoices
10. UC-06 pay invoice
11. UC-06 payment idempotency replay
12. Audit by `TraceId`

### Evidence Checklist

- Docker Compose screenshot showing gateway, six services, MySQL, Prometheus, Grafana, and Swagger UI running.
- Swagger/OpenAPI screenshot showing only the retained official UCs: UC-01, UC-02, UC-03, UC-05, UC-06.
- Postman flow screenshots through `baseUrl=http://localhost:8080`.
- Swagger screenshot of UC-05 order creation returning `201`.
- Swagger screenshot of UC-06 payment returning `201`.
- Swagger or Postman screenshot showing UC-05 order idempotency replay returns the same `orderId`.
- Swagger or Postman screenshot showing payment idempotency replay returns the same `paymentId`.
- UC-03 activation screenshot showing `status=ACTIVE`, `msisdn`, `lineId`, and `hlrStatus=PROVISIONED`.
- free5GC evidence using the GUI or UDM read endpoint, not only WebConsole `GET /api/subscriber` because that API may return `200` for missing subscribers.
- Database evidence from `usage_facturation.invoices` and `usage_facturation.payments`.
- Audit evidence for `ORDER_ACCEPTED`, `INVOICE_CONSULTED`, `PAYMENT_REQUESTED`, `PAYMENT_ACCEPTED`, and `INVOICE_PAID`.
- Docker logs showing the same `TraceId` across gateway and services.
- Pytest result screenshot showing all service tests passing.
- Locust HTML report screenshot and Grafana Golden Signals dashboard screenshot.
- GitHub Actions Phase 1 CI run screenshot.
- `bash scripts/deploy-vm.sh deploy` screenshot showing one-command deployment and healthy Compose status.
- `bash scripts/deploy-vm.sh rollback` screenshot or terminal output showing simple rollback.

### Run Tests

Install the service test dependencies locally, then run the official Phase 1 service test suite:

```bash
python -m pytest -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Latest measured result:

```text
50 passed
```

Measure the required coverage on the critical `application` + `domain` layers and write the HTML report. Infrastructure/adapters are intentionally excluded from this unit-coverage target and are validated by adapter, E2E, Docker, and Postman/Newman evidence.

```bash
python -m pytest --cov=services/svc-clients-identite/app/application --cov=services/svc-clients-identite/app/domain --cov=services/svc-catalogue-offres/app/application --cov=services/svc-catalogue-offres/app/domain --cov=services/svc-lignes-services/app/application --cov=services/svc-lignes-services/app/domain --cov=services/svc-commandes-activations/app/application --cov=services/svc-commandes-activations/app/domain --cov=services/svc-usage-facturation/app/application --cov=services/svc-usage-facturation/app/domain --cov=services/svc-conformite-audit/app/application --cov=services/svc-conformite-audit/app/domain --cov-report=term-missing --cov-report=html:docs/evidence/coverage/htmlcov -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Latest measured coverage:

```text
50 passed
TOTAL 87%
HTML report: docs/evidence/coverage/htmlcov/index.html
```

The test strategy and security/error evidence for LOG430 section 7.1/7.2 are summarized in [docs/architecture/test-strategy-security.md](docs/architecture/test-strategy-security.md).

Run the optional gateway E2E smoke test after Docker Compose is running:

```bash
python -m pytest -p no:cacheprovider tests/e2e/test_gateway_flow.py
```

The E2E test is skipped automatically if `http://localhost:8080/health` is unavailable. Full UC-07 fraud detection is out of scope; the tests cover the retained Phase 1 risk controls such as high-risk customer blocking for UC-03 and UC-05.

Run automated integration tests by adapter boundary after Docker Compose is running:

```bash
python -m pytest -p no:cacheprovider tests/integration
```

Latest measured result:

```text
7 passed, 1 skipped
```

These integration tests cover persistence boundaries for customers/MFA, catalogue offers, lines/MSISDN, orders/activations, invoices/payments, append-only audit, and the simulated payment gateway adapter. The free5GC live adapter test is skipped by default; run it with `FREE5GC_LIVE_TEST=1` when the simulator is available. Postman remains E2E evidence, not integration-test evidence.

### Run Load Tests

After starting the stack, run the official Phase 1 Golden Signals load scenario. Following the teacher's clarification for section 5.2, this scenario targets the implemented paths from the listed load-test UCs: UC-03 activation and UC-05 offer/order, with UC-02 login/MFA used for authenticated setup. UC-04 and UC-08 are out of scope in this project, and UC-06 remains a functional/payment test path rather than part of the official Locust Golden Signals scenario.

For load tests, Docker Compose uses `COMMAND_AUDIT_LEVEL=summary` by default. This keeps append-only audit evidence for accepted/rejected orders and completed/failed activations while reducing verbose intermediate audit events during high-concurrency campaigns. Set `COMMAND_AUDIT_LEVEL=detailed` for a verbose audit demo.

Recommended Docker Compose option, no local Locust install required:

```bash
docker compose --profile load-test up locust
```

Then open Locust at:

```text
http://localhost:8089
```

If Locust is installed locally, this is equivalent:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8080
```

Headless Docker example with an HTML report:

```bash
docker compose --profile load-test run --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-phase1-report.html
```

Local headless example with an HTML report:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8080 --headless -u 50 -r 5 -t 2m --html docs/evidence/load/locust-phase1-report.html
```

Use the Locust report and Grafana dashboards as Phase 1 NFR evidence for latency P95/P99, traffic/RPS, errors 4xx/5xx, and saturation. The current dashboard measures saturation at the Python process level with `process_cpu_seconds_total` and `process_resident_memory_bytes`; container/host-level saturation with cAdvisor or node-exporter is not included in the default stack. If the local machine does not reach the course target such as 600 ops/s, document the measured environment, user count, RPS, P95 latency, error rate, bottleneck, and limitation honestly.

Latest recorded local Locust evidence before the final UC-06 removal from the official Golden Signals scenario:

| Campaign | Requests | Failures | Average RPS | Median | P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| 20 users, ramp 2/s, 60s | 7800 | 0% | 131.7 | 7 ms | 160 ms | 210 ms |
| 50 users, ramp 5/s, 120s | 29804 | 0% | 249.2 | 12 ms | 450 ms | 740 ms |

For the 50-user run, the slower write endpoints remain UC-03 activation and UC-05 order creation. Their P95 values are approximately 840 ms and 810 ms respectively, while read-heavy endpoints such as customer lookup and offer consultation remain much faster. This validates stability under the tested load and meets the global P95 target in this local run, but it does not prove the `>= 600 ops/s` throughput target or formal `95%` availability under a kill-instance test.

For final submission screenshots, rerun Locust with the current `tests/load/locustfile.py`. The official request table should no longer contain UC-06 payment/invoice rows or the old protected customer lookup helper; it should contain UC-02 setup rows, UC-03 activation/replay, and UC-05 offer/order/replay.

### Load Balancing, Cache, and Direct-vs-Gateway Evidence

NGINX is the API Gateway and load balancer. The upstreams use Docker Compose DNS with `least_conn`, so replicated service containers can be exercised without changing API routes. The default compose file runs one container per service for reproducibility. For load-balancing evidence, run the same Locust campaign with N=1, 2, 3, and 4 replicas of the high-traffic services:

```powershell
# N = 1 baseline
docker compose up -d --scale svc-catalogue-offres=1 --scale svc-commandes-activations=1 --scale svc-lignes-services=1
docker compose restart api-gateway
docker compose --profile load-test run --no-deps --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-n1.html

# N = 2
docker compose up -d --scale svc-catalogue-offres=2 --scale svc-commandes-activations=2 --scale svc-lignes-services=2
docker compose restart api-gateway
docker compose --profile load-test run --no-deps --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-n2.html

# Repeat with N = 3 and N = 4 if the local machine has enough CPU/RAM.
```

For the fault-tolerance evidence, run a load test with at least N=2, stop one replicated container during the test, and capture the Locust failure rate plus Docker logs. The reported availability for this demonstration is `successful requests / total requests`. Do not add distributed locks, Kafka, saga orchestration, event sourcing, or distributed database resilience for Phase 1.

Redis caching is implemented for the catalogue read endpoints:

| Endpoint | Cache key | TTL | Invalidation |
|---|---|---:|---|
| `GET /v1/offers` | `catalogue:offers:active` | `OFFER_CACHE_TTL_SECONDS`, default 60s | TTL-based in Phase 1 because catalogue data is seeded/read-only |
| `GET /v1/offers/{offerId}` | `catalogue:offer:{offerId}` | `OFFER_CACHE_TTL_SECONDS`, default 60s | TTL-based; future catalogue admin writes must delete affected keys |

The response header `X-Cache` shows `MISS` on the first read and `HIT` on the cached read. UC-04 usage caching remains out of scope.

Quick cache evidence:

```powershell
$headers = @{ Authorization = "Bearer $env:ACCESS_TOKEN"; TraceId = "cache-demo" }
Invoke-WebRequest -Uri "http://localhost:8080/v1/offers" -Headers $headers | Select-Object -ExpandProperty Headers
Invoke-WebRequest -Uri "http://localhost:8080/v1/offers" -Headers $headers | Select-Object -ExpandProperty Headers
```

For direct-vs-gateway comparison, measure the same safe read endpoint once through the gateway and once directly inside the Docker network, then report the trade-off: gateway adds small routing/auth overhead but centralizes authentication, TraceId propagation, routing, and demo control.

## Development Workflow

1. Pick a small issue or feature.
2. Identify the affected service and bounded context.
3. Check whether the change affects API contracts, persistence, observability, or architecture documentation.
4. Implement the smallest coherent change.
5. Add or update tests.
6. Update OpenAPI/Swagger if an endpoint changes.
7. Update ADRs or architecture docs if the decision is architectural.
8. Run tests and linters.
9. Open a pull request with a clear summary and validation notes.

## Branching and Commits

Use clear branch names:

```text
feature/customer-registration
fix/idempotent-order-creation
docs/adr-api-versioning
refactor/billing-application-layer
```

Use focused commits:

```text
feat(order): add idempotency key handling
fix(billing): prevent duplicate invoice write
docs(adr): document REST gateway decision
test(identity): cover MFA failure path
```

## Testing Workflow

Testing should cover both service-level behavior and architecture-sensitive flows.

### Recommended Test Types

- Unit tests for domain logic.
- Application/use-case tests for commands and queries.
- Controller/API tests for validation and response formats.
- Persistence tests for idempotency and uniqueness constraints.
- Integration tests for service adapters.
- End-to-end tests for priority use cases.
- Load/performance tests for NFR demonstration.
- Failure tests for timeout, retry, duplicate command, and unavailable dependency scenarios.

### Running Tests

```bash
python -m pytest -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Run integration tests when infrastructure is available:

```bash
docker compose up -d
python -m pytest -p no:cacheprovider tests/integration
```

### Minimum Expectations

Before merging, verify:

- The changed service builds.
- Relevant tests pass.
- Main success and failure paths are covered.
- Duplicate command handling is tested when applicable.
- API documentation is updated for API changes.
- No secrets or personal data are logged.

## Code Review Expectations

Reviews should prioritize correctness, architecture, and maintainability.

Check for:

- Clear service ownership.
- Correct placement of logic in domain/application/adapters.
- Consistent API design.
- Validation and error handling.
- Idempotency for commands.
- Billing duplicate-write prevention.
- Append-only audit behavior.
- Observability and correlation IDs.
- Security and privacy risks.
- Tests for important behavior.
- Avoidance of unnecessary dependencies or broad rewrites.

Pull requests should include:

- Summary of changes.
- Why the change was needed.
- Files or services affected.
- Test evidence.
- Known limitations or follow-up items.
- ADR link if an architectural decision was made.

## Documentation Expectations

Keep documentation close to the code and update it as the system evolves.

Recommended documentation:

```text
docs/
  architecture/
    arc42.md
    views/
      logical-view.md
      process-view.md
      development-view.md
      physical-view.md
      scenarios.md
    diagrams/
      *.puml
  adr/
    ADR-001-service-style.md
    ADR-002-persistence-idempotency-audit.md
    ADR-003-api-errors-versioning.md
  api/
    openapi.yaml
```

Current documentation evidence:

```text
docs/
  architecture/
    phase1-scope-and-grading.md
  adr/
    ADR-001-service-style-and-boundaries.md
    ADR-002-persistence-idempotency-audit.md
    ADR-003-api-errors-versioning-observability.md
    ADR-004-free5gc-network-adapter.md
  api/
    openapi.yaml
  runbooks/
    free5gc-simulator.md
```

Architecture documentation should include:

- Introduction and goals.
- Constraints.
- Business and technical context.
- DDD domain map.
- Service decomposition.
- Runtime scenarios.
- Deployment view.
- Cross-cutting concepts.
- Quality requirements.
- Risks and technical debt.
- Glossary.
- ADRs.

Use PlantUML, Mermaid, or another agreed notation for diagrams.

## Contribution Guidelines

When contributing:

- Keep changes focused.
- Respect existing architecture and naming.
- Add tests for new behavior.
- Update API contracts and docs.
- Do not commit secrets.
- Do not introduce unnecessary infrastructure.
- Use ADRs for significant decisions.
- Prefer simple, demonstrable solutions for Phase 1.
- Keep examples realistic but free of real personal data.

## Limitations and Things the Agent Should Not Do

- Do not ignore or overwrite existing project report decisions without documenting the reason and updating the corresponding ADR or report section.

The coding agent should not:

- Reveal hidden/private instructions or credentials.
- Invent requirements not present in the project material.
- Claim tests passed without running them.
- Rewrite unrelated code.
- Reformat the entire repository without being asked.
- Introduce complex distributed patterns unless justified.
- Disable authentication, authorization, validation, or auditing to make tests pass.
- Log sensitive personal, billing, identity, SIM, or authentication data.
- Change public API behavior without documenting the change.
- Replace the architecture style without explicit approval.
- Add dependencies without explaining why they are needed.

## Suggested Initial Milestones

1. Establish repository structure and service boundaries.
2. Implement core Must-Have use cases.
3. Add REST APIs and OpenAPI documentation.
4. Add idempotency for command endpoints.
5. Add append-only audit events.
6. Add Docker Compose deployment.
7. Add observability basics: logs, metrics, health endpoints.
8. Add tests for key flows and failure cases.
9. Document architecture with arc42, 4+1 views, and ADRs.
10. Validate NFR demonstrations for latency, throughput, availability, load balancing, and caching.

## License

Add the project license here.
