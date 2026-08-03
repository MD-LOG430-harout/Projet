# Role 2 Demo Guide - Responsable du domaine DDD

Use this during the oral defense. Your goal is not to present every technical
detail. Your goal is to defend the domain model: bounded contexts, relationships,
aggregates, invariants, and glossary.

## My Role

I am responsible for:

- Section 5: Building Block View / Vue des blocs de construction
- Section 12: Glossary / Glossaire
- 4+1: detailed logical view
- DDD explanation: bounded contexts, aggregates, invariants, context relations

My key idea:

> I defend how the business domain is divided, who owns which data, and how the
> services collaborate without breaking domain boundaries.

## 12-15 Minute Team Flow

Approximate timing:

| Time | Presenter | Topic |
|---|---|---|
| 0:00-1:15 | Role 1 | Context, Phase 1 to Phase 2 objectives |
| 1:15-3:15 | Me | DDD, bounded contexts, aggregates, invariants |
| 3:15-5:15 | Role 3 | Event flow, saga, Outbox, Kafka |
| 5:15-6:45 | Role 4 | Deployment and hexagonal implementation |
| 6:45-8:15 | Role 5 | Quality results, ADRs, risks, limits |
| 8:15-11:30 | Demo | Nominal saga, then the end-to-end Jaeger trace |
| 11:30-13:00 | Demo | Compensation, event replay, DLQ |
| 13:00-13:30 | Demo | Grafana Event-Driven and the sync/event comparison |
| 13:30-15:00 | Team | Conclusion and questions buffer |

The step-by-step version of this run is
[demo-15-minutes.md](demo-15-minutes.md).

## My 90-120 Second Script

Say this calmly, not too fast:

> My responsibility is the detailed logical view and the DDD part of the
> architecture. In Phase 2, we did not add new use cases. We adapted the existing
> Phase 1 use cases to an event-driven collaboration model.
>
> The bounded contexts remain separated by business responsibility:
> `svc-clients-identite` owns customer identity, authentication, MFA, and KYC;
> `svc-catalogue-offres` owns offers; `svc-commandes-activations` owns the
> customer-visible order lifecycle; `svc-lignes-services` owns line activation,
> MSISDN, HLR/HSS, and portability; `svc-usage-facturation` owns payment
> authorization, refusal, refund, and billing; and `svc-conformite-audit` owns
> immutable audit records.
>
> The central aggregate for the customer flow is `Commande`. It is created as
> `EN_COURS`, then reaches one terminal state: either `CONFIRMEE` or `ANNULEE`.
> But the order service is not a central orchestrator. Other contexts react to
> domain facts through Kafka and protect their own invariants locally.
>
> The important domain invariants are: a terminal order cannot move backward;
> duplicate events must not create duplicate business effects; a line cannot
> become active before successful provisioning; payment refusal cancels the
> command; and audit records are append-only.
>
> External systems are isolated with adapters and ACLs. For example, HLR/HSS and
> PortabilityHub have their own external models, but inside CanTelcoX we translate
> them into internal events such as `LigneActivee`, `ActivationEchouee`,
> `NumeroPorte`, and `PortabiliteEchouee`.

## If Time Is Short

> My role is the DDD and detailed logical view. We kept the Phase 1 use cases and
> separated the system into bounded contexts by business ownership: customers,
> catalogue, orders, lines, billing, and audit. The main aggregate is
> `Commande`: it starts as `EN_COURS` and ends as either `CONFIRMEE` or
> `ANNULEE`. Each context protects its own invariants, and external systems like
> HLR/HSS and PortabilityHub are isolated through adapters and ACLs.

## Bounded Contexts

| Bounded context | Service | Owns |
|---|---|---|
| Clients and identity | `svc-clients-identite` | registration, login, MFA, KYC |
| Catalogue | `svc-catalogue-offres` | offers and catalogue cache |
| Commands and activations | `svc-commandes-activations` | orders, order status, saga state |
| Lines and services | `svc-lignes-services` | line lifecycle, MSISDN, HLR/HSS, portability |
| Usage and billing | `svc-usage-facturation` | payment authorization, refusal, refund, invoices |
| Compliance and audit | `svc-conformite-audit` | append-only audit journal |

