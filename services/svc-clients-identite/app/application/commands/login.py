import uuid
from datetime import datetime, timedelta, timezone

from services.shared.errors import ApiError
from services.shared.security import hash_secret, verify_secret

from app.domain.model.mfa_challenge import MfaChallenge


class Login:
    def __init__(self, customer_repository, mfa_repository, audit_client=None):
        self.customer_repository = customer_repository
        self.mfa_repository = mfa_repository
        self.audit_client = audit_client

    def execute(self, payload, trace_id=None):
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        risk_signals = payload.get("riskSignals") or {}
        customer = self.customer_repository.find_by_email(email)
        if not customer or not verify_secret(password, customer["password_hash"]):
            if customer:
                lock_until = self._lock_until_if_threshold_reached(customer)
                if hasattr(self.customer_repository, "record_failed_login"):
                    self.customer_repository.record_failed_login(customer["customer_id"], lock_until=lock_until)
                if lock_until:
                    self._audit("LOGIN_LOCKED", customer["customer_id"], "FAILED", trace_id, {"lockedUntil": lock_until.isoformat()})
            self._audit("LOGIN_FAILED", customer["customer_id"] if customer else None, "FAILED", trace_id)
            raise ApiError(401, "invalid_credentials", "Invalid credentials")
        if customer["status"] != "ACTIVE":
            raise ApiError(403, "customer_not_active", "Customer account is not active")
        locked_until = customer.get("locked_until")
        if locked_until and locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            self._audit("LOGIN_BLOCKED_LOCKED", customer["customer_id"], "FAILED", trace_id)
            raise ApiError(423, "customer_temporarily_locked", "Customer account is temporarily locked")

        login_risk = self._evaluate_login_risk(customer, risk_signals)
        if hasattr(self.customer_repository, "reset_failed_logins"):
            self.customer_repository.reset_failed_logins(customer["customer_id"])
        if hasattr(self.customer_repository, "record_login_risk"):
            self.customer_repository.record_login_risk(customer["customer_id"], login_risk)

        otp = "123456"
        challenge = MfaChallenge(
            challenge_id=str(uuid.uuid4()),
            customer_id=customer["customer_id"],
            otp_hash=hash_secret(otp),
            status="PENDING",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        self.mfa_repository.create(challenge)
        self._audit(
            "LOGIN_MFA_REQUIRED",
            customer["customer_id"],
            "PENDING",
            trace_id,
            {"loginRisk": login_risk, "mfaStrength": "STEP_UP" if login_risk == "HIGH" else "STANDARD"},
        )
        return {
            "challengeId": challenge.challenge_id,
            "mfaRequired": True,
            "mfaStrength": "STEP_UP" if login_risk == "HIGH" else "STANDARD",
            "loginRisk": login_risk,
            "devOtp": otp,
        }

    def _lock_until_if_threshold_reached(self, customer):
        failed_attempts = int(customer.get("failed_login_attempts") or 0) + 1
        if failed_attempts >= 3:
            return datetime.now(timezone.utc) + timedelta(minutes=15)
        return None

    def _evaluate_login_risk(self, customer, risk_signals):
        high_risk_customer = customer.get("risk_level") == "HIGH"
        repeated_failures = int(customer.get("failed_login_attempts") or 0) >= 2
        risky_context = any(
            bool(risk_signals.get(name))
            for name in ("newDevice", "roaming", "unusualLocation", "simSwapRecent")
        )
        return "HIGH" if high_risk_customer or repeated_failures or risky_context else "LOW"

    def _audit(self, event_type, customer_id, result, trace_id, metadata=None):
        if not self.audit_client:
            return
        self.audit_client.record(
            {
                "eventType": event_type,
                "actorId": customer_id,
                "customerId": customer_id,
                "resourceId": customer_id,
                "sourceService": "svc-clients-identite",
                "result": result,
                "metadata": metadata or {},
            },
            trace_id=trace_id,
        )
