from datetime import datetime, timedelta, timezone
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
from services.shared.security import hash_secret


class Customers:
    def __init__(self):
        self.customer = {
            "customer_id": "cust-1",
            "email": "mfa@example.test",
            "display_name": "MFA User",
            "customer_type": "individual",
            "status": "ACTIVE",
            "identity_status": "VERIFIED",
            "risk_level": "LOW",
            "password_hash": hash_secret("Stronger123"),
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_risk": None,
        }

    def create(self, customer):
        pass

    def set_password_hash(self, customer_id, password_hash):
        pass

    def record_failed_login(self, customer_id, lock_until=None):
        self.customer["failed_login_attempts"] += 1
        self.customer["locked_until"] = lock_until.replace(tzinfo=None) if lock_until else None

    def reset_failed_logins(self, customer_id):
        self.customer["failed_login_attempts"] = 0
        self.customer["locked_until"] = None

    def record_login_risk(self, customer_id, risk_level):
        self.customer["last_login_risk"] = risk_level

    def find_by_email(self, email):
        return self.customer if email == self.customer["email"] else None

    def find_by_id(self, customer_id):
        return self.customer if customer_id == self.customer["customer_id"] else None


class MfaRepo:
    def __init__(self):
        self.challenges = {}

    def create(self, challenge):
        self.challenges[challenge.challenge_id] = {
            "challenge_id": challenge.challenge_id,
            "customer_id": challenge.customer_id,
            "otp_hash": challenge.otp_hash,
            "status": challenge.status,
            "expires_at": challenge.expires_at.replace(tzinfo=None),
        }

    def find_by_id(self, challenge_id):
        return self.challenges.get(challenge_id)

    def mark_verified(self, challenge_id):
        self.challenges[challenge_id]["status"] = "VERIFIED"


class AuditSpy:
    def __init__(self):
        self.events = []

    def record(self, event, trace_id=None):
        self.events.append((event, trace_id))


def test_login_creates_mfa_challenge_and_verify_mfa_authenticates():
    mfa = MfaRepo()
    app = create_app(Customers(), mfa, None)
    client = app.test_client()

    login = client.post("/v1/auth/login", json={"email": "mfa@example.test", "password": "Stronger123"})
    assert login.status_code == 202
    challenge_id = login.get_json()["challengeId"]

    verified = client.post("/v1/auth/mfa/verify", json={"challengeId": challenge_id, "otp": "123456"})

    assert verified.status_code == 200
    assert verified.get_json()["authenticated"] is True
    assert verified.get_json()["sessionToken"] == f"dev-session-{challenge_id}"
    assert mfa.challenges[challenge_id]["status"] == "VERIFIED"

    introspected = client.get(
        "/v1/auth/introspect",
        headers={"Authorization": f"Bearer dev-session-{challenge_id}"},
    )

    assert introspected.status_code == 204


def test_mfa_rejects_invalid_otp():
    mfa = MfaRepo()
    challenge_id = "challenge-invalid"
    mfa.challenges[challenge_id] = {
        "challenge_id": challenge_id,
        "customer_id": "cust-1",
        "otp_hash": hash_secret("123456"),
        "status": "PENDING",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(tzinfo=None),
    }
    app = create_app(Customers(), mfa, None)
    client = app.test_client()

    response = client.post("/v1/auth/mfa/verify", json={"challengeId": challenge_id, "otp": "000000"})

    assert response.status_code == 401
    assert response.get_json()["code"] == "mfa_invalid"


def test_introspect_rejects_missing_or_unverified_token():
    mfa = MfaRepo()
    challenge_id = "challenge-pending"
    mfa.challenges[challenge_id] = {
        "challenge_id": challenge_id,
        "customer_id": "cust-1",
        "otp_hash": hash_secret("123456"),
        "status": "PENDING",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(tzinfo=None),
    }
    app = create_app(Customers(), mfa, None)
    client = app.test_client()

    missing = client.get("/v1/auth/introspect")
    pending = client.get(
        "/v1/auth/introspect",
        headers={"Authorization": f"Bearer dev-session-{challenge_id}"},
    )

    assert missing.status_code == 401
    assert missing.get_json()["code"] == "missing_token"
    assert pending.status_code == 401
    assert pending.get_json()["code"] == "invalid_token"


def test_login_locks_customer_after_three_failed_attempts_and_audits_lockout():
    customers = Customers()
    audit = AuditSpy()
    app = create_app(customers, MfaRepo(), audit)
    client = app.test_client()

    for _ in range(3):
        response = client.post("/v1/auth/login", json={"email": "mfa@example.test", "password": "WrongPass123"})
        assert response.status_code == 401

    assert customers.customer["failed_login_attempts"] == 3
    assert customers.customer["locked_until"] is not None
    assert any(event[0]["eventType"] == "LOGIN_LOCKED" for event in audit.events)


def test_login_marks_high_risk_context_as_step_up_mfa():
    customers = Customers()
    app = create_app(customers, MfaRepo(), None)
    client = app.test_client()

    response = client.post(
        "/v1/auth/login",
        json={
            "email": "mfa@example.test",
            "password": "Stronger123",
            "riskSignals": {"newDevice": True},
        },
    )

    assert response.status_code == 202
    assert response.get_json()["loginRisk"] == "HIGH"
    assert response.get_json()["mfaStrength"] == "STEP_UP"
    assert customers.customer["last_login_risk"] == "HIGH"


def test_expired_mfa_is_rejected_and_audited():
    audit = AuditSpy()
    mfa = MfaRepo()
    challenge_id = "challenge-expired"
    mfa.challenges[challenge_id] = {
        "challenge_id": challenge_id,
        "customer_id": "cust-1",
        "otp_hash": hash_secret("123456"),
        "status": "PENDING",
        "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(tzinfo=None),
    }
    app = create_app(Customers(), mfa, audit)
    client = app.test_client()

    response = client.post("/v1/auth/mfa/verify", json={"challengeId": challenge_id, "otp": "123456"})

    assert response.status_code == 422
    assert response.get_json()["code"] == "mfa_expired"
    assert any(event[0]["eventType"] == "MFA_EXPIRED" for event in audit.events)
