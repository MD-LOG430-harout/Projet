from types import SimpleNamespace

from services.shared.kafka import handle_record_with_retry
from services.shared.events import EventEnvelope
from uuid import uuid4


class Consumer:
    def __init__(self):
        self.commits = []

    def commit(self, offsets):
        self.commits.append(offsets)


class Dlq:
    def __init__(self):
        self.calls = []

    def publish(self, record, error, attempts):
        self.calls.append((record, error, attempts))


def valid_event():
    order_id = str(uuid4())
    return EventEnvelope.create(
        event_type="CommandePassee", aggregate_id=order_id, aggregate_type="Commande",
        payload={"idCommande": order_id, "idClient": "client", "idOffre": "offer", "montant": 1, "devise": "CAD"},
        trace_id="1" * 32, correlation_id=order_id, saga_id=str(uuid4()),
    ).to_dict()


def test_retry_exhaustion_publishes_dlq_before_offset_commit():
    consumer, dlq = Consumer(), Dlq()
    record = SimpleNamespace(value=valid_event(), topic="commande-passee.v1", partition=0, offset=7, headers=[], key=b"cmd")
    calls = []

    def fail(document):
        calls.append(document)
        raise RuntimeError("database unavailable")

    assert handle_record_with_retry(consumer, record, fail, dlq, max_attempts=3, base_backoff_seconds=0) == "DLQ"
    assert len(calls) == 3
    assert dlq.calls[0][2] == 3
    assert len(consumer.commits) == 1


def test_success_does_not_publish_dlq():
    consumer, dlq = Consumer(), Dlq()
    record = SimpleNamespace(value=valid_event(), topic="commande-passee.v1", partition=0, offset=1, headers=[], key=b"cmd")
    assert handle_record_with_retry(consumer, record, lambda document: None, dlq) == "PROCESSED"
    assert not dlq.calls
    assert len(consumer.commits) == 1
