# CanTelcoX LOG430 Project

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
- `svc-commandes-activations` for UC-03 activation orchestration, UC-05 minimal order creation, and `Idempotency-Key`.
- `svc-usage-facturation` for UC-06 invoice lookup and invoice payment.
- NGINX API Gateway routing public `/v1` endpoints.
- MySQL schemas for customers, MFA challenges, audit events, catalogue offers, lines, activations, orders, invoices, and payments.
- Prometheus and Grafana basics for `/metrics`.
- OpenAPI draft at `docs/api/openapi.yaml`.

UC-04 usage consultation, UC-07 full fraud detection, and UC-08 monthly billing are intentionally excluded from this Phase 1 implementation. UC-05 is intentionally minimal: it creates and validates an accepted order, but does not implement full ecommerce/cart complexity and does not automatically trigger UC-03 activation.

## Phase 1 Scope and Grading Evidence

The official Phase 1 scope is tracked in [docs/architecture/phase1-scope-and-grading.md](docs/architecture/phase1-scope-and-grading.md). The implemented and planned use cases are:

| UC | Phase 1 decision |
|---|---|
| UC-01 Inscription & verification d'identite | Implemented in `svc-clients-identite` with audit events |
| UC-02 Authentification & MFA | Implemented in `svc-clients-identite` with MFA challenge verification |
| UC-03 Activation d'une ligne | Implemented as activation orchestration using `svc-commandes-activations`, `svc-catalogue-offres`, `svc-lignes-services`, the HLR/free5GC adapter port, and audit |
| UC-05 Prise de commande | Implemented minimally in `svc-commandes-activations` with customer/offer validation, order idempotency, and audit |
| UC-06 Paiement de facture | Implemented in `svc-usage-facturation` with simulated gateway and payment idempotency |

UC-03 is implemented as activation orchestration. UC-05 creates the accepted order as a separate Phase 1 command; full order-to-activation orchestration is documented as a future improvement. UC-04 is out of official report scope and is not exposed as an official API. UC-07 is limited to audit/risk placeholders required by implemented flows. UC-08 is out of scope for implementation.

The detailed UC-03 alternative-path coverage matrix is documented in [docs/architecture/uc03-activation-scope.md](docs/architecture/uc03-activation-scope.md).

Architecture decision records are available under [docs/adr](docs/adr):

- [ADR-001 - Service-Based Architecture and Bounded Contexts](docs/adr/ADR-001-service-style-and-boundaries.md)
- [ADR-002 - Persistence, Idempotency, Exactly-Once Safeguards, and Audit](docs/adr/ADR-002-persistence-idempotency-audit.md)
- [ADR-003 - API Versioning, Normalized Errors, and Observability](docs/adr/ADR-003-api-errors-versioning-observability.md)
- [ADR-004 - free5GC as the UC-03 Network Simulator Adapter Target](docs/adr/ADR-004-free5gc-network-adapter.md)

The free5GC simulator integration notes are in [docs/runbooks/free5gc-simulator.md](docs/runbooks/free5gc-simulator.md). The simulator is currently provided as `docs/free5gc-udm-min-max (2).zip` and should be reused for UC-03 instead of replacing it with a new fake HLR/HSS/UDM.

By default, Docker Compose runs UC-03 with `HLR_ENABLED=false`, which uses `MockHlrAdapter` through the same outbound port as the real network adapter. To call the provided free5GC WebConsole instead, extract/start the simulator, set `HLR_ENABLED=true`, and configure `FREE5GC_WEBUI_URL`.

## Setup Instructions

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

Start the first slice:

```bash
docker compose up --build
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

Create a minimal UC-05 order with idempotency:

```bash
curl -i -X POST http://localhost:8080/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session-token>" \
  -H "Idempotency-Key: demo-order-1" \
  -H "TraceId: demo-order-1" \
  -d "{\"customerId\":\"<customer-id>\",\"offerId\":\"forfait-5g-20gb\",\"quantity\":1,\"orderType\":\"MOBILE_PLAN_SUBSCRIPTION\"}"
```

Repeat the exact same order request with the same `Idempotency-Key`; it returns the same `orderId` and does not create another order. UC-05 intentionally stops at accepted order creation. UC-03 activation remains a separate command in this Phase 1 implementation.

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

- Swagger screenshot of UC-05 order creation returning `201`.
- Swagger screenshot of UC-06 payment returning `201`.
- Swagger or Postman screenshot showing UC-05 order idempotency replay returns the same `orderId`.
- Swagger or Postman screenshot showing payment idempotency replay returns the same `paymentId`.
- Database evidence from `usage_facturation.invoices` and `usage_facturation.payments`.
- Audit evidence for `ORDER_ACCEPTED`, `INVOICE_CONSULTED`, `PAYMENT_REQUESTED`, `PAYMENT_ACCEPTED`, and `INVOICE_PAID`.
- Docker logs showing the same `TraceId` across gateway and services.

### Run Tests

Install the service test dependencies locally, then run:

```bash
python -m pytest services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests
```

Include UC-05 and UC-06 tests:

```bash
python -m pytest services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

### Run Load Tests

After starting the stack, install Locust locally and run the first-slice load scenario:

```bash
locust -f tests/load/locustfile.py --host http://localhost:8080
```

Use the Locust report and Grafana dashboards as Phase 1 NFR evidence for latency, traffic, errors, and saturation. Later slices can add out-of-scope usage consultation if the report scope changes.

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
# Placeholder commands
npm test
# or
mvn test
# or
gradle test
```

Run integration tests when infrastructure is available:

```bash
docker compose up -d
# run integration test command here
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
