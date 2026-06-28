import json
from datetime import timezone

from app.domain.repositories.audit_repository import AuditRepository


class MysqlAuditRepository(AuditRepository):
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def append(self, event):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events
                    (audit_event_id, event_type, actor_id, customer_id, resource_id,
                     trace_id, source_service, result, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.audit_event_id,
                        event.event_type,
                        event.actor_id,
                        event.customer_id,
                        event.resource_id,
                        event.trace_id,
                        event.source_service,
                        event.result,
                        json.dumps(event.metadata),
                        event.created_at.replace(tzinfo=None),
                    ),
                )
            conn.commit()

    def list_by_trace_id(self, trace_id):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT audit_event_id, event_type, actor_id, customer_id, resource_id,
                           trace_id, source_service, result, metadata, created_at
                    FROM audit_events
                    WHERE trace_id=%s
                    ORDER BY created_at ASC
                    """,
                    (trace_id,),
                )
                rows = cursor.fetchall()
        return [_audit_event_public(row) for row in rows]


def _audit_event_public(row):
    created_at = row.get("created_at")
    if hasattr(created_at, "replace") and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return {
        "auditEventId": row.get("audit_event_id"),
        "eventType": row.get("event_type"),
        "actorId": row.get("actor_id"),
        "customerId": row.get("customer_id"),
        "resourceId": row.get("resource_id"),
        "traceId": row.get("trace_id"),
        "sourceService": row.get("source_service"),
        "result": row.get("result"),
        "metadata": metadata,
        "createdAt": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }
