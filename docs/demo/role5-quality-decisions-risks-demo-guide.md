# Role 5 Demo Guide - Qualite, decisions et risques

Use this during the oral defense. Your job is to defend cross-cutting concepts,
ADRs, quality requirements, risks, and honest validation evidence.

## My Role

I am responsible for:

- Section 8: Cross-cutting concepts
- Section 9: ADRs
- Section 10: Quality requirements
- Section 11: Risks and technical debt
- most structuring decision, trade-offs, measured results, and mitigations

My key idea:

> I defend what architectural decisions were made, what quality attributes they
> improve, what they cost, and what evidence we actually have.

## My 60-90 Second Script

> The most structuring Phase 2 decision is the move to event-driven collaboration
> with Kafka, Transactional Outbox, choreographed sagas, and idempotent
> consumers. This improves resilience, traceability, and decoupling for
> long-running telecom workflows.
>
> The main trade-off is complexity. Compared to a synchronous REST chain, we now
> need Kafka topics, Outbox pollers, consumer groups, retries, DLQs, trace
> propagation, metrics, and stronger operational discipline.
>
> Our validation evidence is mixed and we state it honestly. The final verified
> test suite had 97 passed, 0 failed, and 12 skipped. The nominal saga P95 was
> 2.0 seconds, compensation P95 was 2.9543 seconds, availability in the nominal
> mixed test was 100%, Kafka lag after drain was 0, and pending Outbox rows after
> drain were 0.
>
> However, not every quality target was achieved. REST acceptance P95 was 810 ms,
> so the 250 ms target was not met. Throughput was 489.91 req/s, so the
> 1000 ops/s target was not met. Real free5GC successful provisioning was not
> validated because the supplied WebConsole returned an incompatible subscriber
> representation, and the adapter correctly normalized it as a conflict.

## If Time Is Short

> The main decision is event-driven collaboration with Kafka, Outbox,
> choreographed saga, and idempotent consumers. It improves resilience and
> traceability, but adds operational complexity. Evidence is honest: 97 tests
> passed, saga P95 was 2.0 seconds, compensation P95 was 2.9543 seconds, but REST
> acceptance P95 and throughput targets were not met, and real free5GC success
> was not validated.

## ADRs To Mention

| ADR | Decision |
|---|---|
| ADR-005 | Event-driven architecture and choreography |
| ADR-006 | Transactional Outbox |
| ADR-007 | Choreographed saga and compensation |
| ADR-008 | Apache Kafka |
| ADR-009 | HLR/HSS and PortabilityHub adapters/ACL |

If repository numbering differs in a local copy, use the repository filenames as
the source of truth.

## Quality Evidence

| Target | Result |
|---|---|
| Unit/integration/e2e tests | 97 passed, 0 failed, 12 skipped |
| Nominal saga P95 | 2.0 s |
| Compensation P95 | 2.9543 s |
| Nominal mixed availability | 100% |
| Kafka lag after drain | 0 |
| Outbox pending rows after drain | 0 |
| REST acceptance P95 | 810 ms, target not met |
| Throughput | 489.91 req/s, target not met |
| Real free5GC success | not validated |

## Cross-Cutting Concepts

- Idempotence with `processed_events`
- Transactional Outbox
- At-least-once Kafka delivery
- Retry with backoff
- DLQ after retry exhaustion
- Append-only audit
- OpenTelemetry trace propagation
- Prometheus metrics and Grafana dashboards
- Privacy: avoid personal data in events/logs/metrics

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Event loss after business commit | Outbox row in same transaction |
| Duplicate event delivery | `processed_events` plus aggregate state guards |
| Kafka broker failure | documented limitation: single broker is not HA |
| External HLR/HSS mismatch | adapter/ACL normalizes failures |
| PortabilityHub status mismatch | use only supplied statuses |
| Operational complexity | dashboards, evidence, troubleshooting, runbooks |
| Performance targets not met | report honestly; identify as remaining optimization |

## If The Teacher Asks

Question: What is the most important ADR?

Answer:

> The event-driven architecture ADR is the most structuring one because it
> changes how services collaborate. It leads directly to Kafka, Outbox,
> idempotent consumers, saga compensation, audit, and observability decisions.

Question: What quality attribute was sacrificed?

Answer:

> Simplicity was sacrificed. A synchronous REST chain is easier to operate and
> debug. We accepted more moving parts to gain resilience, decoupling, and better
> support for long-running workflows.

Question: Can you claim the NFR targets are achieved?

Answer:

> Only the measured ones that passed. Saga and compensation times passed in the
> recorded tests, but REST acceptance P95 and throughput did not meet the stated
> targets. We should not claim those are achieved.

Question: What is the biggest remaining risk?

Answer:

> The biggest technical risks are performance under load and real free5GC
> compatibility. The demo uses mock HLR for nominal success, and the report
> states the real free5GC success path honestly.

Question: What does the DLQ prove?

Answer:

> DLQ proves that technical consumer failures are not silently ignored after
> retry exhaustion. The failed message is preserved with context and can be
> replayed in a controlled way.

## Anchor Sentence

> My role is to be honest about evidence: the architecture improves resilience
> and traceability, but only measured targets can be claimed as achieved.
