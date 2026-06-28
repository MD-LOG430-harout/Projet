import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-clients-identite"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.main import create_app


class Customers:
    def find_by_id(self, customer_id):
        if customer_id == "cust-1":
            return {
                "customer_id": "cust-1",
                "email": "valid@example.test",
                "display_name": "Valid Customer",
                "legal_name": "Valid Customer",
                "address_line1": "123 Rue Exemple",
                "city": "Montreal",
                "province": "QC",
                "postal_code": "H1A1A1",
                "identity_document_type": "driver_license",
                "identity_document_hash": "hash-only",
                "customer_type": "individual",
                "status": "ACTIVE",
                "identity_status": "VERIFIED",
                "risk_level": "LOW",
                "failed_login_attempts": 0,
                "locked_until": None,
                "last_login_risk": None,
            }
        return None

    def find_by_email(self, email):
        return None

    def create(self, customer):
        pass

    def set_password_hash(self, customer_id, password_hash):
        pass


class Mfa:
    def create(self, challenge):
        pass

    def find_by_id(self, challenge_id):
        return None

    def mark_verified(self, challenge_id):
        pass


def test_customer_validation_endpoint_returns_status_for_activation_slice():
    app = create_app(Customers(), Mfa(), None)
    client = app.test_client()

    response = client.get("/v1/customers/cust-1")

    assert response.status_code == 200
    assert response.get_json()["identityStatus"] == "VERIFIED"


def test_customer_validation_endpoint_returns_404_for_unknown_customer():
    app = create_app(Customers(), Mfa(), None)
    client = app.test_client()

    response = client.get("/v1/customers/missing")

    assert response.status_code == 404
    assert response.get_json()["code"] == "customer_not_found"
