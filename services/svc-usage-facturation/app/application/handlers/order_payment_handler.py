from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from services.shared.events import EventEnvelope
from services.shared.outbox import MysqlOutboxRepository, run_in_transaction
from services.shared.processed_events import DuplicateEvent, MysqlProcessedEventRepository


class OrderPaymentHandler:
    def __init__(self, connection_factory, gateway, processed_events=None, outbox=None):
        self.connection_factory = connection_factory
        self.gateway = gateway
        self.processed_events = processed_events or MysqlProcessedEventRepository()
        self.outbox = outbox or MysqlOutboxRepository()

    def handle(self, event):
        if event["eventType"] == "CommandePassee":
            return self._authorize(event)
        if event["eventType"] in {"ActivationEchouee", "CommandeAnnulee"}:
            return self._refund(event)
        raise ValueError(f"Unsupported payment event: {event['eventType']}")

    def _authorize(self, event):
        payment_id = str(uuid5(NAMESPACE_URL, f"cantelcox:payment:{event['payload']['idCommande']}"))
        prepared = run_in_transaction(
            self.connection_factory,
            lambda cursor: self._prepare_authorization(cursor, event, payment_id),
        )
        if prepared in {"TERMINAL", "DUPLICATE"}:
            return prepared
        result = self.gateway.authorize(
            {
                "paymentId": payment_id,
                "orderId": event["payload"]["idCommande"],
                "amount": event["payload"]["montant"],
                "currency": event["payload"]["devise"],
            },
            traceparent=event.get("traceparent"),
        )
        try:
            return run_in_transaction(
                self.connection_factory,
                lambda cursor: self._finish_authorization(cursor, event, payment_id, result),
            )
        except DuplicateEvent:
            return "DUPLICATE"

    def _prepare_authorization(self, cursor, event, payment_id):
        cursor.execute("SELECT status FROM order_saga_payments WHERE order_id=%s FOR UPDATE", (event["payload"]["idCommande"],))
        row = cursor.fetchone()
        if row and row["status"] in {"AUTORISE", "REFUSE", "REMBOURSE"}:
            return "TERMINAL"
        if not row:
            cursor.execute(
                """
                INSERT INTO order_saga_payments
                  (payment_id, order_id, saga_id, amount, currency, status, authorization_event_id)
                VALUES (%s,%s,%s,%s,%s,'EN_ATTENTE',%s)
                """,
                (payment_id, event["payload"]["idCommande"], event["sagaId"], event["payload"]["montant"], event["payload"]["devise"], event["eventId"]),
            )
        return "READY"

    def _finish_authorization(self, cursor, event, payment_id, gateway_result):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        cursor.execute("SELECT * FROM order_saga_payments WHERE payment_id=%s FOR UPDATE", (payment_id,))
        payment = cursor.fetchone()
        if payment["status"] != "EN_ATTENTE":
            return "TERMINAL"
        now = _now()
        authorized = gateway_result["status"] == "AUTHORIZED"
        event_type = "PaiementAutorise" if authorized else "PaiementRefuse"
        if authorized:
            payload = {
                "idPaiement": payment_id,
                "idCommande": payment["order_id"],
                "montant": float(payment["amount"]),
                "devise": payment["currency"],
                "authorizationId": gateway_result["authorizationId"],
                "authorizedAt": now,
                "idClient": event["payload"]["idClient"],
                "idOffre": event["payload"]["idOffre"],
                "numberMode": event["payload"].get("numberMode", "NEW"),
            }
            for field in ("msisdnDemande", "currentOperator"):
                if event["payload"].get(field):
                    payload[field] = event["payload"][field]
            status = "AUTORISE"
        else:
            payload = {
                "idPaiement": payment_id,
                "idCommande": payment["order_id"],
                "reasonCode": gateway_result.get("reasonCode") or "DECLINED",
                "reasonMessage": "Payment authorization refused",
                "refusedAt": now,
            }
            status = "REFUSE"
        resulting = self._event(event, event_type, payment_id, payload)
        cursor.execute(
            "UPDATE order_saga_payments SET status=%s, authorization_id=%s, updated_at=UTC_TIMESTAMP(6) WHERE payment_id=%s AND status='EN_ATTENTE'",
            (status, gateway_result.get("authorizationId"), payment_id),
        )
        self.outbox.insert(cursor, resulting)
        return "APPLIED"

    def _refund(self, event):
        order_id = event["payload"]["idCommande"]
        payment = run_in_transaction(self.connection_factory, lambda cursor: self._load_payment(cursor, order_id))
        if not payment or payment["status"] != "AUTORISE":
            try:
                return run_in_transaction(self.connection_factory, lambda cursor: self._record_noop(cursor, event))
            except DuplicateEvent:
                return "DUPLICATE"
        result = self.gateway.refund(
            {"paymentId": payment["payment_id"], "authorizationId": payment["authorization_id"], "amount": float(payment["amount"])},
            traceparent=event.get("traceparent"),
        )
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._finish_refund(cursor, event, payment, result))
        except DuplicateEvent:
            return "DUPLICATE"

    def _load_payment(self, cursor, order_id):
        cursor.execute("SELECT * FROM order_saga_payments WHERE order_id=%s", (order_id,))
        return cursor.fetchone()

    def _record_noop(self, cursor, event):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        return "NOOP"

    def _finish_refund(self, cursor, event, payment, result):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        cursor.execute("SELECT status FROM order_saga_payments WHERE payment_id=%s FOR UPDATE", (payment["payment_id"],))
        if cursor.fetchone()["status"] != "AUTORISE":
            return "NOOP"
        payload = {
            "idPaiement": payment["payment_id"],
            "idCommande": payment["order_id"],
            "refundId": result["refundId"],
            "montant": float(payment["amount"]),
            "refundedAt": _now(),
        }
        resulting = self._event(event, "PaiementRembourse", payment["payment_id"], payload)
        cursor.execute(
            "UPDATE order_saga_payments SET status='REMBOURSE', refund_id=%s, updated_at=UTC_TIMESTAMP(6) WHERE payment_id=%s AND status='AUTORISE'",
            (result["refundId"], payment["payment_id"]),
        )
        self.outbox.insert(cursor, resulting)
        return "APPLIED"

    def _event(self, source, event_type, payment_id, payload):
        return EventEnvelope.create(
            event_type=event_type,
            aggregate_id=payment_id,
            aggregate_type="Paiement",
            payload=payload,
            trace_id=source["traceId"],
            correlation_id=source["correlationId"],
            saga_id=source["sagaId"],
            causation_id=source["eventId"],
        )


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
