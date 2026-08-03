import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-clients-identite"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.main import create_app  # noqa: E402


class InMemoryCustomers:
    def __init__(self):
        self.by_id = {}
        self.by_email = {}

    def create(self, customer):
        self.by_id[customer.customer_id] = {
            "customer_id": customer.customer_id,
            "email": customer.email,
            "display_name": customer.display_name,
            "legal_name": customer.legal_name,
            "address_line1": customer.address_line1,
            "city": customer.city,
            "province": customer.province,
            "postal_code": customer.postal_code,
            "identity_document_type": customer.identity_document_type,
            "identity_document_hash": customer.identity_document_hash,
            "customer_type": customer.customer_type,
            "status": customer.status,
            "identity_status": customer.identity_status,
            "risk_level": customer.risk_level,
            "password_hash": None,
        }
        self.by_email[customer.email] = self.by_id[customer.customer_id]

    def set_password_hash(self, customer_id, password_hash):
        self.by_id[customer_id]["password_hash"] = password_hash

    def find_by_email(self, email):
        return self.by_email.get(email)

    def find_by_id(self, customer_id):
        return self.by_id.get(customer_id)


class InMemoryMfa:
    def create(self, challenge):
        pass

    def find_by_id(self, challenge_id):
        return None

    def mark_verified(self, challenge_id):
        pass


class AuditSpy:
    def __init__(self):
        self.events = []

    def record(self, event, trace_id=None):
        self.events.append((event, trace_id))


def test_register_customer_creates_active_verified_customer_and_audit_event():
    customers = InMemoryCustomers()
    audit = AuditSpy()
    app = create_app(customers, InMemoryMfa(), audit)
    client = app.test_client()

    response = client.post(
        "/v1/customers/register",
        json={
            "email": "alice@example.test",
            "password": "Stronger123",
            "displayName": "Alice Test",
            "legalName": "Alice Test",
            "address": {
                "line1": "123 Rue Exemple",
                "city": "Montreal",
                "province": "QC",
                "postalCode": "H1A1A1",
            },
            "identityDocument": {
                "type": "driver_license",
                "number": "SIM-QC-123456",
            },
            "customerType": "individual",
        },
        headers={"TraceId": "trace-register"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["customerId"]
    assert body["status"] == "ACTIVE"
    assert body["identityStatus"] == "VERIFIED"
    assert body["legalName"] == "Alice Test"
    assert body["address"]["province"] == "QC"
    assert body["identityDocument"]["type"] == "driver_license"
    assert body["identityDocument"]["verified"] is True
    assert customers.by_id[body["customerId"]]["identity_document_hash"] != "SIM-QC-123456"
    assert len(audit.events) == 1
    assert audit.events[0][0]["eventType"] == "CUSTOMER_REGISTERED"
    assert audit.events[0][1] == "trace-register"


def test_register_rejects_duplicate_email():
    customers = InMemoryCustomers()
    app = create_app(customers, InMemoryMfa(), None)
    client = app.test_client()
    payload = {
        "email": "dupe@example.test",
        "password": "Stronger123",
        "displayName": "Dupe",
        "legalName": "Dupe Customer",
        "address": {
            "line1": "456 Rue Test",
            "city": "Quebec",
            "province": "QC",
            "postalCode": "G1A1A1",
        },
        "identityDocument": {
            "type": "passport",
            "number": "SIM-PASS-123456",
        },
    }

    assert client.post("/v1/customers/register", json=payload).status_code == 201
    response = client.post("/v1/customers/register", json=payload)

    assert response.status_code == 409
    assert response.get_json()["code"] == "customer_exists"


def test_register_requires_simulated_identity_document_and_address():
    app = create_app(InMemoryCustomers(), InMemoryMfa(), None)
    client = app.test_client()

    response = client.post(
        "/v1/customers/register",
        json={
            "email": "missing-id@example.test",
            "password": "Stronger123",
            "displayName": "Missing Identity",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "validation_error"
