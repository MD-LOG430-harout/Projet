import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-commandes-activations"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from services.shared.errors import ApiError
from app.main import create_app


class Activations:
    def create(self, activation):
        raise AssertionError("UC-05 must not trigger activation")

    def find_by_idempotency_key(self, key):
        return None


class Orders:
    def __init__(self):
        self.by_key = {}

    def create_order(self, order):
        self.by_key[order.idempotency_key] = {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "offer_id": order.offer_id,
            "order_type": order.order_type,
            "status": order.status,
            "orchestration_status": order.orchestration_status,
            "confirmation_status": order.confirmation_status,
            "total_amount": order.total_amount,
            "currency": order.currency,
            "idempotency_key": order.idempotency_key,
            "request_hash": order.request_hash,
            "response_body": order.response_body,
            "http_status": order.http_status,
        }

    def find_order_by_idempotency_key(self, key):
        return self.by_key.get(key)


class Customers:
    def __init__(self, exists=True, risk_level="LOW", status="ACTIVE", identity_status="VERIFIED"):
        self.exists = exists
        self.risk_level = risk_level
        self.status = status
        self.identity_status = identity_status

    def get_customer(self, customer_id, trace_id=None):
        if not self.exists:
            raise ApiError(404, "customer_not_found", "Customer not found")
        return {
            "customerId": customer_id,
            "status": self.status,
            "identityStatus": self.identity_status,
            "riskLevel": self.risk_level,
        }


class Offers:
    def __init__(self, exists=True, active=True):
        self.exists = exists
        self.active = active

    def get_offer(self, offer_id, trace_id=None):
        if not self.exists:
            raise ApiError(404, "offer_not_found", "Offer not found")
        return {
            "offerId": offer_id,
            "status": "ACTIVE" if self.active else "INACTIVE",
            "monthlyPrice": 49.99,
            "currency": "CAD",
        }


class Lines:
    def activate_line(self, payload, trace_id=None):
        raise AssertionError("UC-05 must not activate a line")


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event, trace_id=None):
        self.events.append((event, trace_id))


def make_app(repo=None, customers=None, offers=None, audit=None):
    return create_app(
        activation_repository=Activations(),
        customer_client=customers or Customers(),
        offer_client=offers or Offers(),
        line_client=Lines(),
        audit_client=audit or Audit(),
        order_repository=repo or Orders(),
    )


def order_payload(offer_id="forfait-5g-20gb", quantity=1):
    return {
        "customerId": "cust-1",
        "offerId": offer_id,
        "quantity": quantity,
        "orderType": "NEW_PLAN",
    }


def test_successful_order_creation_and_audit():
    audit = Audit()
    response = make_app(audit=audit).test_client().post(
        "/v1/orders",
        json=order_payload(),
        headers={"Idempotency-Key": "order-1", "TraceId": "trace-order"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "ACCEPTED"
    assert body["orchestrationStatus"] == "READY_FOR_ACTIVATION"
    assert body["confirmationStatus"] == "SIMULATED_SENT"
    assert body["totalAmount"] == 49.99
    assert body["currency"] == "CAD"
    assert any(event[0]["eventType"] == "ORDER_RISK_CHECKED" for event in audit.events)
    assert any(event[0]["eventType"] == "ORDER_ACCEPTED" for event in audit.events)
    assert any(event[0]["eventType"] == "ORDER_CONFIRMATION_SIMULATED" for event in audit.events)


def test_idempotent_order_replay_returns_same_order():
    repo = Orders()
    client = make_app(repo=repo).test_client()

    first = client.post("/v1/orders", json=order_payload(), headers={"Idempotency-Key": "order-replay"})
    second = client.post("/v1/orders", json=order_payload(), headers={"Idempotency-Key": "order-replay"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json() == second.get_json()
    assert second.headers["Idempotency-Replayed"] == "true"
    assert len(repo.by_key) == 1


def test_same_order_key_with_different_payload_returns_conflict():
    client = make_app().test_client()
    client.post("/v1/orders", json=order_payload(), headers={"Idempotency-Key": "order-conflict"})

    response = client.post("/v1/orders", json=order_payload(quantity=2), headers={"Idempotency-Key": "order-conflict"})

    assert response.status_code == 409
    assert response.get_json()["code"] == "idempotency_key_conflict"


def test_missing_order_idempotency_key_returns_400():
    response = make_app().test_client().post("/v1/orders", json=order_payload())

    assert response.status_code == 400
    assert response.get_json()["code"] == "missing_idempotency_key"


def test_unknown_customer_returns_404_for_order():
    response = make_app(customers=Customers(exists=False)).test_client().post(
        "/v1/orders",
        json=order_payload(),
        headers={"Idempotency-Key": "order-customer"},
    )

    assert response.status_code == 404
    assert response.get_json()["code"] == "customer_not_found"


def test_ineligible_customer_returns_403_and_audits():
    audit = Audit()
    response = make_app(customers=Customers(status="PENDING"), audit=audit).test_client().post(
        "/v1/orders",
        json=order_payload(),
        headers={"Idempotency-Key": "order-ineligible"},
    )

    assert response.status_code == 403
    assert response.get_json()["code"] == "customer_not_eligible"
    assert any(event[0]["eventType"] == "ORDER_ELIGIBILITY_FAILED" for event in audit.events)


def test_unknown_offer_returns_404_for_order():
    response = make_app(offers=Offers(exists=False)).test_client().post(
        "/v1/orders",
        json=order_payload("missing"),
        headers={"Idempotency-Key": "order-offer"},
    )

    assert response.status_code == 404
    assert response.get_json()["code"] == "offer_not_found"


def test_inactive_offer_returns_409_for_order():
    response = make_app(offers=Offers(active=False)).test_client().post(
        "/v1/orders",
        json=order_payload("forfait-retired-10gb"),
        headers={"Idempotency-Key": "order-inactive"},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "offer_inactive"


def test_high_risk_customer_blocks_order_and_audits():
    audit = Audit()
    response = make_app(customers=Customers(risk_level="HIGH"), audit=audit).test_client().post(
        "/v1/orders",
        json=order_payload(),
        headers={"Idempotency-Key": "order-risk"},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "order_blocked_high_risk"
    assert any(event[0]["eventType"] == "ORDER_RISK_CHECKED" for event in audit.events)
    assert any(event[0]["eventType"] == "ORDER_BLOCKED_RISK" for event in audit.events)


def test_change_plan_requires_line_id_as_phase1_compatibility_check():
    audit = Audit()
    payload = order_payload()
    payload["orderType"] = "CHANGE_PLAN"
    response = make_app(audit=audit).test_client().post(
        "/v1/orders",
        json=payload,
        headers={"Idempotency-Key": "order-change-plan"},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "order_incompatible"
    assert any(event[0]["eventType"] == "ORDER_COMPATIBILITY_FAILED" for event in audit.events)
