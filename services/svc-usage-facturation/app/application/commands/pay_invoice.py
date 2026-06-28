import hashlib
import json
import uuid

from services.shared.errors import ApiError

from app.domain.model.payment import Payment
from app.application.queries.get_invoices import _invoice_public


class PayInvoice:
    def __init__(self, repository, payment_gateway, audit_client=None):
        self.repository = repository
        self.payment_gateway = payment_gateway
        self.audit_client = audit_client

    def execute(self, invoice_id, payload, idempotency_key, trace_id=None):
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required")
        self._validate_payload(payload)
        request_hash = self._hash_payload(invoice_id, payload)
        existing = self.repository.find_payment_by_idempotency_key(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ApiError(409, "idempotency_key_conflict", "Idempotency-Key was already used with a different payload")
            return self._response_from_existing(existing), int(existing["http_status"]), True

        invoice = self.repository.get_invoice(invoice_id)
        if not invoice:
            raise ApiError(404, "invoice_not_found", "Invoice not found", {"invoiceId": invoice_id})
        if invoice["customer_id"] != payload["customerId"]:
            raise ApiError(409, "invoice_customer_mismatch", "Invoice does not belong to the customer")
        if invoice["status"] != "OPEN":
            raise ApiError(409, "invoice_not_open", "Invoice is not open for payment", {"status": invoice["status"]})
        if float(invoice["amount_due"]) != float(payload["amount"]):
            raise ApiError(409, "payment_amount_mismatch", "Payment amount must match invoice amount")
        if invoice["currency"] != payload["currency"]:
            raise ApiError(409, "payment_currency_mismatch", "Payment currency must match invoice currency")

        payment_id = str(uuid.uuid4())
        self._audit("PAYMENT_REQUESTED", payload["customerId"], invoice_id, "PENDING", trace_id, {"paymentId": payment_id})
        try:
            gateway_result = self.payment_gateway.charge(
                {
                    "paymentId": payment_id,
                    "invoiceId": invoice_id,
                    "customerId": payload["customerId"],
                    "amount": payload["amount"],
                    "currency": payload["currency"],
                    "paymentMethod": payload["paymentMethod"],
                },
                trace_id=trace_id,
            )
        except Exception as exc:
            self._audit("PAYMENT_FAILED", payload["customerId"], invoice_id, "FAILED", trace_id, {"error": str(exc)})
            raise ApiError(503, "payment_gateway_unavailable", "Simulated payment gateway is unavailable")

        response = {
            "paymentId": payment_id,
            "invoiceId": invoice_id,
            "customerId": payload["customerId"],
            "amount": float(payload["amount"]),
            "currency": payload["currency"],
            "status": "ACCEPTED",
            "invoiceStatus": "PAID",
            "gatewayTransactionId": gateway_result["gatewayTransactionId"],
        }
        payment = Payment(
            payment_id=payment_id,
            invoice_id=invoice_id,
            customer_id=payload["customerId"],
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            amount=float(payload["amount"]),
            currency=payload["currency"],
            payment_method=payload["paymentMethod"],
            status="ACCEPTED",
            response_body=response,
            http_status=201,
        )
        self.repository.create_payment_and_mark_invoice_paid(payment)
        self._audit("PAYMENT_ACCEPTED", payload["customerId"], invoice_id, "SUCCESS", trace_id, {"paymentId": payment_id})
        self._audit("INVOICE_PAID", payload["customerId"], invoice_id, "SUCCESS", trace_id, {"paymentId": payment_id})
        return response, 201, False

    def _validate_payload(self, payload):
        if not payload.get("customerId"):
            raise ApiError(400, "validation_error", "customerId is required", {"field": "customerId"})
        if payload.get("paymentMethod") != "SIMULATED_CARD":
            raise ApiError(400, "validation_error", "paymentMethod must be SIMULATED_CARD", {"field": "paymentMethod"})
        if float(payload.get("amount") or 0) <= 0:
            raise ApiError(400, "validation_error", "amount must be greater than zero", {"field": "amount"})
        if payload.get("currency") != "CAD":
            raise ApiError(400, "validation_error", "currency must be CAD", {"field": "currency"})

    def _hash_payload(self, invoice_id, payload):
        canonical = json.dumps({"invoiceId": invoice_id, **payload}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _response_from_existing(self, existing):
        body = existing["response_body"]
        return json.loads(body) if isinstance(body, str) else body

    def _audit(self, event_type, customer_id, resource_id, result, trace_id, metadata=None):
        if self.audit_client:
            self.audit_client.record(
                {
                    "eventType": event_type,
                    "actorId": customer_id,
                    "customerId": customer_id,
                    "resourceId": resource_id,
                    "sourceService": "svc-usage-facturation",
                    "result": result,
                    "metadata": metadata or {},
                },
                trace_id=trace_id,
            )
