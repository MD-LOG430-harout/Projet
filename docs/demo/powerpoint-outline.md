# PowerPoint outline - four slides for the CanTelcoX CTO

## Slide 1 - The business and technical problem

Title: CanTelcoX: making long telecom workflows resilient

Bullets:

- long synchronous chains amplify outages and latency
- order state is difficult to recover and trace
- objective: evolve without rewriting six services

Recommended diagram or screenshot:

Use the Phase 2 architecture diagram showing API Gateway, six services, MySQL,
Kafka, PortabilityHub, Prometheus/Grafana, and Jaeger.

Speaker notes, max 45 seconds:

Address the teacher as CanTelcoX's CTO. Start with the operational problem, not
the technology. Explain that the recommendation preserves the existing services
and public APIs while changing the internal collaboration model.

## Slide 2 - Recommended architecture

Title: Evolutionary event-driven architecture

Bullets:

- REST for immediate interaction; Kafka for long workflows
- Outbox + idempotent consumers protect integrity
- choreographed saga reaches a controlled terminal state

Recommended diagram or screenshot:

Show the sequence diagram for the nominal order saga, or a terminal command
screenshot showing `HTTP 202`, `Location`, `EN_COURS`, and final `CONFIRMEE`.

Speaker notes, max 45 seconds:

The order endpoint returns `202 Accepted`, not completion. The order service
writes the order, saga state, and `CommandePassee` in one local transaction.
After that, each service consumes and produces facts through Kafka until the
order reaches `CONFIRMEE`.

## Slide 3 - Evidence under success and failure

Title: Compensation and portability

Bullets:

- `ActivationEchouee -> CommandeAnnulee`
- `CommandeAnnulee -> PaiementRembourse`
- PortabilityHub REST initiation plus callback

Recommended diagram or screenshot:

Show the compensation sequence diagram or a PortabilityHub test output screenshot
with `port_completed` and `rejected` scenarios.

Speaker notes, max 45 seconds:

Compensation is modeled as business facts, not reverse database transactions.
For portability, initiation is synchronous REST to the supplied Hub, then HTTP
callbacks are mapped by the ACL: `port_completed` becomes `NumeroPorte`, while
`rejected` and `cancelled` become `PortabiliteEchouee`.

## Slide 4 - Recommendation and production conditions

Title: Proceed, with three production gates

Bullets:

- make Kafka highly available
- meet acceptance latency and throughput targets
- validate the real free5GC path end to end

Recommended diagram or screenshot:

Show the evidence folder, the performance summary, or a screenshot of Grafana
Golden Signals plus the final test result.

Speaker notes, max 45 seconds:

Recommend continuing the architecture because the prototype validates the core
integrity and resilience mechanisms. Do not recommend production approval yet:
make it conditional on Kafka high availability, performance remediation, and
successful end-to-end free5GC validation.

