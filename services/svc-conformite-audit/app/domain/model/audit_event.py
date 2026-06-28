from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuditEvent:
    audit_event_id: str
    event_type: str
    actor_id: str | None
    customer_id: str | None
    resource_id: str | None
    trace_id: str | None
    source_service: str
    result: str
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

