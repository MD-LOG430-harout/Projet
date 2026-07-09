# UC-06 - Paiement de facture: Phase 1 Coverage

## Scope Decision

UC-06 is implemented in `svc-usage-facturation` as a Phase 1 invoice payment slice.
It validates a payable invoice, charges a simulated payment gateway, records an idempotent payment, marks the invoice as paid, and emits audit events.

Phase 1 decisions:

- Invoice payment is exposed through `POST /v1/invoices/{invoice_id}/payments`.
- `Idempotency-Key` is mandatory and prevents duplicate payment transactions.
- Only full payment is supported: the payment amount must equal `invoice.amount_due`.
- Only `SIMULATED_CARD` and `CAD` are accepted.
- Successful payment marks the invoice `PAID`.
- Partial payment is not implemented in Phase 1.
- Gateway refusal and timeout are represented as `503 payment_gateway_unavailable`.
- No pending/reconciliation workflow is implemented in Phase 1.

## Main Implemented Flow

1. The client selects an invoice, typically after `GET /v1/invoices` or `GET /v1/invoices/{invoice_id}`.
2. The client sends `POST /v1/invoices/{invoice_id}/payments` with `customerId`, `paymentMethod=SIMULATED_CARD`, `amount`, `currency=CAD`, `TraceId`, and `Idempotency-Key`.
3. `svc-usage-facturation` validates the idempotency key and request payload.
4. The service checks whether the same idempotency key was already used.
5. The service loads the invoice and verifies that it belongs to the customer.
6. The service verifies that the invoice status is `OPEN`.
7. The service verifies that the amount and currency match the invoice.
8. The service records `PAYMENT_REQUESTED`.
9. The service calls the simulated payment gateway.
10. On success, the service inserts the payment and marks the invoice `PAID` in the same repository operation.
11. The service records `PAYMENT_ACCEPTED` and `INVOICE_PAID`.
12. The response returns payment status `ACCEPTED`, invoice status `PAID`, and the simulated gateway transaction id.

## Coverage Matrix

| Path | Status | Evidence | Reason |
|---|---|---|---|
| Main payment path | Implemented | `POST /v1/invoices/{invoice_id}/payments`; `PayInvoice`; `test_successful_payment_and_idempotent_replay_and_audit` | Demonstrates invoice validation, gateway charge, payment persistence, invoice status update, idempotency, and audit. |
| FA1 - Invoice missing or not payable | Implemented | `invoice_not_found`, `invoice_not_open`; `test_unknown_invoice_returns_404` | Missing invoices return `404`; non-`OPEN` invoices are rejected. |
| FA2 - Payment refused | Partial | Simulated gateway can fail; `test_payment_gateway_failure_returns_503_and_audits` | Refusal is not modeled separately from gateway unavailable. |
| FA3 - Invoice already paid | Implemented | `invoice_already_paid`; `test_invoice_already_paid_returns_409_with_new_key` | A new payment attempt for a paid invoice is blocked. |
| FA4 - Gateway timeout | Partial | `payment_gateway_unavailable` | Timeout/unavailable are collapsed into the same `503`; no pending reconciliation state exists. |
| FA5 - Duplicate request | Implemented | `Idempotency-Key`; `test_successful_payment_and_idempotent_replay_and_audit`; `test_same_payment_key_different_payload_returns_conflict` | Same key and same payload replays the stored payment; same key with different payload returns conflict. |
| Partial payment | Out of scope | Payment amount must equal invoice amount | Phase 1 supports full payment only. |

## Future Work Boundaries

Future UC-06 extensions may add:

- partial payments and remaining-balance tracking;
- declined payment status distinct from gateway timeout/unavailable;
- pending payment state and reconciliation workflow;
- retry/reprise job for gateway timeout;
- additional payment methods beyond `SIMULATED_CARD`.
