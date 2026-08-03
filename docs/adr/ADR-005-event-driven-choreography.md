# ADR-005 - Architecture evenementielle et choregraphie

## Status

Accepted for Phase 2.

## Context

The Phase 1 services coordinate multi-service work through synchronous REST.
Phase 2 must reduce temporal coupling while preserving the six bounded contexts
and the existing public REST API conventions.

## Decision

Use Apache Kafka for internal domain facts and a choreographed saga without a
central orchestrator. The internal catalogue contains exactly eleven ASCII-only
event types. Each service reacts to events it owns locally and records any new
event through its Transactional Outbox. Customer validation, offer lookup,
authentication, status queries, and supplied synchronous external contracts
remain REST interactions.

## Consequences

The services become temporally decoupled, but the process is distributed across
event contracts and handlers. Correlation identifiers, OpenTelemetry traces,
state guards, metrics, and end-to-end tests are therefore mandatory.

