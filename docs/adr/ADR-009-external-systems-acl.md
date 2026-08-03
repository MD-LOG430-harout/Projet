# ADR-009 - Integration HLR/HSS et PortabilityHub via adapters/ACL

## Status

Accepted for Phase 2.

## Context

The supplied free5GC and PortabilityHub implementations are mandatory and their
executable contracts take precedence over conceptual template material.

## Decision

`svc-lignes-services` owns domain ports and anti-corruption adapters for both
systems. free5GC provisioning uses only `POST /api/login`, subscriber `GET`, and
subscriber `POST`; incompatible existing data is a normalized activation
failure because no supported update operation exists. Calls propagate W3C
`traceparent`, use bounded retry/timeout policies, and keep credentials and
subscriber secrets in environment-backed configuration.

Portability initiation uses synchronous `POST /portability/order`. Hub status
notifications, when used, arrive through its supplied HTTP webhook mechanism.
The external statuses are `pending_out_validation`, `approved`, `rejected`,
`port_completed`, and `cancelled`. The reference seven-topic external Kafka
choreography is not the CanTelcoX internal topology.

## Consequences

Network calls occur outside SQL transactions. Adapter results are converted
into local transactions and one of the eleven internal events. Correlation is
persisted by Hub order identifier; external structures do not enter the domain.
