# ADR-004 - free5GC as the UC-03 Network Simulator Adapter Target

## Status

Accepted

## Context

The added simulator material contains a reduced free5GC stack with WebConsole provisioning and UDM subscriber-data reads. The bundle also contains a FastAPI usage facade, but UC-04 usage consultation is out of the official Phase 1 implementation scope. The project statement requires simulated HLR/HSS/UDM integration for activation. Recreating a fake simulator would duplicate existing project material and weaken domain realism.

## Decision

Use the existing free5GC simulator as the external network adapter target for UC-03 where available. `svc-lignes-services` owns the adapter boundary:

- `Free5gcHlrAdapter` calls WebConsole for subscriber provisioning.
- `svc-commandes-activations` orchestrates activation but does not call free5GC directly.

The adapter is enabled by configuration. A local mock adapter is used for reproducible demos when the simulator is unavailable. UDM subscriber visibility checks remain a documented simulator capability, but they are not part of the official Phase 1 implementation.

## Consequences

UC-03 is closer to a real telecom activation flow while keeping free5GC isolated from the domain model. The trade-off is that Docker Compose must either run the simulator stack or document how to start it separately.

## Alternatives Considered

Building a custom fake HLR was rejected because the repository already includes a reusable simulator. Direct MongoDB access from BSS services was rejected because provisioning should go through the simulator boundary. The simulator `usage-api` is not used by the official Phase 1 scope because UC-04 is out of scope.
