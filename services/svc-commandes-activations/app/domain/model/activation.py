from dataclasses import dataclass


@dataclass(frozen=True)
class Activation:
    activation_id: str
    idempotency_key: str
    request_hash: str
    customer_id: str
    offer_id: str
    line_id: str | None
    status: str
    response_body: dict
    http_status: int
    failure_reason: str | None = None
