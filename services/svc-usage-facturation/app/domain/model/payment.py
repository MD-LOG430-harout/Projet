from dataclasses import dataclass


@dataclass(frozen=True)
class Payment:
    payment_id: str
    invoice_id: str
    customer_id: str
    idempotency_key: str
    request_hash: str
    amount: float
    currency: str
    payment_method: str
    status: str
    response_body: dict
    http_status: int
    failure_reason: str | None = None
