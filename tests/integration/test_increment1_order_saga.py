import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pymysql
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "svc-commandes-activations"
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(ROOT))
for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]

from app.adapters.outbound.persistence.mysql_activation_repository import MysqlActivationRepository  # noqa: E402
from app.application.handlers.order_saga_handler import OrderSagaHandler  # noqa: E402
from app.domain.model.order import Order  # noqa: E402
from app.domain.model.saga_state import SagaState  # noqa: E402
from services.shared.events import EventEnvelope  # noqa: E402
from services.shared.kafka import handle_record  # noqa: E402


def connect():
    return pymysql.connect(
        host=os.getenv("INCREMENT0_MYSQL_HOST", "127.0.0.1"),
        user="cantelcox",
        password=os.getenv("INCREMENT0_MYSQL_PASSWORD", os.getenv("MYSQL_PASSWORD", "cantelcox_dev")),
        database="commandes_activations",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def mysql_available():
    try:
        connection = connect()
        connection.close()
        return True
    except pymysql.MySQLError:
        return False


pytestmark = pytest.mark.skipif(not mysql_available(), reason="Increment 1 MySQL dependency is unavailable")


def make_order(order_id=None, saga_id=None, key=None):
    order_id = order_id or str(uuid4())
    saga_id = saga_id or str(uuid4())
    created_at = datetime.now(timezone.utc)
    return Order(
        order_id=order_id,
        customer_id=str(uuid4()),
        offer_id="offer-1",
        order_type="NEW_PLAN",
        status="EN_COURS",
        orchestration_status="EN_COURS",
        confirmation_status="PENDING",
        total_amount=49.99,
        currency="CAD",
        idempotency_key=key or f"increment1-{uuid4()}",
        request_hash="a" * 64,
        response_body={"orderId": order_id, "status": "EN_COURS", "sagaId": saga_id},
        saga_id=saga_id,
        created_at=created_at,
    )


def create_order(repository=None, event_id=None):
    repository = repository or MysqlActivationRepository(connect)
    order = make_order()
    event = EventEnvelope.create(
        event_type="CommandePassee",
        aggregate_id=order.order_id,
        aggregate_type="Commande",
        payload={"idCommande": order.order_id, "idClient": order.customer_id, "idOffre": order.offer_id, "montant": 49.99, "devise": "CAD"},
        trace_id="1" * 32,
        correlation_id=order.order_id,
        saga_id=order.saga_id,
        event_id=event_id,
    )
    saga = SagaState(
        saga_id=order.saga_id,
        order_id=order.order_id,
        status="EN_COURS",
        deadline_at=datetime.now(timezone.utc) + timedelta(seconds=60),
        last_event_id=event.eventId,
    )
    repository.create_order_with_saga(order, saga, event)
    return order, event


def source_event(event_type, order, event_id=None):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payloads = {
        "PaiementAutorise": {"idPaiement": "pay-1", "idCommande": order.order_id, "montant": 49.99, "devise": "CAD", "authorizationId": "auth-1", "authorizedAt": now},
        "PaiementRefuse": {"idPaiement": "pay-1", "idCommande": order.order_id, "reasonCode": "DECLINED", "reasonMessage": "declined", "refusedAt": now},
        "PaiementRembourse": {"idPaiement": "pay-1", "idCommande": order.order_id, "refundId": "refund-1", "montant": 49.99, "refundedAt": now},
        "LigneActivee": {"idLigne": "line-1", "idCommande": order.order_id, "msisdn": "15145550123", "activationMode": "NEW", "hlrReference": "hlr-1", "activatedAt": now},
        "ActivationEchouee": {"idLigne": "line-1", "idCommande": order.order_id, "reasonCode": "HLR_FAILED", "reasonMessage": "failed", "attempts": 1, "failedAt": now},
        "NumeroPorte": {"idCommande": order.order_id, "idLigne": "line-1", "portId": "port-1", "msisdn": "15145550123", "portedAt": now, "previousOperator": "other"},
        "PortabiliteEchouee": {"idCommande": order.order_id, "idLigne": "line-1", "portId": "port-1", "msisdn": "15145550123", "reasonCode": "REJECTED", "reasonMessage": "rejected", "failedAt": now, "hubStatus": "rejected"},
    }
    aggregate_types = {"PaiementAutorise": "Paiement", "PaiementRefuse": "Paiement", "PaiementRembourse": "Paiement", "LigneActivee": "Ligne", "ActivationEchouee": "Ligne", "NumeroPorte": "Portabilite", "PortabiliteEchouee": "Portabilite"}
    return EventEnvelope.create(
        event_type=event_type,
        aggregate_id=f"source-{uuid4()}",
        aggregate_type=aggregate_types[event_type],
        payload=payloads[event_type],
        trace_id="2" * 32,
        correlation_id=order.order_id,
        saga_id=order.saga_id,
        causation_id=str(uuid4()),
        event_id=event_id,
    ).to_dict()


def order_status(order_id):
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM orders WHERE order_id=%s", (order_id,))
            return cursor.fetchone()["status"]


def test_order_saga_and_outbox_commit_atomically_and_rollback_together():
    repository = MysqlActivationRepository(connect)
    committed_order, committed_event = create_order(repository)
    rolled_back_order = make_order()
    duplicate_event = EventEnvelope.create(
        event_type="CommandePassee", aggregate_id=rolled_back_order.order_id, aggregate_type="Commande",
        payload={"idCommande": rolled_back_order.order_id, "idClient": rolled_back_order.customer_id, "idOffre": rolled_back_order.offer_id, "montant": 49.99, "devise": "CAD"},
        trace_id="1" * 32, correlation_id=rolled_back_order.order_id, saga_id=rolled_back_order.saga_id,
        event_id=committed_event.eventId,
    )
    rolled_back_saga = SagaState(rolled_back_order.saga_id, rolled_back_order.order_id, "EN_COURS", datetime.now(timezone.utc) + timedelta(seconds=60))

    with pytest.raises(pymysql.err.IntegrityError):
        repository.create_order_with_saga(rolled_back_order, rolled_back_saga, duplicate_event)

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM orders WHERE order_id IN (%s,%s)", (committed_order.order_id, rolled_back_order.order_id))
            assert cursor.fetchone()["n"] == 1
            cursor.execute("SELECT COUNT(*) AS n FROM saga_state WHERE order_id=%s", (rolled_back_order.order_id,))
            assert cursor.fetchone()["n"] == 0


@pytest.mark.parametrize("event_type", ["PaiementRefuse", "ActivationEchouee", "PortabiliteEchouee"])
def test_failure_events_cancel_order_once(event_type):
    order, _ = create_order()
    handler = OrderSagaHandler(connect)

    assert handler.handle(source_event(event_type, order)) == "APPLIED"
    assert order_status(order.order_id) == "ANNULEE"


def test_ligne_activee_confirms_and_duplicate_or_late_events_do_not_transition_again():
    order, _ = create_order()
    handler = OrderSagaHandler(connect)
    activated = source_event("LigneActivee", order)

    assert handler.handle(activated) == "APPLIED"
    assert handler.handle(activated) == "DUPLICATE"
    assert handler.handle(source_event("ActivationEchouee", order)) == "LATE_IGNORED"
    assert order_status(order.order_id) == "CONFIRMEE"
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM outbox_events WHERE aggregate_id=%s AND event_type='CommandeConfirmee'", (order.order_id,))
            assert cursor.fetchone()["n"] == 1


def test_numero_porte_is_intermediate_until_line_activation():
    order, _ = create_order()
    handler = OrderSagaHandler(connect)

    assert handler.handle(source_event("NumeroPorte", order)) == "APPLIED"
    assert order_status(order.order_id) == "EN_COURS"


class RecordingConsumer:
    def __init__(self):
        self.commits = []

    def commit(self, offsets):
        self.commits.append(offsets)


def test_offset_is_not_committed_before_successful_local_transaction():
    order, _ = create_order()
    document = source_event("LigneActivee", order)
    consumer = RecordingConsumer()
    record = SimpleNamespace(value=document, topic="ligne-activee.v1", partition=0, offset=4)

    class FailingHandler:
        def handle(self, event):
            raise RuntimeError("transaction failed")

    with pytest.raises(RuntimeError):
        handle_record(consumer, record, FailingHandler().handle)
    assert consumer.commits == []

    handle_record(consumer, record, OrderSagaHandler(connect).handle)
    assert len(consumer.commits) == 1
