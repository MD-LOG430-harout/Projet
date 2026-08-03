import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-commandes-activations"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from services.shared.errors import ApiError  # noqa: E402
from app.main import create_app  # noqa: E402


class Activations:
    def __init__(self):
        self.by_key = {}

    def create(self, activation):
        self.by_key[activation.idempotency_key] = {
            "activation_id": activation.activation_id,
            "idempotency_key": activation.idempotency_key,
            "request_hash": activation.request_hash,
            "customer_id": activation.customer_id,
            "offer_id": activation.offer_id,
            "line_id": activation.line_id,
            "status": activation.status,
            "response_body": activation.response_body,
            "http_status": activation.http_status,
            "failure_reason": activation.failure_reason,
        }

    def find_by_idempotency_key(self, key):
        return self.by_key.get(key)


class Customers:
    def __init__(self, exists=True, risk_level="LOW"):
        self.exists = exists
        self.risk_level = risk_level

    def get_customer(self, customer_id, trace_id=None):
        if not self.exists:
            raise ApiError(404, "customer_not_found", "Customer not found")
        return {"customerId": customer_id, "status": "ACTIVE", "identityStatus": "VERIFIED", "riskLevel": self.risk_level}


class Offers:
    def __init__(self, exists=True, active=True):
        self.exists = exists
        self.active = active

    def get_offer(self, offer_id, trace_id=None):
        if not self.exists:
            raise ApiError(404, "offer_not_found", "Offer not found")
        return {"offerId": offer_id, "status": "ACTIVE" if self.active else "INACTIVE"}


class Lines:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    def activate_line(self, payload, trace_id=None):
        self.calls += 1
        if self.fail:
            raise ApiError(503, "hlr_provisioning_failed", "HLR/free5GC provisioning failed")
        return {
            "lineId": "line-1",
            "msisdn": payload.get("msisdn") or "14385550123",
            "simType": payload["simType"],
            "simIdentifier": "ICCID-1",
            "hlrStatus": "PROVISIONED",
            "numberMode": payload.get("numberMode", "NEW"),
            "portabilityStatus": "ACCEPTED" if payload.get("numberMode") == "PORT_IN" else None,
        }


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event, trace_id=None):
        self.events.append((event, trace_id))


def make_app(repo=None, customers=None, offers=None, lines=None, audit=None):
    return create_app(
        repo or Activations(),
        customers or Customers(),
        offers or Offers(),
        lines or Lines(),
        audit or Audit(),
    )


def test_successful_activation_and_idempotent_replay():
    repo = Activations()
    lines = Lines()
    app = make_app(repo=repo, lines=lines)
    client = app.test_client()
    payload = {"customerId": "cust-1", "offerId": "forfait-5g-20gb", "simType": "SIM"}

    first = client.post("/v1/activations", json=payload, headers={"Idempotency-Key": "key-1"})
    second = client.post("/v1/activations", json=payload, headers={"Idempotency-Key": "key-1"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json() == second.get_json()
    assert lines.calls == 1
    assert second.headers["Idempotency-Replayed"] == "true"


def test_activation_supports_simulated_portability_with_existing_msisdn():
    app = make_app()
    client = app.test_client()
    payload = {
        "customerId": "cust-1",
        "offerId": "forfait-5g-20gb",
        "simType": "ESIM",
        "numberMode": "PORT_IN",
        "msisdn": "14385551234",
    }

    response = client.post("/v1/activations", json=payload, headers={"Idempotency-Key": "key-port-in"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["msisdn"] == "14385551234"
    assert body["numberMode"] == "PORT_IN"
    assert body["portabilityStatus"] == "ACCEPTED"


def test_activation_requires_msisdn_for_simulated_portability():
    response = make_app().test_client().post(
        "/v1/activations",
        json={
            "customerId": "cust-1",
            "offerId": "forfait-5g-20gb",
            "simType": "ESIM",
            "numberMode": "PORT_IN",
        },
        headers={"Idempotency-Key": "key-port-missing"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == "validation_error"
    assert body["details"]["field"] == "msisdn"


def test_missing_idempotency_key_returns_400():
    response = make_app().test_client().post(
        "/v1/activations",
        json={"customerId": "cust-1", "offerId": "forfait-5g-20gb", "simType": "SIM"},
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "missing_idempotency_key"


def test_unknown_customer_returns_404():
    response = make_app(customers=Customers(exists=False)).test_client().post(
        "/v1/activations",
        json={"customerId": "missing", "offerId": "forfait-5g-20gb", "simType": "SIM"},
        headers={"Idempotency-Key": "key-customer"},
    )

    assert response.status_code == 404
    assert response.get_json()["code"] == "customer_not_found"


def test_unknown_offer_returns_404():
    response = make_app(offers=Offers(exists=False)).test_client().post(
        "/v1/activations",
        json={"customerId": "cust-1", "offerId": "missing", "simType": "SIM"},
        headers={"Idempotency-Key": "key-offer"},
    )

    assert response.status_code == 404
    assert response.get_json()["code"] == "offer_not_found"


def test_inactive_offer_returns_409():
    response = make_app(offers=Offers(active=False)).test_client().post(
        "/v1/activations",
        json={"customerId": "cust-1", "offerId": "forfait-retired-10gb", "simType": "SIM"},
        headers={"Idempotency-Key": "key-inactive"},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "offer_inactive"


def test_hlr_failure_returns_503_and_audits_failure():
    audit = Audit()
    response = make_app(lines=Lines(fail=True), audit=audit).test_client().post(
        "/v1/activations",
        json={"customerId": "cust-1", "offerId": "forfait-5g-20gb", "simType": "ESIM"},
        headers={"Idempotency-Key": "key-hlr"},
    )

    assert response.status_code == 503
    assert response.get_json()["code"] == "hlr_provisioning_failed"
    assert any(event[0]["eventType"] == "ACTIVATION_FAILED" for event in audit.events)


def test_high_risk_customer_blocks_activation_and_audits_decision():
    audit = Audit()
    response = make_app(customers=Customers(risk_level="HIGH"), audit=audit).test_client().post(
        "/v1/activations",
        json={"customerId": "cust-1", "offerId": "forfait-5g-20gb", "simType": "ESIM"},
        headers={"Idempotency-Key": "key-risk"},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "activation_blocked_high_risk"
    assert any(event[0]["eventType"] == "ACTIVATION_BLOCKED_HIGH_RISK" for event in audit.events)
