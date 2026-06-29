from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    offer_id: str
    order_type: str
    status: str
    orchestration_status: str
    confirmation_status: str
    total_amount: float
    currency: str
    idempotency_key: str
    request_hash: str
    response_body: dict
    http_status: int = 201
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
