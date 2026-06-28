from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MfaChallenge:
    challenge_id: str
    customer_id: str
    otp_hash: str
    status: str
    expires_at: datetime

