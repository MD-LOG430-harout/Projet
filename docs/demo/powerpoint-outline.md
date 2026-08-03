# PowerPoint outline - four slides only

## Slide 1 - From Phase 1 to Phase 2

Title: From Phase 1 to Phase 2

Bullets:

- synchronous REST became event-driven
- Kafka + Outbox + saga
- six existing services preserved

Recommended diagram or screenshot:

Use the Phase 2 architecture diagram showing API Gateway, six services, MySQL,
Kafka, PortabilityHub, Prometheus/Grafana, and Jaeger.

Speaker notes, max 45 seconds:

Phase 1 mostly coordinated the services through synchronous REST. Phase 2 keeps
the existing use cases and services, but changes the collaboration style: public
requests are accepted quickly, local state and Outbox events are committed in
MySQL, and Kafka carries the saga facts asynchronously.

## Slide 2 - Nominal saga

Title: Nominal saga

Bullets:

- `CommandePassee -> PaiementAutorise`
- `PaiementAutorise -> LigneActivee`
- `LigneActivee -> CommandeConfirmee`

Recommended diagram or screenshot:

Show the sequence diagram for the nominal order saga, or a terminal command
screenshot showing `HTTP 202`, `Location`, `EN_COURS`, and final `CONFIRMEE`.

Speaker notes, max 45 seconds:

The order endpoint returns `202 Accepted`, not completion. The order service
writes the order, saga state, and `CommandePassee` in one local transaction.
After that, each service consumes and produces facts through Kafka until the
order reaches `CONFIRMEE`.

## Slide 3 - Compensation and portability

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

## Slide 4 - Evidence and limits

Title: Evidence and limits

Bullets:

- 97 passed, 0 failed
- saga P95 2.0 s; compensation P95 2.95 s
- throughput and real free5GC success still unresolved

Recommended diagram or screenshot:

Show the evidence folder, the performance summary, or a screenshot of Grafana
Golden Signals plus the final test result.

Speaker notes, max 45 seconds:

The saved validation has 97 passed, 0 failed, and 12 skipped. Nominal saga P95
was 2.0 seconds, compensation P95 was 2.9543 seconds, availability was 100% in
the nominal mixed test, Kafka lag after drain was 0, and pending Outbox rows
after drain were 0. The honest limits are that acceptance P95 and throughput did
not meet targets, and real free5GC success was not validated.

