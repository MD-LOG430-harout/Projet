from datetime import datetime, timezone

from services.shared.errors import ApiError
from services.shared.security import verify_secret


class VerifyMfa:
    def __init__(self, mfa_repository, customer_repository, audit_client=None):
        self.mfa_repository = mfa_repository
        self.customer_repository = customer_repository
        self.audit_client = audit_client

    def execute(self, payload, trace_id=None):
        challenge_id = payload.get("challengeId")
        otp = payload.get("otp") or ""
        challenge = self.mfa_repository.find_by_id(challenge_id)
        if not challenge:
            raise ApiError(404, "mfa_challenge_not_found", "MFA challenge not found")
        if challenge["status"] != "PENDING":
            raise ApiError(409, "mfa_already_used", "MFA challenge is no longer pending")
        if challenge["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            self._audit("MFA_EXPIRED", challenge["customer_id"], "FAILED", trace_id)
            raise ApiError(422, "mfa_expired", "MFA challenge expired")
        if not verify_secret(otp, challenge["otp_hash"]):
            self._audit("MFA_FAILED", challenge["customer_id"], "FAILED", trace_id)
            raise ApiError(401, "mfa_invalid", "Invalid MFA code")

        self.mfa_repository.mark_verified(challenge_id)
        customer = self.customer_repository.find_by_id(challenge["customer_id"])
        self._audit("MFA_VERIFIED", challenge["customer_id"], "SUCCESS", trace_id)
        return {
            "authenticated": True,
            "customerId": challenge["customer_id"],
            "sessionToken": f"dev-session-{challenge_id}",
            "customerStatus": customer["status"],
        }

    def _audit(self, event_type, customer_id, result, trace_id):
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
                "metadata": {},
            },
            trace_id=trace_id,
        )
