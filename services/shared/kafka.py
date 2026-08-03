from __future__ import annotations

from dataclasses import dataclass
import json
from os import environ
import time
from datetime import datetime, timezone

from kafka.structs import OffsetAndMetadata, TopicPartition
from opentelemetry import trace
from opentelemetry.trace import SpanKind

from services.shared.schema_validation import validate_event
from services.shared.events import EVENT_TOPICS
from services.shared.event_metrics import (
    CONSUMER_LAG,
    EVENTS_CONSUMED,
    EVENTS_DLQ,
    EVENTS_PRODUCED,
    EVENT_PROCESSING_DURATION,
    EVENT_RETRIES,
)
from services.shared.tracing import extract_context, inject_context, traceparent_from_trace_id


_tracer = trace.get_tracer("services.shared.kafka")

# Lag is a broker-wide gauge: refreshing it on every record would add a round trip per message.
LAG_REPORT_INTERVAL_SECONDS = 5.0
_last_lag_report: dict[int, float] = {}


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
        topic = EVENT_TOPICS[event_type]
        # The Outbox relay runs in its own thread with no ambient span, so the envelope
        # traceId is the only link back to the request that created the event.
        parent_context = extract_context(
            {"traceparent": traceparent_from_trace_id(document["traceId"])}
        )
        with _tracer.start_as_current_span(
            f"publish {topic}", context=parent_context, kind=SpanKind.PRODUCER
        ) as span:
            span.set_attribute("messaging.system", "kafka")
            span.set_attribute("messaging.destination.name", topic)
            span.set_attribute("cantelcox.event_type", event_type)
            span.set_attribute("cantelcox.event_id", document["eventId"])
            span.set_attribute("cantelcox.saga_id", document["sagaId"])
            future = self.producer.send(
                topic,
                key=aggregate_id.encode("utf-8"),
                value=json.dumps(document, separators=(",", ":")).encode("utf-8"),
                headers=[
                    *_trace_headers(document["traceId"]),
                    ("eventId", document["eventId"].encode("ascii")),
                    ("aggregateId", document["aggregateId"].encode("utf-8")),
                    ("sagaId", document["sagaId"].encode("ascii")),
                    ("correlationId", document["correlationId"].encode("utf-8")),
                    ("causationId", (document.get("causationId") or "").encode("ascii")),
                ],
            )
            result = future.get(timeout=self.ack_timeout_seconds)
        EVENTS_PRODUCED.labels(self.service_name, event_type, topic).inc()
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
    event_type = _event_type_of(record)
    # Continue the producer trace so Jaeger links REST -> publish -> consume across services.
    context = extract_context(_header_carrier(record))
    with _tracer.start_as_current_span(
        f"consume {record.topic}", context=context, kind=SpanKind.CONSUMER
    ) as span:
        span.set_attribute("messaging.system", "kafka")
        span.set_attribute("messaging.source.name", record.topic)
        span.set_attribute("messaging.kafka.source.partition", record.partition)
        span.set_attribute("messaging.kafka.message.offset", record.offset)
        span.set_attribute("cantelcox.event_type", event_type)
        span.set_attribute("cantelcox.consumer", service_name)

        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                with EVENT_PROCESSING_DURATION.labels(service_name, event_type).time():
                    validate_event(record.value)
                    handler(record.value)
                _commit_record(consumer, record)
                EVENTS_CONSUMED.labels(service_name, event_type, record.topic, "success").inc()
                _report_consumer_lag(consumer, service_name)
                return "PROCESSED"
            except Exception as exc:
                last_error = exc
                if attempt < max_attempts:
                    EVENT_RETRIES.labels(service_name, "consumer", event_type).inc()
                    time.sleep(min(base_backoff_seconds * (2 ** (attempt - 1)), 2.0))
        span.set_attribute("cantelcox.dlq_reason", f"{type(last_error).__name__}: {last_error}")
        span.set_status(trace.Status(trace.StatusCode.ERROR, "routed to DLQ"))
        dlq_publisher.publish(record, last_error, max_attempts)
        _commit_record(consumer, record)
        EVENTS_CONSUMED.labels(service_name, event_type, record.topic, "dlq").inc()
        _report_consumer_lag(consumer, service_name)
        return "DLQ"


def _event_type_of(record) -> str:
    value = getattr(record, "value", None)
    if isinstance(value, dict):
        return value.get("eventType", "invalid")
    return "invalid"


def _header_carrier(record) -> dict[str, str]:
    """W3C propagators expect a string mapping; Kafka headers are (name, bytes) pairs."""
    carrier = {}
    for name, value in (getattr(record, "headers", None) or []):
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        carrier[name] = value
    return carrier


def _trace_headers(trace_id: str) -> list[tuple[str, bytes]]:
    """Propagate the producer span; fall back to the envelope trace id if tracing is off."""
    carrier: dict[str, str] = {}
    inject_context(carrier)
    if "traceparent" not in carrier:
        carrier["traceparent"] = traceparent_from_trace_id(trace_id)
    headers = [("traceparent", carrier["traceparent"].encode("ascii"))]
    if carrier.get("tracestate"):
        headers.append(("tracestate", carrier["tracestate"].encode("ascii")))
    return headers


def _report_consumer_lag(consumer, service_name: str) -> None:
    """Publish the broker lag per topic, throttled so it costs one round trip every few seconds."""
    key = id(consumer)
    now = time.monotonic()
    if now - _last_lag_report.get(key, 0.0) < LAG_REPORT_INTERVAL_SECONDS:
        return
    _last_lag_report[key] = now
    try:
        partitions = list(consumer.assignment() or [])
        if not partitions:
            return
        end_offsets = consumer.end_offsets(partitions)
        per_topic: dict[str, int] = {}
        for partition in partitions:
            end = end_offsets.get(partition)
            position = consumer.position(partition)
            if end is None or position is None:
                continue
            per_topic[partition.topic] = per_topic.get(partition.topic, 0) + max(end - position, 0)
        for topic, lag in per_topic.items():
            CONSUMER_LAG.labels(service_name, topic).set(lag)
    except Exception:
        # Observability must never interrupt consumption.
        return


def _commit_record(consumer, record):
    consumer.commit(
        offsets={
            TopicPartition(record.topic, record.partition): OffsetAndMetadata(record.offset + 1, "", -1)
        }
    )
