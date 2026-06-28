from flask import Blueprint, current_app, g, jsonify, request

from app.application.commands.record_audit_event import RecordAuditEvent
from services.shared.errors import ApiError


bp = Blueprint("conformite_audit", __name__)


@bp.post("/v1/audit-events")
def record_audit_event():
    use_case = RecordAuditEvent(current_app.config["audit_repository"])
    event = use_case.execute(request.get_json(silent=True) or {}, trace_id=g.trace_id)
    return jsonify(
        {
            "auditEventId": event.audit_event_id,
            "eventType": event.event_type,
            "traceId": event.trace_id,
            "sourceService": event.source_service,
            "result": event.result,
            "createdAt": event.created_at.isoformat(),
        }
    ), 201


@bp.get("/v1/audit-events")
def list_audit_events():
    trace_id = request.args.get("traceId")
    if not trace_id:
        raise ApiError(400, "validation_error", "traceId query parameter is required", {"field": "traceId"})
    events = current_app.config["audit_repository"].list_by_trace_id(trace_id)
    return jsonify({"traceId": trace_id, "events": events})


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-conformite-audit"})
