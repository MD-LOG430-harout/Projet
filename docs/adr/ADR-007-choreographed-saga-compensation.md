# ADR-007 - Saga choregraphiee et compensation

## Status

Accepted for Phase 2.

## Context

Order acceptance, payment authorization, line activation, and portability are
owned by different services and cannot share one database transaction.

## Decision

Use the event sequence `CommandePassee` to payment result, line result, and
command terminal result. Payment refusal cancels the order. Activation or
portability failure after authorization causes an idempotent refund/reversal,
resource release, and order cancellation. Compensations are forward state
transitions protected by aggregate guards, not reverse database transactions.

UC-06 invoice payment remains a separate synchronous capture flow. The order
saga uses a distinct authorization and refund model.

## Consequences

Nominal and compensated terminal states must be observable and testable.
Timeout detection may publish a fact but must not become a hidden orchestrator.

