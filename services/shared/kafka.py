from __future__ import annotations

from dataclasses import dataclass
import json
from os import environ
import time
from datetime import datetime, timezone

from kafka.structs import OffsetAndMetadata, TopicPartition

from services.shared.schema_validation import validate_event
from services.shared.events import EVENT_TOPICS
from services.shared.event_metrics import EVENTS_CONSUMED, EVENTS_DLQ, EVENTS_PRODUCED, EVENT_RETRIES
from services.shared.tracing import traceparent_from_trace_id


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str
    client_id: str
    group_id: str | None = None
    auto_offset_reset: str = "earliest"
    security_protocol: str = "PLAINTEXT"

    @classmethod
    def from_env(cls, service_name: str, *, consumer: bool = False) -> "KafkaSettings":
        return cls(
            bootstrap_servers=environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            client_id=environ.get("KAFKA_CLIENT_ID", service_name),
            group_id=environ.get("KAFKA_GROUP_ID", service_name) if consumer else None,
            auto_offset_reset=environ.get("KAFKA_AUTO_OFFSET_RESET", "earliest"),
            security_protocol=environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        )

    def producer_config(self) -> dict[str, object]:
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "acks": "all",
            "enable_idempotence": True,
            "security_protocol": self.security_protocol,
            "retries": 5,
            "max_in_flight_requests_per_connection": 1,
        }

    def consumer_config(self) -> dict[str, object]:
        if not self.group_id:
            raise ValueError("group_id is required for a consumer")
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "group_id": self.group_id,
            "enable_auto_commit": False,
            "auto_offset_reset": self.auto_offset_reset,
            "security_protocol": self.security_protocol,
        }


def handle_record(consumer, record, handler) -> None:
    """Validate and handle one record, then commit only its next offset."""
    validate_event(record.value)
    handler(record.value)
    consumer.commit(
        offsets={
            TopicPartition(record.topic, record.partition): OffsetAndMetadata(
                record.offset + 1, "", -1
            )
        }
    )


class KafkaEnvelopePublisher:
    def __init__(self, producer, service_name="unknown", ack_timeout_seconds: int = 10):
        self.producer = producer
        self.service_name = service_name
        self.ack_timeout_seconds = ack_timeout_seconds

    def publish(self, event_type: str, aggregate_id: str, document: dict):
        validate_event(document)
        if document["aggregateId"] != aggregate_id:
            raise ValueError("Kafka key must equal envelope aggregateId")
        future = self.producer.send(
            EVENT_TOPICS[event_type],
            key=aggregate_id.encode("utf-8"),
            value=json.dumps(document, separators=(",", ":")).encode("utf-8"),
            headers=[
                ("traceparent", traceparent_from_trace_id(document["traceId"]).encode("ascii")),
                ("eventId", document["eventId"].encode("ascii")),
                ("aggregateId", document["aggregateId"].encode("utf-8")),
                ("sagaId", document["sagaId"].encode("ascii")),
                ("correlationId", document["correlationId"].encode("utf-8")),
                ("causationId", (document.get("causationId") or "").encode("ascii")),
            ],
        )
        result = future.get(timeout=self.ack_timeout_seconds)
        EVENTS_PRODUCED.labels(self.service_name, event_type, EVENT_TOPICS[event_type]).inc()
        return result


class KafkaDlqPublisher:
    def __init__(self, producer, service_name="unknown", ack_timeout_seconds=10):
        self.producer = producer
        self.service_name = service_name
        self.ack_timeout_seconds = ack_timeout_seconds

    def publish(self, record, error, attempts):
        document = {
            "originalPayload": record.value,
            "originalHeaders": {
                key: value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
                for key, value in (record.headers or [])
            },
            "originalTopic": record.topic,
            "originalPartition": record.partition,
            "originalOffset": record.offset,
            "error": f"{type(error).__name__}: {error}",
            "attempts": attempts,
            "failedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        future = self.producer.send(
            f"{record.topic}.dlq",
            key=getattr(record, "key", None),
            value=json.dumps(document, separators=(",", ":")).encode("utf-8"),
            headers=[("dlq_reason", str(error).encode("utf-8")), ("dlq_original_topic", record.topic.encode("utf-8")), ("dlq_attempts", str(attempts).encode("ascii"))],
        )
        result = future.get(timeout=self.ack_timeout_seconds)
        EVENTS_DLQ.labels(self.service_name, record.topic).inc()
        return result


def handle_record_with_retry(consumer, record, handler, dlq_publisher, max_attempts=3, base_backoff_seconds=0.25, service_name="unknown"):
    """Retry technical failures, then acknowledge only after handling or DLQ ACK."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            validate_event(record.value)
            handler(record.value)
            _commit_record(consumer, record)
            EVENTS_CONSUMED.labels(service_name, record.value["eventType"], record.topic, "success").inc()
            return "PROCESSED"
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                EVENT_RETRIES.labels(service_name, "consumer", record.value.get("eventType", "invalid")).inc()
                time.sleep(min(base_backoff_seconds * (2 ** (attempt - 1)), 2.0))
    dlq_publisher.publish(record, last_error, max_attempts)
    _commit_record(consumer, record)
    return "DLQ"


def _commit_record(consumer, record):
    consumer.commit(
        offsets={
            TopicPartition(record.topic, record.partition): OffsetAndMetadata(record.offset + 1, "", -1)
        }
    )
