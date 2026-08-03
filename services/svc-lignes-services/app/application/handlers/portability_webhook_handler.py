from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from services.shared.events import EventEnvelope
from services.shared.outbox import MysqlOutboxRepository, run_in_transaction
from services.shared.tracing import traceparent_from_trace_id


class UnknownHubOrder(LookupError):
    pass


class InvalidWebhook(ValueError):
    pass


class PortabilityWebhookHandler:
    STATUSES = {"pending_out_validation", "approved", "rejected", "port_completed", "cancelled"}
    TERMINAL = {"rejected", "port_completed", "cancelled", "TIMED_OUT", "FAILED"}

    def __init__(self, connection_factory, hlr_adapter, outbox=None):
        self.connection_factory = connection_factory
        self.hlr_adapter = hlr_adapter
        self.outbox = outbox or MysqlOutboxRepository()

    def handle(self, notification):
        event_id, order = self._validate(notification)
        correlation = run_in_transaction(
            self.connection_factory,
            lambda cursor: self._load(cursor, order["id"]),
        )
        if not correlation:
            raise UnknownHubOrder(order["id"])
        if order.get("number") and order["number"] != correlation["msisdn"]:
            raise InvalidWebhook("callback MSISDN does not match the correlated order")
        status = order["status"]
        if status == "port_completed":
            line = run_in_transaction(self.connection_factory, lambda cursor: self._load_line(cursor, correlation["id_ligne"]))
            try:
                result = self.hlr_adapter.provision(
                    SimpleNamespace(**line),
                    trace_id=correlation["trace_id_initial"],
                    traceparent=traceparent_from_trace_id(correlation["trace_id_initial"]),
                )
            except Exception as exc:
                return run_in_transaction(
                    self.connection_factory,
                    lambda cursor, error=exc: self._apply_failure(cursor, notification, event_id, order, correlation, getattr(error, "code", "HLR_PROVISIONING_FAILED"), str(error)),
                )
            return run_in_transaction(
                self.connection_factory,
                lambda cursor: self._apply_completed(cursor, notification, event_id, order, correlation, result),
            )
        return run_in_transaction(
            self.connection_factory,
            lambda cursor: self._apply_status(cursor, notification, event_id, order, correlation),
        )

    def _validate(self, notification):
        if notification.get("eventType") not in {
            "PortabilityOrderOutValidationNeededEvent",
            "PortabilityOrderStateChangeEvent",
        }:
            raise InvalidWebhook("unsupported EventNotification eventType")
        event_id = notification.get("eventId")
        order = ((notification.get("event") or {}).get("portabilityOrder") or {})
        if not event_id or not order.get("id") or order.get("status") not in self.STATUSES:
            raise InvalidWebhook("invalid EventNotification payload")
        return event_id, order

    def _load(self, cursor, hub_order_id):
        cursor.execute("SELECT * FROM portability_correlations WHERE hub_order_id=%s", (hub_order_id,))
        return cursor.fetchone()

    def _load_line(self, cursor, line_id):
        cursor.execute("SELECT * FROM service_lines WHERE line_id=%s", (line_id,))
        return cursor.fetchone()

    def _reserve_callback(self, cursor, event_id, order):
        cursor.execute(
            "INSERT IGNORE INTO portability_webhook_events(event_id,hub_order_id,hub_status) VALUES (%s,%s,%s)",
            (event_id, order["id"], order["status"]),
        )
        return cursor.rowcount == 1

    def _lock_correlation(self, cursor, hub_order_id):
        cursor.execute("SELECT * FROM portability_correlations WHERE hub_order_id=%s FOR UPDATE", (hub_order_id,))
        return cursor.fetchone()

    def _apply_status(self, cursor, notification, event_id, order, correlation):
        if not self._reserve_callback(cursor, event_id, order):
            return "DUPLICATE"
        current = self._lock_correlation(cursor, order["id"])
        if current["status"] in self.TERMINAL:
            return "LATE_IGNORED"
        status = order["status"]
        cursor.execute("UPDATE portability_correlations SET status=%s WHERE hub_order_id=%s", (status, order["id"]))
        cursor.execute("UPDATE service_lines SET portability_status=%s WHERE line_id=%s", (status, correlation["id_ligne"]))
        if status in {"rejected", "cancelled"}:
            cursor.execute("UPDATE line_saga_state SET status='FAILED' WHERE line_id=%s", (correlation["id_ligne"],))
            cursor.execute("UPDATE service_lines SET status='FAILED',failure_reason=%s WHERE line_id=%s", (order.get("rejectionReason") or status, correlation["id_ligne"]))
            self.outbox.insert(cursor, self._failure_event(notification, event_id, order, correlation, status.upper(), order.get("rejectionReason") or status))
        return "APPLIED"

    def _apply_completed(self, cursor, notification, event_id, order, correlation, hlr_result):
        if not self._reserve_callback(cursor, event_id, order):
            return "DUPLICATE"
        current = self._lock_correlation(cursor, order["id"])
        if current["status"] in self.TERMINAL:
            return "LATE_IGNORED"
        cursor.execute("UPDATE portability_correlations SET status='port_completed' WHERE hub_order_id=%s", (order["id"],))
        cursor.execute("UPDATE line_saga_state SET status='ACTIVE' WHERE line_id=%s", (correlation["id_ligne"],))
        cursor.execute("UPDATE service_lines SET status='ACTIVE',hlr_status='PROVISIONED',portability_status='port_completed',failure_reason=NULL WHERE line_id=%s", (correlation["id_ligne"],))
        source = self._source(notification, event_id, correlation)
        ported_at = notification.get("timeOccurred") or notification.get("eventTime") or _now()
        port_payload = {
            "idCommande": correlation["id_commande"], "idLigne": correlation["id_ligne"],
            "portId": correlation["portability_id"], "hubOrderId": correlation["hub_order_id"],
            "msisdn": correlation["msisdn"], "portedAt": ported_at,
            "previousOperator": correlation["current_operator"],
        }
        line_payload = {
            "idLigne": correlation["id_ligne"], "idCommande": correlation["id_commande"],
            "msisdn": correlation["msisdn"], "activationMode": "PORT_IN",
            "hlrReference": hlr_result.get("hlrReference", correlation["id_ligne"]), "activatedAt": _now(),
        }
        self.outbox.insert(cursor, self._event(source, "NumeroPorte", correlation["portability_id"], "Portabilite", port_payload))
        self.outbox.insert(cursor, self._event(source, "LigneActivee", correlation["id_ligne"], "Ligne", line_payload))
        return "APPLIED"

    def _apply_failure(self, cursor, notification, event_id, order, correlation, code, message):
        if not self._reserve_callback(cursor, event_id, order):
            return "DUPLICATE"
        self._lock_correlation(cursor, order["id"])
        cursor.execute("UPDATE portability_correlations SET status='FAILED' WHERE hub_order_id=%s", (order["id"],))
        cursor.execute("UPDATE line_saga_state SET status='FAILED' WHERE line_id=%s", (correlation["id_ligne"],))
        cursor.execute("UPDATE service_lines SET status='FAILED',hlr_status='FAILED',failure_reason=%s WHERE line_id=%s", (message[:255], correlation["id_ligne"]))
        self.outbox.insert(cursor, self._failure_event(notification, event_id, order, correlation, code, message))
        return "APPLIED"

    def _failure_event(self, notification, event_id, order, correlation, code, message):
        payload = {
            "idCommande": correlation["id_commande"], "idLigne": correlation["id_ligne"],
            "portId": correlation["portability_id"], "hubOrderId": correlation["hub_order_id"],
            "msisdn": correlation["msisdn"], "reasonCode": code, "reasonMessage": message,
            "failedAt": notification.get("timeOccurred") or notification.get("eventTime") or _now(),
        }
        if order["status"] in {"rejected", "cancelled"}:
            payload["hubStatus"] = order["status"]
        return self._event(self._source(notification, event_id, correlation), "PortabiliteEchouee", correlation["portability_id"], "Portabilite", payload)

    def _source(self, notification, event_id, correlation):
        return {
            "eventId": str(uuid5(NAMESPACE_URL, f"portabilityhub:{event_id}")),
            "traceId": correlation["trace_id_initial"],
            "correlationId": correlation["id_commande"],
            "sagaId": correlation["saga_id"],
        }

    def _event(self, source, event_type, aggregate_id, aggregate_type, payload):
        return EventEnvelope.create(event_type=event_type, aggregate_id=aggregate_id, aggregate_type=aggregate_type, payload=payload, trace_id=source["traceId"], correlation_id=source["correlationId"], saga_id=source["sagaId"], causation_id=source["eventId"])


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PortabilityTimeoutScanner:
    def __init__(self, connection_factory, outbox=None):
        self.connection_factory = connection_factory
        self.outbox = outbox or MysqlOutboxRepository()

    def scan(self, limit=100):
        return run_in_transaction(self.connection_factory, lambda cursor: self._scan(cursor, limit))

    def _scan(self, cursor, limit):
        cursor.execute(
            f"SELECT * FROM portability_correlations WHERE status IN ('pending_out_validation','approved') AND deadline_at<=UTC_TIMESTAMP(6) ORDER BY deadline_at LIMIT {int(limit)} FOR UPDATE SKIP LOCKED"
        )
        rows = cursor.fetchall()
        for row in rows:
            cursor.execute("UPDATE portability_correlations SET status='TIMED_OUT' WHERE portability_id=%s", (row["portability_id"],))
            source_id = str(uuid5(NAMESPACE_URL, f"cantelcox:portability-timeout:{row['portability_id']}"))
            payload = {"idCommande": row["id_commande"], "idLigne": row["id_ligne"], "portId": row["portability_id"], "hubOrderId": row["hub_order_id"], "msisdn": row["msisdn"], "reasonCode": "PORTABILITY_TIMEOUT", "reasonMessage": "Internal portability deadline expired", "failedAt": _now()}
            event = EventEnvelope.create(event_type="PortabiliteEchouee", aggregate_id=row["portability_id"], aggregate_type="Portabilite", payload=payload, trace_id=row["trace_id_initial"], correlation_id=row["id_commande"], saga_id=row["saga_id"], causation_id=source_id)
            self.outbox.insert(cursor, event)
        return len(rows)
