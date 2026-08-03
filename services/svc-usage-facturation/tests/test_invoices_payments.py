from datetime import date, datetime
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-usage-facturation"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from services.shared.errors import ApiError  # noqa: E402
from app.main import create_app  # noqa: E402


class Repository:
    def __init__(self):
        self.invoice = {
            "invoice_id": "inv-1",
            "customer_id": "cust-1",
            "billing_period": "2026-06",
            "amount_due": 49.99,
            "currency": "CAD",
            "status": "OPEN",
            "due_date": date(2026, 7, 15),
            "created_at": datetime(2026, 6, 1, 12, 0, 0),
        }
        self.payments_by_key = {}

    def list_invoices_by_customer(self, customer_id):
        return [self.invoice] if customer_id == self.invoice["customer_id"] else []

    def get_invoice(self, invoice_id):
        return self.invoice if invoice_id == self.invoice["invoice_id"] else None

    def find_payment_by_idempotency_key(self, key):
        return self.payments_by_key.get(key)

    def create_payment_and_mark_invoice_paid(self, payment):
        self.payments_by_key[payment.idempotency_key] = {
            "payment_id": payment.payment_id,
            "invoice_id": payment.invoice_id,
            "customer_id": payment.customer_id,
            "idempotency_key": payment.idempotency_key,
            "request_hash": payment.request_hash,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "status": payment.status,
            "response_body": payment.response_body,
            "http_status": payment.http_status,
        }
        self.invoice["status"] = "PAID"


class Customers:
    def __init__(self, exists=True):
        self.exists = exists

    def get_customer(self, customer_id, trace_id=None):
        if not self.exists:
            raise ApiError(404, "customer_not_found", "Customer not found")
        return {"customerId": customer_id, "status": "ACTIVE"}


class Gateway:
    def __init__(self, fail=False):
        self.fail = fail

    def charge(self, payment_request, trace_id=None):
        if self.fail:
            raise RuntimeError("down")
        return {"gatewayTransactionId": "txn-1", "status": "ACCEPTED"}


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event, trace_id=None):
        self.events.append((event, trace_id))


def make_app(repo=None, customers=None, gateway=None, audit=None):
    return create_app(
        repository=repo or Repository(),
        customer_client=customers or Customers(),
        payment_gateway=gateway or Gateway(),
        audit_client=audit or Audit(),
    )


def payment_payload(amount=49.99):
    return {"customerId": "cust-1", "paymentMethod": "SIMULATED_CARD", "amount": amount, "currency": "CAD"}


def test_get_invoices_by_customer_and_invoice_by_id():
    client = make_app().test_client()

    invoices = client.get("/v1/invoices?customerId=cust-1")
    invoice = client.get("/v1/invoices/inv-1")

    assert invoices.status_code == 200
    assert invoices.get_json()["invoices"][0]["invoiceId"] == "inv-1"
    assert invoice.status_code == 200
    assert invoice.get_json()["status"] == "OPEN"


def test_unknown_customer_for_invoices_returns_404():
    response = make_app(customers=Customers(exists=False)).test_client().get("/v1/invoices?customerId=missing")

    assert response.status_code == 404
    assert response.get_json()["code"] == "customer_not_found"


def test_successful_payment_and_idempotent_replay_and_audit():
    repo = Repository()
    audit = Audit()
    client = make_app(repo=repo, audit=audit).test_client()

    first = client.post("/v1/invoices/inv-1/payments", json=payment_payload(), headers={"Idempotency-Key": "pay-1"})
    second = client.post("/v1/invoices/inv-1/payments", json=payment_payload(), headers={"Idempotency-Key": "pay-1"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json() == second.get_json()
    assert second.headers["Idempotency-Replayed"] == "true"
    assert repo.invoice["status"] == "PAID"
    assert any(event[0]["eventType"] == "INVOICE_PAID" for event in audit.events)


def test_same_payment_key_different_payload_returns_conflict():
    client = make_app().test_client()
    client.post("/v1/invoices/inv-1/payments", json=payment_payload(), headers={"Idempotency-Key": "pay-conflict"})

    response = client.post("/v1/invoices/inv-1/payments", json=payment_payload(amount=40.00), headers={"Idempotency-Key": "pay-conflict"})

    assert response.status_code == 409
    assert response.get_json()["code"] == "idempotency_key_conflict"


def test_missing_idempotency_key_returns_400():
    response = make_app().test_client().post("/v1/invoices/inv-1/payments", json=payment_payload())

    assert response.status_code == 400
    assert response.get_json()["code"] == "missing_idempotency_key"


def test_unknown_invoice_returns_404():
    response = make_app().test_client().post(
        "/v1/invoices/missing/payments",
        json=payment_payload(),
        headers={"Idempotency-Key": "pay-missing"},
    )

    assert response.status_code == 404
    assert response.get_json()["code"] == "invoice_not_found"


def test_invoice_already_paid_returns_409_with_new_key():
    repo = Repository()
    repo.invoice["status"] = "PAID"
    response = make_app(repo=repo).test_client().post(
        "/v1/invoices/inv-1/payments",
        json=payment_payload(),
        headers={"Idempotency-Key": "pay-paid"},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "invoice_already_paid"


def test_payment_gateway_failure_returns_503_and_audits():
    audit = Audit()
    response = make_app(gateway=Gateway(fail=True), audit=audit).test_client().post(
        "/v1/invoices/inv-1/payments",
        json=payment_payload(),
        headers={"Idempotency-Key": "pay-fail"},
    )

    assert response.status_code == 503
    assert response.get_json()["code"] == "payment_gateway_unavailable"
    assert any(event[0]["eventType"] == "PAYMENT_FAILED" for event in audit.events)
