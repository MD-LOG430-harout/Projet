# ADR-006 - Transactional Outbox

## Status

Accepted for Phase 2.

## Context

Writing business state and publishing directly to Kafka can lose an event or
publish an event for a transaction that later rolls back.

## Decision

Every producer writes its aggregate mutation and an `outbox_events` row in one
local MySQL transaction. An application poller claims bounded batches with
`FOR UPDATE SKIP LOCKED`, publishes with `aggregateId` as the Kafka key, and
marks a row `PUBLISHED` only after broker acknowledgement. Failed publication
increments the attempt count and schedules retry with bounded backoff.

## Consequences

Publication is at-least-once. A crash after Kafka acknowledgement and before the
MySQL update can republish the same immutable `eventId`; consumers must remove
the duplicate effect. Outbox is not exactly-once delivery and does not replace
Kafka replication.

