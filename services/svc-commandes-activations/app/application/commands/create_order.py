import hashlib
import json
import uuid

from services.shared.errors import ApiError

from app.domain.model.order import Order


SUPPORTED_ORDER_TYPES = {"NEW_PLAN", "CHANGE_PLAN", "ADD_OPTION"}
IMPLEMENTED_ORDER_TYPES = {"NEW_PLAN"}


class CreateOrder:
    SUMMARY_AUDIT_EVENTS = {
        "ORDER_ACCEPTED",
        "ORDER_REJECTED",
        "ORDER_BLOCKED_RISK",
        "ORDER_ELIGIBILITY_FAILED",
        "ORDER_COMPATIBILITY_FAILED",
    }

    def __init__(self, order_repository, customer_client, offer_client, audit_client=None, audit_level="detailed"):
        self.order_repository = order_repository
        self.customer_client = customer_client
        self.offer_client = offer_client
        self.audit_client = audit_client
        self.audit_level = audit_level

    def execute(self, payload, idempotency_key, trace_id=None):
        self._validate_payload(payload)
        request_hash = self._hash_payload(payload)
        existing = self.order_repository.find_order_by_idempotency_key(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ApiError(409, "idempotency_key_conflict", "Idempotency-Key was already used with a different payload")
            return self._response_from_existing(existing), int(existing["http_status"]), True

        order_id = str(uuid.uuid4())
        customer_id = payload["customerId"]
        offer_id = payload["offerId"]
        self._audit("ORDER_REQUESTED", order_id, customer_id, "PENDING", trace_id, {"offerId": offer_id})

        try:
            customer = self.customer_client.get_customer(customer_id, trace_id=trace_id)
            if customer.get("status") != "ACTIVE" or customer.get("identityStatus") != "VERIFIED":
                self._audit(
                    "ORDER_ELIGIBILITY_FAILED",
                    order_id,
                    customer_id,
                    "FAILED",
                    trace_id,
                    {"status": customer.get("status"), "identityStatus": customer.get("identityStatus")},
                )
                raise ApiError(403, "customer_not_eligible", "Customer is not eligible to place this order")
            self._audit("ORDER_CUSTOMER_VALIDATED", order_id, customer_id, "SUCCESS", trace_id)
            self._audit("ORDER_RISK_CHECKED", order_id, customer_id, "SUCCESS", trace_id, {"riskLevel": customer.get("riskLevel")})
            if customer.get("riskLevel") == "HIGH":
                self._audit("ORDER_BLOCKED_RISK", order_id, customer_id, "FAILED", trace_id, {"riskLevel": "HIGH"})
                raise ApiError(409, "order_blocked_high_risk", "Order is blocked because the customer risk level is high")

            offer = self.offer_client.get_offer(offer_id, trace_id=trace_id)
            if offer.get("status") != "ACTIVE":
                raise ApiError(409, "offer_inactive", "Offer is not active", {"offerId": offer_id})
            self._audit("ORDER_OFFER_VALIDATED", order_id, customer_id, "SUCCESS", trace_id)

            if payload["orderType"] in {"CHANGE_PLAN", "ADD_OPTION"} and not payload.get("lineId"):
                self._audit(
                    "ORDER_COMPATIBILITY_FAILED",
                    order_id,
                    customer_id,
                    "FAILED",
                    trace_id,
                    {"orderType": payload["orderType"], "reason": "lineId_required"},
                )
                raise ApiError(409, "order_incompatible", "lineId is required for this order type", {"field": "lineId"})
            if payload["orderType"] not in IMPLEMENTED_ORDER_TYPES:
                self._audit(
                    "ORDER_COMPATIBILITY_FAILED",
                    order_id,
                    customer_id,
                    "FAILED",
                    trace_id,
                    {"orderType": payload["orderType"], "reason": "phase1_not_implemented"},
                )
                raise ApiError(501, "order_type_not_implemented", "This order type is documented as future work for Phase 1")
        except ApiError as exc:
            self._audit("ORDER_REJECTED", order_id, customer_id, "FAILED", trace_id, {"code": exc.code, "details": exc.details})
            raise

        quantity = int(payload["quantity"])
        monthly_price = float(offer.get("monthlyPrice") or 0)
        total_amount = round(monthly_price * quantity, 2)
        response = {
            "orderId": order_id,
            "customerId": customer_id,
            "offerId": offer_id,
            "orderType": payload["orderType"],
            "status": "ACCEPTED",
            "orchestrationStatus": "READY_FOR_ACTIVATION",
            "confirmationStatus": "SIMULATED_SENT",
            "totalAmount": total_amount,
            "currency": "CAD",
        }
        order = Order(
            order_id=order_id,
            customer_id=customer_id,
            offer_id=offer_id,
            order_type=payload["orderType"],
            status="ACCEPTED",
            orchestration_status="READY_FOR_ACTIVATION",
            confirmation_status="SIMULATED_SENT",
            total_amount=total_amount,
            currency="CAD",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            response_body=response,
            http_status=201,
        )
        response["createdAt"] = order.created_at.isoformat()
        order = Order(
            order_id=order.order_id,
            customer_id=order.customer_id,
            offer_id=order.offer_id,
            order_type=order.order_type,
            status=order.status,
            orchestration_status=order.orchestration_status,
            confirmation_status=order.confirmation_status,
            total_amount=order.total_amount,
            currency=order.currency,
            idempotency_key=order.idempotency_key,
            request_hash=order.request_hash,
            response_body=response,
            http_status=order.http_status,
            created_at=order.created_at,
        )
        self.order_repository.create_order(order)
        self._audit("ORDER_ACCEPTED", order_id, customer_id, "SUCCESS", trace_id, {"totalAmount": total_amount, "currency": "CAD"})
        self._audit("ORDER_CONFIRMATION_SIMULATED", order_id, customer_id, "SUCCESS", trace_id, {"confirmationStatus": "SIMULATED_SENT"})
        return response, 201, False

    def _validate_payload(self, payload):
        if not payload.get("customerId"):
            raise ApiError(400, "validation_error", "customerId is required", {"field": "customerId"})
        if not payload.get("offerId"):
            raise ApiError(400, "validation_error", "offerId is required", {"field": "offerId"})
        if payload.get("orderType") not in SUPPORTED_ORDER_TYPES:
            raise ApiError(400, "validation_error", "orderType must be NEW_PLAN, CHANGE_PLAN, or ADD_OPTION", {"field": "orderType"})
        try:
            quantity = int(payload.get("quantity"))
        except (TypeError, ValueError):
            raise ApiError(400, "validation_error", "quantity must be a positive integer", {"field": "quantity"})
        if quantity < 1:
            raise ApiError(400, "validation_error", "quantity must be a positive integer", {"field": "quantity"})
        payload["quantity"] = quantity

    def _hash_payload(self, payload):
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _response_from_existing(self, existing):
        body = existing["response_body"]
        return json.loads(body) if isinstance(body, str) else body

    def _audit(self, event_type, order_id, customer_id, result, trace_id, metadata=None):
        if not self.audit_client:
            return
        if self.audit_level == "summary" and event_type not in self.SUMMARY_AUDIT_EVENTS:
            return
        self.audit_client.record(
            {
                "eventType": event_type,
                "actorId": customer_id,
                "customerId": customer_id,
                "resourceId": order_id,
                "sourceService": "svc-commandes-activations",
                "result": result,
                "metadata": metadata or {},
            },
            trace_id=trace_id,
        )
