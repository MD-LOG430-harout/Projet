import hashlib
import json
import uuid

from services.shared.errors import ApiError

from app.domain.model.activation import Activation


class CreateActivation:
    def __init__(self, activation_repository, customer_client, offer_client, line_client, audit_client=None):
        self.activation_repository = activation_repository
        self.customer_client = customer_client
        self.offer_client = offer_client
        self.line_client = line_client
        self.audit_client = audit_client

    def execute(self, payload, idempotency_key, trace_id=None):
        self._validate_payload(payload)
        request_hash = self._hash_payload(payload)
        existing = self.activation_repository.find_by_idempotency_key(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ApiError(409, "idempotency_key_conflict", "Idempotency-Key was already used with a different payload")
            return self._response_from_existing(existing), int(existing["http_status"]), True

        activation_id = str(uuid.uuid4())
        customer_id = payload["customerId"]
        offer_id = payload["offerId"]
        self._audit("ACTIVATION_REQUESTED", activation_id, customer_id, "PENDING", trace_id, {"offerId": offer_id})

        try:
            customer = self.customer_client.get_customer(customer_id, trace_id=trace_id)
            if customer.get("status") != "ACTIVE" or customer.get("identityStatus") != "VERIFIED":
                raise ApiError(409, "customer_not_eligible", "Customer is not eligible for activation")
            if customer.get("riskLevel") == "HIGH":
                self._audit("ACTIVATION_BLOCKED_HIGH_RISK", activation_id, customer_id, "FAILED", trace_id)
                raise ApiError(409, "activation_blocked_high_risk", "Activation is blocked because the customer risk level is high")
            self._audit("ACTIVATION_CUSTOMER_VALIDATED", activation_id, customer_id, "SUCCESS", trace_id)

            offer = self.offer_client.get_offer(offer_id, trace_id=trace_id)
            if offer.get("status") != "ACTIVE":
                raise ApiError(409, "offer_inactive", "Offer is not active", {"offerId": offer_id})
            self._audit("ACTIVATION_OFFER_VALIDATED", activation_id, customer_id, "SUCCESS", trace_id)

            line = self.line_client.activate_line(
                {
                    "customerId": customer_id,
                    "offerId": offer_id,
                    "simType": payload["simType"],
                    "msisdn": payload.get("msisdn"),
                },
                trace_id=trace_id,
            )
            self._audit("ACTIVATION_LINE_ACTIVATED", activation_id, customer_id, "SUCCESS", trace_id, {"lineId": line["lineId"]})
        except ApiError as exc:
            self._audit("ACTIVATION_FAILED", activation_id, customer_id, "FAILED", trace_id, {"code": exc.code, "details": exc.details})
            raise

        response = {
            "activationId": activation_id,
            "status": "ACTIVE",
            "customerId": customer_id,
            "offerId": offer_id,
            "lineId": line["lineId"],
            "msisdn": line["msisdn"],
            "simType": line["simType"],
            "simIdentifier": line["simIdentifier"],
            "hlrStatus": line["hlrStatus"],
        }
        activation = Activation(
            activation_id=activation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            customer_id=customer_id,
            offer_id=offer_id,
            line_id=line["lineId"],
            status="ACTIVE",
            response_body=response,
            http_status=201,
        )
        self.activation_repository.create(activation)
        self._audit("ACTIVATION_COMPLETED", activation_id, customer_id, "SUCCESS", trace_id, {"lineId": line["lineId"]})
        return response, 201, False

    def _validate_payload(self, payload):
        if not payload.get("customerId"):
            raise ApiError(400, "validation_error", "customerId is required", {"field": "customerId"})
        if not payload.get("offerId"):
            raise ApiError(400, "validation_error", "offerId is required", {"field": "offerId"})
        if (payload.get("simType") or "").upper() not in {"SIM", "ESIM"}:
            raise ApiError(400, "validation_error", "simType must be SIM or ESIM", {"field": "simType"})
        payload["simType"] = payload["simType"].upper()

    def _hash_payload(self, payload):
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _response_from_existing(self, existing):
        body = existing["response_body"]
        return json.loads(body) if isinstance(body, str) else body

    def _audit(self, event_type, activation_id, customer_id, result, trace_id, metadata=None):
        if not self.audit_client:
            return
        self.audit_client.record(
            {
                "eventType": event_type,
                "actorId": customer_id,
                "customerId": customer_id,
                "resourceId": activation_id,
                "sourceService": "svc-commandes-activations",
                "result": result,
                "metadata": metadata or {},
            },
            trace_id=trace_id,
        )
