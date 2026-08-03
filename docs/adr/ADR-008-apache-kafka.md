# ADR-008 - Apache Kafka

## Status

Accepted for Phase 2.

## Context

The lab requires durable asynchronous collaboration, partition ordering, replay,
consumer groups, and observable offsets on a single course VM.

## Decision

Use a single Apache Kafka broker in KRaft mode with replication factor 1. Use
one topic per internal event type, three partitions per topic, `aggregateId` as
the message key, one group per consuming service, manual offset commit after a
successful local transaction, and source-specific `<topic>.dlq` topics for
unrecoverable consumer failures.

## Consequences

Ordering exists only within a partition. Replication factor 1 is not fault
tolerant. Delivery is at-least-once; consumer idempotence supplies unique
business effects. Kafka transactions and exactly-once claims are excluded.

