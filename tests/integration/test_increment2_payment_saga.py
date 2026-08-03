import os
import pathlib
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pymysql
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "svc-usage-facturation"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.adapters.outbound.payment.simulated_payment_gateway import SimulatedPaymentGateway  # noqa: E402
from app.application.handlers.order_payment_handler import OrderPaymentHandler  # noqa: E402
from services.shared.events import EventEnvelope  # noqa: E402


def connect():
    return pymysql.connect(
        host=os.getenv("PHASE2_MYSQL_HOST", "127.0.0.1"), user="cantelcox",
        password=os.getenv("MYSQL_PASSWORD", "cantelcox_dev"), database="usage_facturation",
        autocommit=False, cursorclass=pymysql.cursors.DictCursor,
    )


def available():
    try:
        connect().close()
        return True
    except pymysql.MySQLError:
        return False


pytestmark = pytest.mark.skipif(not available(), reason="Phase 2 MySQL unavailable")


def event(event_type, order_id, saga_id, causation_id=None):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if event_type == "CommandePassee":
        payload = {"idCommande": order_id, "idClient": str(uuid4()), "idOffre": "offer-1", "montant": 49.99, "devise": "CAD", "numberMode": "NEW"}
        aggregate_type = "Commande"
    else:
        payload = {"idCommande": order_id, "reasonCode": "FAILED", "reasonMessage": "failure", "cancelledAt": now, "compensationRequired": True}
        aggregate_type = "Commande"
    return EventEnvelope.create(
        event_type=event_type, aggregate_id=order_id, aggregate_type=aggregate_type,
        payload=payload, trace_id="1" * 32, correlation_id=order_id, saga_id=saga_id,
        causation_id=causation_id,
    ).to_dict()


def test_authorize_duplicate_refund_and_duplicate_compensation():
    order_id, saga_id = str(uuid4()), str(uuid4())
    gateway = SimulatedPaymentGateway()
    handler = OrderPaymentHandler(connect, gateway)
    created = event("CommandePassee", order_id, saga_id)

    assert handler.handle(created) == "APPLIED"
    assert handler.handle(created) in {"TERMINAL", "DUPLICATE"}
    cancelled = event("CommandeAnnulee", order_id, saga_id, str(uuid4()))
    assert handler.handle(cancelled) == "APPLIED"
    assert handler.handle(cancelled) == "DUPLICATE"

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM order_saga_payments WHERE order_id=%s", (order_id,))
            assert cursor.fetchone()["status"] == "REMBOURSE"
            cursor.execute("SELECT event_type,COUNT(*) AS n FROM outbox_events WHERE aggregate_id=(SELECT payment_id FROM order_saga_payments WHERE order_id=%s) GROUP BY event_type", (order_id,))
            counts = {row["event_type"]: row["n"] for row in cursor.fetchall()}
            assert counts["PaiementAutorise"] == 1
            assert counts["PaiementRembourse"] == 1


def test_refusal_never_also_authorizes():
    order_id, saga_id = str(uuid4()), str(uuid4())
    handler = OrderPaymentHandler(connect, SimulatedPaymentGateway(force_refusal=True))
    assert handler.handle(event("CommandePassee", order_id, saga_id)) == "APPLIED"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status,payment_id FROM order_saga_payments WHERE order_id=%s", (order_id,))
            row = cursor.fetchone()
            assert row["status"] == "REFUSE"
            cursor.execute("SELECT event_type FROM outbox_events WHERE aggregate_id=%s", (row["payment_id"],))
            assert [item["event_type"] for item in cursor.fetchall()] == ["PaiementRefuse"]
