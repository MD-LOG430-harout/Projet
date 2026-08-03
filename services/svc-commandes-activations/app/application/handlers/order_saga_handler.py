from datetime import datetime, timezone

from services.shared.event_metrics import SAGA_DURATION, SAGA_TRANSITIONS
from services.shared.events import EventEnvelope
from services.shared.outbox import MysqlOutboxRepository, run_in_transaction
from services.shared.processed_events import DuplicateEvent, MysqlProcessedEventRepository


SERVICE_NAME = "svc-commandes-activations"


CANCELLATION_EVENTS = {
    "PaiementRefuse": "PAYMENT_REFUSED",
    "ActivationEchouee": "ACTIVATION_FAILED",
    "PortabiliteEchouee": "PORTABILITY_FAILED",
}


class OrderSagaHandler:
    def __init__(self, connection_factory, processed_events=None, outbox=None):
        self.connection_factory = connection_factory
        self.processed_events = processed_events or MysqlProcessedEventRepository()
        self.outbox = outbox or MysqlOutboxRepository()

    def handle(self, event):
        try:
            result = run_in_transaction(self.connection_factory, lambda cursor: self._apply(cursor, event))
        except DuplicateEvent:
            result = "DUPLICATE"
        # APPLIED advances the saga; DUPLICATE and LATE_IGNORED are the idempotency guards.
        SAGA_TRANSITIONS.labels(SERVICE_NAME, result).inc()
        return result

    def _apply(self, cursor, event):
        event_type = event["eventType"]
        self.processed_events.reserve(cursor, event["eventId"], event_type)
        order_id = event["payload"]["idCommande"]
        cursor.execute("SELECT * FROM orders WHERE order_id=%s FOR UPDATE", (order_id,))
        order = cursor.fetchone()
        if not order:
            raise LookupError(f"Order {order_id} does not exist")
        cursor.execute("SELECT * FROM saga_state WHERE order_id=%s FOR UPDATE", (order_id,))
        saga = cursor.fetchone()
        if not saga:
            raise LookupError(f"Saga for order {order_id} does not exist")

        if order["status"] in {"CONFIRMEE", "ANNULEE"}:
            return "LATE_IGNORED"

        if event_type == "PaiementAutorise":
            self._advance(cursor, saga["saga_id"], event, payment_status="AUTHORIZED")
            return "APPLIED"
        if event_type == "PaiementRembourse":
            self._advance(cursor, saga["saga_id"], event, payment_status="REFUNDED")
            return "APPLIED"
        if event_type == "NumeroPorte":
            self._advance(cursor, saga["saga_id"], event, portability_status="COMPLETED")
            return "APPLIED"
        if event_type == "LigneActivee":
            return self._terminate(cursor, order, saga, event, "CONFIRMEE")
        if event_type in CANCELLATION_EVENTS:
            return self._terminate(cursor, order, saga, event, "ANNULEE")
        raise ValueError(f"Unsupported order saga event: {event_type}")

    def _advance(self, cursor, saga_id, event, **fields):
        assignments = ["last_event_type=%s", "last_event_id=%s", "updated_at=UTC_TIMESTAMP(6)"]
        params = [event["eventType"], event["eventId"]]
        for name, value in fields.items():
            assignments.append(f"{name}=%s")
            params.append(value)
        params.append(saga_id)
        cursor.execute(f"UPDATE saga_state SET {', '.join(assignments)} WHERE saga_id=%s", params)

    def _terminate(self, cursor, order, saga, source_event, status):
        event_type = "CommandeConfirmee" if status == "CONFIRMEE" else "CommandeAnnulee"
        now = datetime.now(timezone.utc)
        if status == "CONFIRMEE":
            line_id = source_event["payload"]["idLigne"]
            payload = {
                "idCommande": order["order_id"],
                "idClient": order["customer_id"],
                "idLigne": line_id,
                "confirmedAt": now.isoformat().replace("+00:00", "Z"),
            }
            reason = None
        else:
            reason = CANCELLATION_EVENTS[source_event["eventType"]]
            payload = {
                "idCommande": order["order_id"],
                "reasonCode": reason,
                "reasonMessage": source_event["payload"].get("reasonMessage", ""),
                "cancelledAt": now.isoformat().replace("+00:00", "Z"),
                "compensationRequired": saga["payment_status"] == "AUTHORIZED",
            }
            line_id = source_event["payload"].get("idLigne")

        resulting_event = EventEnvelope.create(
            event_type=event_type,
            aggregate_id=order["order_id"],
            aggregate_type="Commande",
            payload=payload,
            trace_id=source_event["traceId"],
            correlation_id=source_event["correlationId"],
            saga_id=source_event["sagaId"],
            causation_id=source_event["eventId"],
        )
        cursor.execute(
            """
            UPDATE orders
            SET status=%s, orchestration_status=%s, confirmation_status=%s,
                line_id=COALESCE(%s, line_id), terminal_event_id=%s,
                terminal_reason=%s, updated_at=UTC_TIMESTAMP(6)
            WHERE order_id=%s AND status='EN_COURS'
            """,
            (status, status, status, line_id, source_event["eventId"], reason, order["order_id"]),
        )
        if cursor.rowcount != 1:
            return "LATE_IGNORED"
        cursor.execute(
            """
            UPDATE saga_state
            SET status=%s, line_status=%s, last_event_type=%s, last_event_id=%s,
                completed_at=UTC_TIMESTAMP(6), updated_at=UTC_TIMESTAMP(6)
            WHERE saga_id=%s AND status='EN_COURS'
            """,
            (status, "ACTIVE" if status == "CONFIRMEE" else "FAILED", source_event["eventType"], source_event["eventId"], saga["saga_id"]),
        )
        self.outbox.insert(cursor, resulting_event)
        self._observe_saga_duration(cursor, saga["saga_id"], status)
        return "APPLIED"

    def _observe_saga_duration(self, cursor, saga_id, status):
        """Time between order acceptance and the terminal state, measured by the database clock."""
        cursor.execute(
            "SELECT TIMESTAMPDIFF(MICROSECOND, created_at, completed_at) AS elapsed FROM saga_state WHERE saga_id=%s",
            (saga_id,),
        )
        row = cursor.fetchone()
        if row and row["elapsed"] is not None:
            SAGA_DURATION.labels(status).observe(float(row["elapsed"]) / 1_000_000)


class SagaTimeoutScanner:
    """Detect expired sagas without coordinating their compensation."""

    def __init__(self, order_repository):
        self.order_repository = order_repository

    def detect_expired(self, limit=100):
        return self.order_repository.find_expired_sagas(limit)
