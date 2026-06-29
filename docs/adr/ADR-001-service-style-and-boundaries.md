# ADR-001 - Service-Based Architecture and Bounded Contexts

## Status

Accepted

## Context

CanTelcoX must demonstrate a distributed BSS architecture for a telecom domain while remaining feasible for LOG430 Phase 1. The official scope requires DDD, clear bounded contexts, a REST API Gateway, containerized deployment, observability, and traceable architectural decisions.

## Decision

Use a service-based / microservices-oriented architecture with six bounded-context services:

- `svc-clients-identite`
- `svc-lignes-services`
- `svc-commandes-activations`
- `svc-catalogue-offres`
- `svc-usage-facturation`
- `svc-conformite-audit`

Each service follows a hexagonal structure where controllers call application use cases, use cases coordinate domain behavior, and adapters handle persistence or external HTTP calls.

## Consequences

The design maps directly to the DDD domains in the report and makes grading evidence easier to trace by service and use case. The trade-off is additional operational complexity: service-to-service calls, Docker Compose wiring, health checks, metrics, and integration tests are required.

## Alternatives Considered

A modular monolith would be simpler to implement but would not demonstrate the microservices/API Gateway/deployment goals of Phase 1 as clearly.

