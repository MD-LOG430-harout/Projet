import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-conformite-audit"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.main import create_app  # noqa: E402


class AppendOnlyAuditRepo:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)

    def list_by_trace_id(self, trace_id):
        return [
            {
                "auditEventId": event.audit_event_id,
                "eventType": event.event_type,
                "actorId": event.actor_id,
                "customerId": event.customer_id,
                "resourceId": event.resource_id,
                "traceId": event.trace_id,
                "sourceService": event.source_service,
                "result": event.result,
                "metadata": event.metadata,
                "createdAt": event.created_at.isoformat(),
            }
            for event in self.events
            if event.trace_id == trace_id
        ]


def test_audit_events_are_appended_by_post_only():
    repo = AppendOnlyAuditRepo()
    app = create_app(repo)
    client = app.test_client()

    response = client.post(
        "/v1/audit-events",
        json={
            "eventType": "CUSTOMER_REGISTERED",
            "actorId": "cust-1",
            "customerId": "cust-1",
            "resourceId": "cust-1",
            "sourceService": "svc-clients-identite",
            "result": "SUCCESS",
            "metadata": {"riskLevel": "LOW"},
        },
        headers={"TraceId": "trace-audit"},
    )

    assert response.status_code == 201
    assert len(repo.events) == 1
    assert repo.events[0].trace_id == "trace-audit"

    assert client.put("/v1/audit-events").status_code == 405
    assert client.delete("/v1/audit-events").status_code == 405


def test_audit_events_can_be_listed_by_trace_id_for_demo_evidence():
    repo = AppendOnlyAuditRepo()
    app = create_app(repo)
    client = app.test_client()

    client.post(
        "/v1/audit-events",
        json={"eventType": "INVOICE_CONSULTED", "sourceService": "svc-usage-facturation", "result": "SUCCESS"},
        headers={"TraceId": "trace-demo"},
    )

    response = client.get("/v1/audit-events?traceId=trace-demo")

    assert response.status_code == 200
    assert response.get_json()["events"][0]["eventType"] == "INVOICE_CONSULTED"
