from uuid import uuid4

import pytest

from services.shared.events import EventEnvelope
from services.shared.kafka import KafkaSettings
from services.shared.processed_events import DuplicateEvent, MysqlProcessedEventRepository
from services.shared.tracing import inject_traceparent, parse_traceparent
from services.shared.tracing import extract_context, inject_context


def test_envelope_is_immutable_and_uses_aggregate_as_kafka_key():
    envelope = EventEnvelope.create(
        event_type="CommandePassee",
        aggregate_id="cmd-1",
        aggregate_type="Commande",
        payload={
            "idCommande": "cmd-1",
            "idClient": "cli-1",
            "idOffre": "offre-1",
            "montant": 10.0,
            "devise": "CAD",
        },
        trace_id="0123456789abcdef0123456789abcdef",
        correlation_id="cmd-1",
        saga_id=str(uuid4()),
    )
    assert envelope.topic == "commande-passee.v1"
    assert envelope.kafka_key == "cmd-1"
    with pytest.raises(TypeError):
        envelope.payload["new"] = "value"


def test_consumer_configuration_disables_auto_commit():
    settings = KafkaSettings("kafka:9092", "svc-test", group_id="svc-test")
    assert settings.consumer_config()["enable_auto_commit"] is False
    assert settings.consumer_config()["auto_offset_reset"] == "earliest"
    assert settings.producer_config()["acks"] == "all"
    assert settings.producer_config()["enable_idempotence"] is True
    assert settings.producer_config()["security_protocol"] == "PLAINTEXT"
    assert settings.producer_config()["max_in_flight_requests_per_connection"] == 1


def test_w3c_traceparent_validation_and_injection():
    value = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    headers = {}
    assert parse_traceparent(value)["trace_id"] == "0123456789abcdef0123456789abcdef"
    inject_traceparent(headers, value.upper())
    assert headers["traceparent"] == value
    with pytest.raises(ValueError):
        inject_traceparent(headers, "not-a-traceparent")


def test_opentelemetry_extracts_and_reinjects_w3c_context():
    value = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    context = extract_context({"traceparent": value})
    headers = {}
    inject_context(headers, context)
    assert headers["traceparent"].startswith("00-0123456789abcdef0123456789abcdef-")


class DuplicateCursor:
    def execute(self, statement, parameters):
        error = RuntimeError("duplicate")
        error.args = (1062, "duplicate")
        raise error


def test_processed_event_duplicate_is_normalized():
    with pytest.raises(DuplicateEvent):
        MysqlProcessedEventRepository().reserve(DuplicateCursor(), str(uuid4()), "CommandePassee")
