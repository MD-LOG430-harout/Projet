import json

from services.shared.outbox import run_in_transaction
from services.shared.processed_events import DuplicateEvent, MysqlProcessedEventRepository


PORTABILITY_FIELDS = (
    "hubOrderId", "portabilityId", "portId", "idCommande", "idLigne",
    "msisdn", "previousOperator", "portedAt",
)


class AuditEventHandler:
    def __init__(self, connection_factory, processed_events=None):
        self.connection_factory = connection_factory
        self.processed_events = processed_events or MysqlProcessedEventRepository()

    def handle(self, event):
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._apply(cursor, event))
        except DuplicateEvent:
            return "DUPLICATE"

    def _apply(self, cursor, event):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        payload = event["payload"]
        portability = {field: payload[field] for field in PORTABILITY_FIELDS if field in payload}
        cursor.execute(
            """
            INSERT INTO audit_events
              (audit_event_id,event_id,event_type,occurred_at,aggregate_id,correlation_id,
               causation_id,saga_id,trace_id,source_service,result,metadata,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'RECORDED',%s,%s)
            """,
            (
                event["eventId"], event["eventId"], event["eventType"],
                event["occurredAt"].replace("T", " ").replace("Z", "")[:26],
                event["aggregateId"], event["correlationId"], event.get("causationId"),
                event["sagaId"], event["traceId"], "kafka",
                json.dumps(portability, separators=(",", ":")),
                event["occurredAt"].replace("T", " ").replace("Z", "")[:26],
            ),
        )
        return "APPLIED"