## Aggregates To Mention

| Aggregate | Service | Main invariant |
|---|---|---|
| `Commande` | `svc-commandes-activations` | moves from `EN_COURS` to one terminal state |
| `SagaState` | `svc-commandes-activations` | tracks saga progress without orchestrating every step |
| `ServiceLine` / line state | `svc-lignes-services` | line active only after provisioning succeeds |
| Payment authorization | `svc-usage-facturation` | refusal and refund are idempotent business facts |
| Portability correlation | `svc-lignes-services` | Hub statuses are normalized before internal events |
| Audit event | `svc-conformite-audit` | append-only and deduplicated by `eventId` |

## Context Relationships

Use these terms if asked:

- Published language: internal Kafka event names like `CommandePassee`,
  `PaiementAutorise`, and `LigneActivee`.
- Anti-corruption layer: used for HLR/HSS and PortabilityHub.
- Customer-supplier style: order context publishes facts; billing and lines react.
- No shared database ownership: each service owns its own schema/tables.

Good sentence:

> The contexts collaborate through stable business events, not by directly
> modifying each other's data.

## Invariants

Remember these:

- A command starts as `EN_COURS`.
- A command ends as either `CONFIRMEE` or `ANNULEE`.
- A terminal command cannot move backward.
- Duplicate events cannot create duplicate business effects.
- Payment refusal leads to cancellation, not activation.
- A line cannot become `ACTIVE` before HLR/HSS or mock HLR succeeds.
- External statuses are translated by adapters/ACLs.
- Audit is append-only.

## Demo Commands

Nominal saga:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
```

This shows:

```text
CommandePassee
-> PaiementAutorise
-> LigneActivee
-> CommandeConfirmee
```

Compensation:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
```

This shows:

```text
CommandePassee
-> PaiementRefuse
-> CommandeAnnulee
```

Preflight:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
```

PortabilityHub:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

## If The Teacher Asks

Question: Why these bounded contexts?

Answer:

> Because each context owns a different business capability and its own data.
> Customers own identity. Catalogue owns offers. Commands owns the order
> lifecycle. Lines owns activation and portability. Billing owns payment facts.
> Audit owns compliance records. This avoids mixing responsibilities and prevents
> one service from directly changing another service's domain state.

Question: What is the aggregate root?

Answer:

> The main aggregate root for my section is `Commande`. It controls the customer
> visible lifecycle and exposes the status endpoint. Other aggregates exist in
> their own contexts, such as line state, payment authorization state, portability
> correlation, and audit records.

Question: Why not one big transaction?

Answer:

> Because the services own separate data and external systems are involved. A
> distributed transaction would tightly couple the services. Phase 2 uses a saga:
> each service commits locally, publishes a business fact, and compensates with
> another business fact if a later step fails.

Question: How do you avoid duplicates?

Answer:

> Consumers use `processed_events` for idempotence and aggregate state guards for
> business safety. So if Kafka delivers the same event again, the service detects
> the duplicate or sees that the aggregate is already terminal and does not apply
> the effect twice.

Question: What is the role of ACL?

Answer:

> ACL protects our domain from external models. HLR/HSS and PortabilityHub do not
> leak their raw structures into our internal domain. Adapters translate their
> statuses and failures into internal domain events.

## Honest Limits To Mention

Use these only if asked about validation:

- Verified tests: 97 passed, 0 failed, 12 skipped.
- Nominal saga P95: 2.0 seconds.
- Compensation P95: 2.9543 seconds.
- Availability in nominal mixed test: 100%.
- Kafka lag after drain: 0.
- Pending Outbox rows after drain: 0.
- Acceptance P95 target was not met in the final load test.
- Throughput target was not met.
- Real free5GC successful provisioning was not validated.

## My Anchor Sentence

If you get nervous, come back to this:

> My role is to explain ownership: each bounded context owns its data and
> invariants, and Phase 2 connects those contexts with events and ACLs instead of
> direct cross-service state changes.
