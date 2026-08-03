import os
import pathlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pymysql
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "svc-lignes-services"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.application.handlers.line_saga_handler import LineSagaHandler  # noqa: E402
from app.application.handlers.portability_webhook_handler import PortabilityTimeoutScanner, PortabilityWebhookHandler  # noqa: E402
from services.shared.events import EventEnvelope  # noqa: E402


def connect():
    return pymysql.connect(
        host=os.getenv("PHASE2_MYSQL_HOST", "127.0.0.1"), user="cantelcox",
        password=os.getenv("MYSQL_PASSWORD", "cantelcox_dev"), database="lignes_services",
        autocommit=False, cursorclass=pymysql.cursors.DictCursor,
    )


def available():
    try:
        connect().close()
        return True
    except pymysql.MySQLError:
        return False


pytestmark = pytest.mark.skipif(not available(), reason="Phase 2 MySQL unavailable")


class Hlr:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    def provision(self, line, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("HLR failed")
        return {"hlrReference": line.supi, "created": True}


class Hub:
    def __init__(self):
        self.calls = 0

    def initiate(self, **kwargs):
        self.calls += 1
        return {"orderId": f"PORT-{uuid4()}", "status": "pending_out_validation"}


def payment_event(number_mode="NEW"):
    order_id, saga_id = str(uuid4()), str(uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {"idPaiement": str(uuid4()), "idCommande": order_id, "montant": 49.99, "devise": "CAD", "authorizationId": "auth", "authorizedAt": now, "idClient": str(uuid4()), "idOffre": "offer-1", "numberMode": number_mode}
    if number_mode == "PORT_IN":
        payload.update({"msisdnDemande": f"15{uuid4().int % 10_000_000_000:010d}", "currentOperator": "BSS2"})
    return EventEnvelope.create(event_type="PaiementAutorise", aggregate_id=payload["idPaiement"], aggregate_type="Paiement", payload=payload, trace_id="2" * 32, correlation_id=order_id, saga_id=saga_id, causation_id=str(uuid4())).to_dict()


def test_direct_activation_and_failure_are_domain_events():
    event = payment_event()
    handler = LineSagaHandler(connect, Hlr(), Hub())
    assert handler.handle(event) == "APPLIED"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM service_lines WHERE line_id=(SELECT line_id FROM line_saga_state WHERE order_id=%s)", (event["payload"]["idCommande"],))
            assert cursor.fetchone()["status"] == "ACTIVE"

    failed = payment_event()
    assert LineSagaHandler(connect, Hlr(fail=True), Hub()).handle(failed) == "APPLIED"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT event_type FROM outbox_events WHERE aggregate_id=(SELECT line_id FROM line_saga_state WHERE order_id=%s)", (failed["payload"]["idCommande"],))
            assert "ActivationEchouee" in [row["event_type"] for row in cursor.fetchall()]


def test_portability_initiation_and_terminal_webhooks_are_idempotent():
    source = payment_event("PORT_IN")
    hlr, hub = Hlr(), Hub()
    assert LineSagaHandler(connect, hlr, hub).handle(source) == "APPLIED"
    assert hub.calls == 1
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM portability_correlations WHERE id_commande=%s", (source["payload"]["idCommande"],))
            correlation = cursor.fetchone()

    notification = {
        "eventId": f"PORT-EVT-{uuid4()}", "eventType": "PortabilityOrderStateChangeEvent",
        "eventTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": {"portabilityOrder": {"id": correlation["hub_order_id"], "number": correlation["msisdn"], "status": "approved"}},
    }
    webhook = PortabilityWebhookHandler(connect, hlr)
    assert webhook.handle(notification) == "APPLIED"
    completed = {**notification, "eventId": f"PORT-EVT-{uuid4()}", "event": {"portabilityOrder": {**notification["event"]["portabilityOrder"], "status": "port_completed"}}}
    assert webhook.handle(completed) == "APPLIED"
    assert webhook.handle(completed) == "DUPLICATE"
    late = {**notification, "eventId": f"PORT-EVT-{uuid4()}", "event": {"portabilityOrder": {**notification["event"]["portabilityOrder"], "status": "rejected"}}}
    assert webhook.handle(late) == "LATE_IGNORED"

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM service_lines WHERE line_id=%s", (correlation["id_ligne"],))
            assert cursor.fetchone()["status"] == "ACTIVE"
            cursor.execute("SELECT event_type,COUNT(*) AS n FROM outbox_events WHERE aggregate_id IN (%s,%s) GROUP BY event_type", (correlation["id_ligne"], correlation["portability_id"]))
            counts = {row["event_type"]: row["n"] for row in cursor.fetchall()}
            assert counts["NumeroPorte"] == 1
            assert counts["LigneActivee"] == 1


@pytest.mark.parametrize("terminal_status", ["rejected", "cancelled"])
def test_portability_failure_callbacks_map_to_internal_failure(terminal_status):
    source = payment_event("PORT_IN")
    assert LineSagaHandler(connect, Hlr(), Hub()).handle(source) == "APPLIED"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM portability_correlations WHERE id_commande=%s", (source["payload"]["idCommande"],))
            correlation = cursor.fetchone()
    notification = {
        "eventId": f"PORT-EVT-{uuid4()}", "eventType": "PortabilityOrderStateChangeEvent",
        "eventTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": {"portabilityOrder": {"id": correlation["hub_order_id"], "number": correlation["msisdn"], "status": terminal_status, "rejectionReason": "test"}},
    }
    assert PortabilityWebhookHandler(connect, Hlr()).handle(notification) == "APPLIED"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM portability_correlations WHERE portability_id=%s", (correlation["portability_id"],))
            assert cursor.fetchone()["status"] == terminal_status
            cursor.execute("SELECT COUNT(*) AS n FROM outbox_events WHERE aggregate_id=%s AND event_type='PortabiliteEchouee'", (correlation["portability_id"],))
            assert cursor.fetchone()["n"] == 1


def test_internal_portability_timeout_emits_failure_without_external_expired_status():
    source = payment_event("PORT_IN")
    assert LineSagaHandler(connect, Hlr(), Hub()).handle(source) == "APPLIED"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE portability_correlations SET deadline_at=UTC_TIMESTAMP(6) WHERE id_commande=%s", (source["payload"]["idCommande"],))
        connection.commit()
    assert PortabilityTimeoutScanner(connect).scan() == 1
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status,portability_id FROM portability_correlations WHERE id_commande=%s", (source["payload"]["idCommande"],))
            row = cursor.fetchone()
            assert row["status"] == "TIMED_OUT"
            cursor.execute("SELECT payload FROM outbox_events WHERE aggregate_id=%s AND event_type='PortabiliteEchouee' ORDER BY id DESC LIMIT 1", (row["portability_id"],))
            payload = cursor.fetchone()["payload"]
            import json
            document = json.loads(payload) if isinstance(payload, str) else payload
            assert document["payload"]["reasonCode"] == "PORTABILITY_TIMEOUT"
