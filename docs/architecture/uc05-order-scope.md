# UC-05 - Prise de commande: Phase 1 Coverage

## Scope Decision

UC-05 is implemented as a Phase 1 order intake slice in `svc-commandes-activations`.
It validates the customer, validates the selected offer, applies a simple risk control, stores an idempotent order, and simulates confirmation.

Phase 1 decisions:

- Order intake is exposed through `POST /v1/orders` behind the API Gateway.
- `Idempotency-Key` is mandatory and prevents duplicate order creation.
- `NEW_PLAN` is implemented and creates an order with status `ACCEPTED`.
- Accepted orders are marked `READY_FOR_ACTIVATION`; actual line provisioning is handled separately by UC-03.
- `CHANGE_PLAN` and `ADD_OPTION` are accepted by validation as known order types, but are not executed in Phase 1.
- Confirmation is simulated with `confirmationStatus=SIMULATED_SENT`; no notification provider is called.
- Fraud detection is limited to the customer's existing `riskLevel`; full UC-07 fraud scoring is future work.

## Main Implemented Flow

1. The client sends `POST /v1/orders` with `customerId`, `offerId`, `orderType`, `quantity`, `TraceId`, and `Idempotency-Key`.
2. `svc-commandes-activations` validates the payload and idempotency key.
3. The service checks whether the same idempotency key was already used.
4. The service validates the customer through `svc-clients-identite`.
5. The service rejects the order if the customer is not `ACTIVE`, the identity is not `VERIFIED`, or `riskLevel` is `HIGH`.
6. The service validates the offer through `svc-catalogue-offres`.
7. For `NEW_PLAN`, the service calculates `totalAmount = monthlyPrice * quantity`.
8. The service persists the order with status `ACCEPTED`, `orchestrationStatus=READY_FOR_ACTIVATION`, and `confirmationStatus=SIMULATED_SENT`.
9. `svc-conformite-audit` stores append-only order events.

## Coverage Matrix

| Path | Status | Evidence | Reason |
|---|---|---|---|
| Main order intake | Implemented | `POST /v1/orders`; `CreateOrder`; `test_successful_order_creation_and_audit` | Demonstrates customer validation, offer validation, pricing, order persistence, audit, and simulated confirmation. |
| FA1 - Offer missing or inactive | Implemented | `test_unknown_offer_returns_404_for_order`; `test_inactive_offer_returns_409_for_order` | Unknown offers return `offer_not_found`; inactive offers return `offer_inactive`. |
| FA2 - Customer not eligible | Implemented | `test_ineligible_customer_returns_403_and_audits` | Customer must be `ACTIVE` and identity must be `VERIFIED`. |
| FA3 - Fraud or high risk | Partial | `test_high_risk_customer_blocks_order_and_audits` | Phase 1 blocks `riskLevel=HIGH`; full fraud scoring is future work. |
| FA4 - Incompatible offer/order type | Partial | `test_change_plan_requires_line_id_as_phase1_compatibility_check` | `CHANGE_PLAN` and `ADD_OPTION` require `lineId` and then return `501 order_type_not_implemented`; only `NEW_PLAN` is implemented. |
| FA5 - Execution/provisioning failure | Out of scope for UC-05 | UC-03 activation tests | UC-05 does not provision services. It prepares the order for activation. |
| FA6 - Confirmation failure | Simulated only | `confirmationStatus=SIMULATED_SENT`; `ORDER_CONFIRMATION_SIMULATED` | No real notification provider or retry queue exists in Phase 1. |
| FA7 - Duplicate order | Implemented | `test_idempotent_order_replay_returns_same_order`; `test_same_order_key_with_different_payload_returns_conflict` | Same key and same payload replays the stored order; same key with different payload returns conflict. |

## Future Work Boundaries

Future UC-05 extensions may add:

- automatic orchestration from accepted order to UC-03 activation;
- full `CHANGE_PLAN` and `ADD_OPTION` execution against an existing line;
- service compatibility rules based on current line state and options;
- notification provider integration and retry handling;
- richer fraud scoring beyond customer `riskLevel`.
