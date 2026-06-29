# UC-03 - Activation d'une ligne: Phase 1 Coverage

## Scope Decision

UC-03 is implemented as a focused Phase 1 vertical slice. It demonstrates the activation path end to end without expanding into full order-taking, full fraud detection, a real portability hub, or retry orchestration.

Phase 1 decisions:

- Activation is exposed through `POST /v1/activations` and passes through the NGINX API Gateway.
- The activation request acts as the simplified activation command for Phase 1.
- Full UC-05 order-taking and order lifecycle validation are excluded from this slice.
- Full UC-07 fraud detection is excluded; UC-03 only performs a simple customer risk-level block when available.
- Portability is implemented only as a Phase 1 simulation: `numberMode=PORT_IN` accepts a provided `msisdn`, records `portabilityStatus=ACCEPTED`, and then provisions the line. A real portability hub with refusal/pending flows remains future work.
- `svc-lignes-services` provisions the subscriber through the free5GC WebConsole adapter when `HLR_ENABLED=true`.
- `Idempotency-Key` is mandatory and prevents duplicate line provisioning.

## Updated Preconditions

For Phase 1, UC-03 does not require a previously created UC-05 order. The precondition is:

> A valid activation request exists for an identified, active, verified customer and an active offer. Full order validation belongs to UC-05 and is excluded from this Phase 1 slice.

The network simulator should be available when `HLR_ENABLED=true`. If it is unavailable, the activation fails with a normalized error, the line is marked failed by `svc-lignes-services`, and the failure is audited.

## Main Implemented Flow

1. The client sends `POST /v1/activations` with `customerId`, `offerId`, `simType`, optional `numberMode`, optional `msisdn`, `TraceId`, and `Idempotency-Key`.
2. `svc-commandes-activations` checks idempotency before doing side effects.
3. `svc-commandes-activations` validates the customer through `svc-clients-identite`.
4. `svc-commandes-activations` blocks activation if the customer's `riskLevel` is `HIGH`.
5. `svc-commandes-activations` validates the offer through `svc-catalogue-offres`.
6. `svc-commandes-activations` calls `svc-lignes-services` to assign a new MSISDN (`numberMode=NEW`) or accept a simulated port-in MSISDN (`numberMode=PORT_IN`) and provision the SIM/eSIM.
7. `svc-lignes-services` creates a pending line, calls the HLR/free5GC adapter, and marks the line `ACTIVE` or `FAILED`.
8. `svc-commandes-activations` stores the replayable activation result.
9. `svc-conformite-audit` stores append-only audit events for the activation path.

## Matrice de couverture UC-03

| Path | Status | Evidence | Reason |
|---|---|---|---|
| Main activation path | Implemented | `POST /v1/activations`; `svc-commandes-activations/app/application/commands/create_activation.py`; Swagger and Postman collection | Demonstrates customer validation, offer validation, line creation, free5GC provisioning, audit, and response through the gateway. |
| Preconditions: valid activation request, identified customer, active offer | Implemented | Customer lookup via `CustomerClient`; offer lookup via `OfferClient`; tests `test_unknown_customer_returns_404`, `test_unknown_offer_returns_404`, `test_inactive_offer_returns_409` | Phase 1 replaces full order validation with a valid activation command because UC-05 is excluded. |
| FA1 - Commande inexistante/invalide | Documented / adapted | Missing/invalid activation fields return `validation_error`; unknown customer/offer return normalized errors | Full UC-05 order-taking and order status validation are intentionally out of scope. |
| FA2 - Risque eleve ou fraude detectee | Partial | `riskLevel == HIGH` blocks activation with `activation_blocked_high_risk`; audit event `ACTIVATION_BLOCKED_HIGH_RISK`; test `test_high_risk_customer_blocks_activation_and_audits_decision` | Provides a Phase 1 risk control without building full UC-07 fraud detection. |
| FA3 - Aucun MSISDN disponible | Documented | Current code assigns generated MSISDN and enforces uniqueness in MySQL (`service_lines.msisdn`) | A real MSISDN inventory/pool exhaustion workflow is not required for this slice. |
| FA4 - Portabilite refusee/indisponible | Partial | OpenAPI supports `numberMode=PORT_IN`; `svc-lignes-services` requires the provided `msisdn`, stores `portabilityStatus=ACCEPTED`, and provisions the line; Postman includes "Activate line with simulated portability" | Phase 1 supports the happy path for keeping an old number, but refusal, pending status, and an external portability hub remain future work. |
| FA5 - SIM/eSIM invalide ou deja utilisee | Partial | `simType` validation in `ActivateLine`; generated `simIdentifier`; unique constraints on `sim_identifier` and `imsi` | Basic validation and uniqueness safeguards exist, but no full SIM inventory is implemented. |
| FA6 - HLR/free5GC failure | Implemented basic path | `ActivateLine` marks the line failed when adapter provisioning raises; orchestrator returns normalized 503 and writes `ACTIVATION_FAILED`; tests cover HLR failure | Phase 1 stores failure state and audit evidence but does not implement a retry/reprise endpoint. |
| FA7 - Requete repetee | Implemented | Required `Idempotency-Key`; unique key in `commandes_activations.activations`; replay returns same result with `Idempotency-Replayed: true`; tests and Postman replay request | Prevents duplicate activation and duplicate free5GC provisioning. |

## Future Work Boundaries

Future UC-03/UC-05/UC-07 extensions may add:

- full order aggregate and order status validation;
- portability request aggregate, external portability hub adapter, refusal handling, and pending/retry lifecycle;
- SIM/eSIM inventory and reservation lifecycle;
- MSISDN pool allocation with exhaustion and quarantine rules;
- fraud scoring beyond simple customer `riskLevel`;
- activation retry/reprise endpoint for failed free5GC provisioning.
