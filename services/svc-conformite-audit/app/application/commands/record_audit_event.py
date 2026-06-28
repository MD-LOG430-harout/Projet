import uuid

from services.shared.errors import ApiError

from app.domain.model.audit_event import AuditEvent


class RecordAuditEvent:
    def __init__(self, audit_repository):
        self.audit_repository = audit_repository

    def execute(self, payload, trace_id=None):
        event_type = payload.get("eventType")
        source_service = payload.get("sourceService")
        result = payload.get("result")
        if not event_type:
            raise ApiError(400, "validation_error", "eventType is required", {"field": "eventType"})
        if not source_service:
            raise ApiError(400, "validation_error", "sourceService is required", {"field": "sourceService"})
        if not result:
            raise ApiError(400, "validation_error", "result is required", {"field": "result"})

        event = AuditEvent(
            audit_event_id=str(uuid.uuid4()),
            event_type=event_type,
            actor_id=payload.get("actorId"),
            customer_id=payload.get("customerId"),
            resource_id=payload.get("resourceId"),
            trace_id=payload.get("traceId") or trace_id,
            source_service=source_service,
            result=result,
            metadata=payload.get("metadata") or {},
        )
        self.audit_repository.append(event)
        return event

