from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from services.shared.events import EventEnvelope
from services.shared.outbox import MysqlOutboxRepository, run_in_transaction
from services.shared.processed_events import DuplicateEvent, MysqlProcessedEventRepository
from services.shared.tracing import traceparent_from_trace_id


class LineSagaHandler:
    def __init__(self, connection_factory, hlr_adapter, portability_adapter, processed_events=None, outbox=None):
        self.connection_factory = connection_factory
        self.hlr_adapter = hlr_adapter
        self.portability_adapter = portability_adapter
        self.processed_events = processed_events or MysqlProcessedEventRepository()
        self.outbox = outbox or MysqlOutboxRepository()

    def handle(self, event):
        if event["eventType"] == "PaiementAutorise":
            return self._activate(event)
        if event["eventType"] == "CommandeAnnulee":
            return self._release(event)
        raise ValueError(f"Unsupported line event: {event['eventType']}")

    def _activate(self, event):
        line = run_in_transaction(self.connection_factory, lambda cursor: self._reserve(cursor, event))
        if line["status"] in {"ACTIVE", "FAILED", "RELEASED", "PORTABILITY_PENDING"}:
            return "TERMINAL"
        if line["number_mode"] == "PORT_IN":
            return self._initiate_portability(event, line)
        try:
            result = self.hlr_adapter.provision(
                SimpleNamespace(**line),
                trace_id=event["traceId"],
                traceparent=traceparent_from_trace_id(event["traceId"]),
            )
        except Exception as exc:
            return self._finish_failure(event, line, getattr(exc, "code", "HLR_PROVISIONING_FAILED"), str(exc))
        return self._finish_activation(event, line, result["hlrReference"] if isinstance(result, dict) else line["supi"])

    def _reserve(self, cursor, event):
        order_id = event["payload"]["idCommande"]
        cursor.execute(
            """
            SELECT l.*, s.order_id, s.saga_id, s.number_mode, s.current_operator, s.status AS saga_status
            FROM line_saga_state s JOIN service_lines l ON l.line_id=s.line_id
            WHERE s.order_id=%s FOR UPDATE
            """,
            (order_id,),
        )
        existing = cursor.fetchone()
        if existing:
            existing["status"] = existing["saga_status"]
            return existing
        line_id = str(uuid5(NAMESPACE_URL, f"cantelcox:line:{order_id}"))
        imsi_digits = str(uuid5(NAMESPACE_URL, f"cantelcox:imsi:{order_id}").int)[:10]
        imsi = f"20893{imsi_digits}"
        number_mode = event["payload"].get("numberMode", "NEW")
        msisdn = event["payload"].get("msisdnDemande") or f"1438{str(uuid5(NAMESPACE_URL, order_id).int)[:7]}"
        sim_identifier = f"ICCID-{uuid5(NAMESPACE_URL, f'cantelcox:sim:{order_id}').hex[:18].upper()}"
        cursor.execute(
            """
            INSERT INTO service_lines
              (line_id,customer_id,offer_id,msisdn,sim_type,sim_identifier,imsi,supi,status,hlr_status,number_mode,portability_status)
            VALUES (%s,%s,%s,%s,'SIM',%s,%s,%s,'PENDING','PENDING',%s,%s)
            """,
            (line_id, event["payload"]["idClient"], event["payload"]["idOffre"], msisdn, sim_identifier, imsi, f"imsi-{imsi}", number_mode, "INITIATING" if number_mode == "PORT_IN" else None),
        )
        cursor.execute(
            """
            INSERT INTO line_saga_state
              (line_id,order_id,saga_id,customer_id,offer_id,number_mode,current_operator,status,source_event_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'RESERVED',%s)
            """,
            (line_id, order_id, event["sagaId"], event["payload"]["idClient"], event["payload"]["idOffre"], number_mode, event["payload"].get("currentOperator"), event["eventId"]),
        )
        return {
            "line_id": line_id, "order_id": order_id, "saga_id": event["sagaId"],
            "customer_id": event["payload"]["idClient"], "offer_id": event["payload"]["idOffre"],
            "msisdn": msisdn, "sim_type": "SIM", "sim_identifier": sim_identifier,
            "imsi": imsi, "supi": f"imsi-{imsi}", "status": "RESERVED", "hlr_status": "PENDING",
            "number_mode": number_mode, "current_operator": event["payload"].get("currentOperator"),
        }

    def _initiate_portability(self, event, line):
        if not line.get("current_operator"):
            return self._finish_portability_failure(event, line, "CURRENT_OPERATOR_MISSING", "Current operator is required")
        try:
            result = self.portability_adapter.initiate(
                customer_id=line["customer_id"],
                msisdn=line["msisdn"],
                current_operator=line["current_operator"],
                traceparent=traceparent_from_trace_id(event["traceId"]),
            )
        except Exception as exc:
            return self._finish_portability_failure(event, line, getattr(exc, "code", "PORTABILITY_INITIATION_FAILED"), str(exc))
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._persist_portability(cursor, event, line, result))
        except DuplicateEvent:
            return "DUPLICATE"

    def _persist_portability(self, cursor, event, line, result):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        portability_id = str(uuid5(NAMESPACE_URL, f"cantelcox:portability:{line['order_id']}"))
        deadline = datetime.now(timezone.utc) + timedelta(hours=48)
        cursor.execute(
            """
            INSERT INTO portability_correlations
              (portability_id,hub_order_id,id_ligne,id_commande,saga_id,idempotency_key,msisdn,current_operator,trace_id_initial,status,deadline_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE hub_order_id=COALESCE(hub_order_id,VALUES(hub_order_id))
            """,
            (portability_id, result["orderId"], line["line_id"], line["order_id"], event["sagaId"], f"port-{line['order_id']}", line["msisdn"], line["current_operator"], event["traceId"], result["status"], deadline.replace(tzinfo=None)),
        )
        cursor.execute("UPDATE line_saga_state SET status='PORTABILITY_PENDING' WHERE line_id=%s", (line["line_id"],))
        cursor.execute("UPDATE service_lines SET portability_status=%s WHERE line_id=%s", (result["status"], line["line_id"]))
        payload = {
            "idCommande": line["order_id"], "idLigne": line["line_id"], "portId": portability_id,
            "hubOrderId": result["orderId"], "msisdn": line["msisdn"], "currentOperator": line["current_operator"],
            "requestedAt": _now(), "expiresAt": deadline.isoformat().replace("+00:00", "Z"),
        }
        self.outbox.insert(cursor, self._event(event, "PortabiliteDemandee", portability_id, "Portabilite", payload))
        return "APPLIED"

    def _finish_activation(self, event, line, hlr_reference):
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._persist_activation(cursor, event, line, hlr_reference))
        except DuplicateEvent:
            return "DUPLICATE"

    def _persist_activation(self, cursor, event, line, hlr_reference):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        cursor.execute("SELECT status FROM line_saga_state WHERE line_id=%s FOR UPDATE", (line["line_id"],))
        if cursor.fetchone()["status"] != "RESERVED":
            return "TERMINAL"
        cursor.execute("UPDATE service_lines SET status='ACTIVE',hlr_status='PROVISIONED',failure_reason=NULL WHERE line_id=%s", (line["line_id"],))
        cursor.execute("UPDATE line_saga_state SET status='ACTIVE' WHERE line_id=%s", (line["line_id"],))
        payload = {"idLigne": line["line_id"], "idCommande": line["order_id"], "msisdn": line["msisdn"], "activationMode": line["number_mode"], "hlrReference": hlr_reference, "activatedAt": _now()}
        self.outbox.insert(cursor, self._event(event, "LigneActivee", line["line_id"], "Ligne", payload))
        return "APPLIED"

    def _finish_failure(self, event, line, code, message):
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._persist_failure(cursor, event, line, code, message))
        except DuplicateEvent:
            return "DUPLICATE"

    def _persist_failure(self, cursor, event, line, code, message):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        cursor.execute("UPDATE service_lines SET status='FAILED',hlr_status='FAILED',failure_reason=%s WHERE line_id=%s", (message[:255], line["line_id"]))
        cursor.execute("UPDATE line_saga_state SET status='FAILED' WHERE line_id=%s AND status NOT IN ('ACTIVE','RELEASED')", (line["line_id"],))
        payload = {"idLigne": line["line_id"], "idCommande": line["order_id"], "reasonCode": code, "reasonMessage": message, "attempts": 1, "failedAt": _now()}
        self.outbox.insert(cursor, self._event(event, "ActivationEchouee", line["line_id"], "Ligne", payload))
        return "APPLIED"

    def _finish_portability_failure(self, event, line, code, message):
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._persist_portability_failure(cursor, event, line, code, message))
        except DuplicateEvent:
            return "DUPLICATE"

    def _persist_portability_failure(self, cursor, event, line, code, message):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        portability_id = str(uuid5(NAMESPACE_URL, f"cantelcox:portability:{line['order_id']}"))
        cursor.execute("UPDATE service_lines SET status='FAILED',portability_status='FAILED',failure_reason=%s WHERE line_id=%s", (message[:255], line["line_id"]))
        cursor.execute("UPDATE line_saga_state SET status='FAILED' WHERE line_id=%s", (line["line_id"],))
        payload = {"idCommande": line["order_id"], "idLigne": line["line_id"], "portId": portability_id, "msisdn": line["msisdn"], "reasonCode": code, "reasonMessage": message, "failedAt": _now()}
        self.outbox.insert(cursor, self._event(event, "PortabiliteEchouee", portability_id, "Portabilite", payload))
        return "APPLIED"

    def _release(self, event):
        try:
            return run_in_transaction(self.connection_factory, lambda cursor: self._persist_release(cursor, event))
        except DuplicateEvent:
            return "DUPLICATE"

    def _persist_release(self, cursor, event):
        self.processed_events.reserve(cursor, event["eventId"], event["eventType"])
        cursor.execute("SELECT line_id,status FROM line_saga_state WHERE order_id=%s FOR UPDATE", (event["payload"]["idCommande"],))
        row = cursor.fetchone()
        if not row or row["status"] == "RELEASED":
            return "NOOP"
        cursor.execute("UPDATE line_saga_state SET status='RELEASED' WHERE line_id=%s", (row["line_id"],))
        cursor.execute("UPDATE service_lines SET status='RELEASED' WHERE line_id=%s", (row["line_id"],))
        return "APPLIED"

    def _event(self, source, event_type, aggregate_id, aggregate_type, payload):
        return EventEnvelope.create(event_type=event_type, aggregate_id=aggregate_id, aggregate_type=aggregate_type, payload=payload, trace_id=source["traceId"], correlation_id=source["correlationId"], saga_id=source["sagaId"], causation_id=source["eventId"])


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
