import os
import pathlib
import sys
from uuid import uuid4

import pymysql
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "svc-conformite-audit"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.application.handlers.audit_event_handler import AuditEventHandler  # noqa: E402
from services.shared.events import EventEnvelope  # noqa: E402


def connect():
    return pymysql.connect(
        host=os.getenv("PHASE2_MYSQL_HOST", "127.0.0.1"), user="cantelcox",
        password=os.getenv("MYSQL_PASSWORD", "cantelcox_dev"), database="conformite_audit",
        autocommit=False, cursorclass=pymysql.cursors.DictCursor,
    )


def available():
    try:
        connect().close()
        return True
    except pymysql.MySQLError:
        return False


pytestmark = pytest.mark.skipif(not available(), reason="Phase 2 MySQL unavailable")


def test_internal_event_is_appended_once_with_original_identifiers():
    order_id, saga_id = str(uuid4()), str(uuid4())
    event = EventEnvelope.create(
        event_type="CommandePassee", aggregate_id=order_id, aggregate_type="Commande",
        payload={"idCommande": order_id, "idClient": "client", "idOffre": "offer", "montant": 49.99, "devise": "CAD"},
        trace_id="3" * 32, correlation_id=order_id, saga_id=saga_id,
    ).to_dict()
    handler = AuditEventHandler(connect)
    assert handler.handle(event) == "APPLIED"
    assert handler.handle(event) == "DUPLICATE"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT event_id,event_type,aggregate_id,correlation_id,saga_id,trace_id FROM audit_events WHERE event_id=%s", (event["eventId"],))
            row = cursor.fetchone()
            assert row == {
                "event_id": event["eventId"], "event_type": "CommandePassee",
                "aggregate_id": order_id, "correlation_id": order_id,
                "saga_id": saga_id, "trace_id": "3" * 32,
            }


def test_database_rejects_update_and_delete_of_audit_fact():
    order_id, saga_id = str(uuid4()), str(uuid4())
    event = EventEnvelope.create(
        event_type="CommandePassee", aggregate_id=order_id, aggregate_type="Commande",
        payload={"idCommande": order_id, "idClient": "client", "idOffre": "offer", "montant": 1, "devise": "CAD"},
        trace_id="4" * 32, correlation_id=order_id, saga_id=saga_id,
    ).to_dict()
    AuditEventHandler(connect).handle(event)
    with connect() as connection:
        with connection.cursor() as cursor:
            with pytest.raises(pymysql.MySQLError):
                cursor.execute("UPDATE audit_events SET result='ALTERED' WHERE event_id=%s", (event["eventId"],))
        connection.rollback()
        with connection.cursor() as cursor:
            with pytest.raises(pymysql.MySQLError):
                cursor.execute("DELETE FROM audit_events WHERE event_id=%s", (event["eventId"],))
