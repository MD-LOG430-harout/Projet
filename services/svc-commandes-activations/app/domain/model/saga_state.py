from dataclasses import dataclass, field
from datetime import datetime, timezone


ACTIVE = "EN_COURS"
TERMINAL_STATES = frozenset({"CONFIRMEE", "ANNULEE"})


@dataclass(frozen=True)
class SagaState:
    saga_id: str
    order_id: str
    status: str
    deadline_at: datetime
    payment_status: str = "PENDING"
    line_status: str = "PENDING"
    portability_status: str = "NOT_REQUIRED"
    last_event_type: str = "CommandePassee"
    last_event_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATES
