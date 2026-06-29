# ADR-002 - Persistence, Idempotency, Exactly-Once Safeguards, and Audit

## Status

Accepted

## Context

CanTelcoX handles sensitive commands: registration, activation, invoice payment, and billing-related writes. Retries and double submissions must not create duplicate activations or payments. Compliance-sensitive actions must be traceable.

## Decision

Use MySQL persistence with isolated schemas per service. Use local transactions, unique constraints, and idempotency tables for activation and payment commands. Keep the audit log append-only in `svc-conformite-audit`; existing audit events must not be updated or deleted.

For Phase 1, practical exactly-once means deterministic writes enforced by database constraints and replayable idempotency responses. Kafka, event sourcing, distributed sagas, and full outbox processing are deferred unless explicitly needed later.

## Consequences

This gives demonstrable integrity guarantees without over-engineering. Duplicate activation/payment attempts can return the original result. The audit log supports CRTC/Law 25 traceability. The limitation is that cross-service consistency is handled through clear orchestration and compensating status updates rather than distributed transactions.

## Alternatives Considered

Distributed transactions were rejected as too heavy for Phase 1. Full event sourcing was rejected because the report only requires append-only audit, not event-sourced domain state.

