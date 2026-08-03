import os
import threading

from app.adapters.inbound.kafka.audit_event_consumer import AuditEventConsumer, build_consumer, build_dlq_publisher
from app.application.handlers.audit_event_handler import AuditEventHandler


def start_event_runtime(connection_factory):
    if os.getenv("AUDIT_EVENT_RUNTIME_ENABLED", "false").lower() != "true":
        return []
    consumer = AuditEventConsumer(build_consumer(), AuditEventHandler(connection_factory), build_dlq_publisher())
    thread = threading.Thread(target=consumer.run_forever, name="audit-event-consumer", daemon=True)
    thread.start()
    return [thread]
