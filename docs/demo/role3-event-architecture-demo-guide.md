# Role 3 Demo Guide - Architecture dynamique et evenementielle

Use this during the oral defense. Your job is to defend the runtime behavior:
end-to-end scenario, saga, Kafka, Outbox, idempotence, retries, and DLQ.

## My Role

I am responsible for:

- Section 6: Runtime View / Vue d'execution
- 4+1: process view
- end-to-end event flow
- saga versus distributed transaction
- choreography versus orchestration
- Outbox and consistency in Phase 2

My key idea:

> I defend what happens at runtime after a request is accepted.

## My 90-120 Second Script

> The main runtime scenario starts with `POST /v1/orders`. The order service
> validates synchronously what must be validated immediately, then creates the
> order as `EN_COURS`, creates `saga_state`, and writes `CommandePassee` to the
> Outbox in the same MySQL transaction. The API returns `202 Accepted`, because
> acceptance is not completion.
>
> After that, the Outbox poller publishes `CommandePassee` to Kafka using
> `aggregateId` as the key. Billing consumes it and publishes either
> `PaiementAutorise` or `PaiementRefuse`. If payment is authorized, lines consumes
> that fact, provisions the line through the mock HLR or HLR/HSS adapter, and
> publishes `LigneActivee` or `ActivationEchouee`. The order service consumes
> the result and publishes either `CommandeConfirmee` or `CommandeAnnulee`.
>
> This is a choreographed saga, not a distributed transaction and not a central
> orchestrator. Each participant owns its local transaction, records processed
> events for idempotence, applies business state guards, and commits the Kafka
> offset only after successful local processing.

## If Time Is Short

> Runtime starts with `POST /v1/orders`: the order is accepted as `EN_COURS`, and
> `CommandePassee` is written to the Outbox in the same local transaction. Kafka
> then carries the saga facts: payment authorization, line activation, and final
> confirmation or cancellation. It is choreography, not orchestration, and
> consistency comes from Outbox plus idempotent consumers.

## Nominal Flow

```text
CommandePassee
-> PaiementAutorise
-> LigneActivee
-> CommandeConfirmee
```

Demo command:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
```

## Compensation Flow

```text
CommandePassee
-> PaiementRefuse
-> CommandeAnnulee
```

Demo command:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
```

Alternative compensation:

```text
ActivationEchouee
-> CommandeAnnulee
-> PaiementRembourse
```

## What To Point At In Output

- `HTTP 202`
- `Location: /v1/orders/{orderId}/status`
- initial `EN_COURS`
- final `CONFIRMEE` or `ANNULEE`
- `outbox_events` rows with `PUBLISHED`
- `processed_events` counts
- audit chain with event names and same `saga_id`

## If The Teacher Asks

Question: Why saga instead of distributed transaction?

Answer:

> A telecom activation crosses multiple services and external systems. A
> distributed transaction would tightly couple those systems and is not realistic
> for Kafka and external HTTP APIs. The saga uses local transactions and
> compensating business facts.

Question: Why choreography instead of orchestration?

Answer:

> Choreography keeps each service responsible for its own reaction to facts.
> There is no central coordinator telling every participant what to do. The
> trade-off is that observability and event contracts become more important.

Question: How does Outbox help?

Answer:

> The business mutation and event record are committed in the same local MySQL
> transaction. If publication fails, the Outbox row remains retryable. This
> avoids losing the event after the business state changes.

Question: Is delivery exactly once?

Answer:

> No. The guarantee is at-least-once delivery with idempotent consumers. The
> duplicate window is expected, especially around Kafka acknowledgement and
> marking the Outbox row as published.

Question: When is the Kafka offset committed?

Answer:

> Only after the local transaction succeeds. That transaction includes
> `processed_events`, business state changes, and any new Outbox event.

## Anchor Sentence

> My role is to explain the runtime story: one local transaction accepts the
> command, then the saga advances through business facts published by Kafka.

## Live Evidence I Own (Annexe D.2)

| Claim | Command | What the room sees |
|---|---|---|
| End-to-end tracing | `-Step Acceptance`, then Jaeger | one trace, `POST /v1/orders` + `publish`/`consume` spans of the four services |
| Replay without double effect | `-Step Replay` | identical state before/after, `DUPLICATE` in `cantelcox_saga_transitions_total` |
| Retry then DLQ | `-Step Dlq` | record in `paiement-autorise.v1.dlq` with `attempts=3`, consumer still running |
| Broker lag | Grafana `CanTelcoX Event-Driven` | `cantelcox_consumer_lag` per topic |

Question: How does the trace survive the Outbox, since the relay publishes in
another thread?

Answer:

> The relay has no ambient span, so the envelope `traceId` is the anchor. The
> producer span is started under a context rebuilt from that `traceId`, the W3C
> context is injected into the Kafka `traceparent` header, and the consumer
> re-extracts it. That is what keeps REST, publish and consume in one trace.

Question: What proves the replay was actually received rather than never
delivered?

Answer:

> The `DUPLICATE` counter. `processed_events` reserves the `eventId` inside the
> same transaction as the business effect, so the second delivery raises a
> duplicate-key error that the handler normalises and reports.
