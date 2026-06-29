# ADR-003 - API Versioning, Normalized Errors, and Observability

## Status

Accepted

## Context

Multiple services expose REST endpoints through NGINX. Clients, tests, logs, and dashboards need consistent behavior across services.

## Decision

Expose public APIs under `/v1`. Return normalized JSON errors with `code`, `message`, `details`, `traceId`, and `timestamp`. Propagate `TraceId`, `X-Request-Id`, and `Idempotency-Key` through the API Gateway. Each service exposes `/health` and `/metrics`.

## Consequences

This improves API documentation, testability, and debugging. The trade-off is that every new service must reuse the shared error, logging, and metrics conventions instead of returning framework-default errors.

## Alternatives Considered

Unversioned APIs and service-specific error formats were rejected because they make OpenAPI, client handling, and observability evidence weaker.

