import json

from kafka import KafkaConsumer, KafkaProducer

from services.shared.events import EVENT_TOPICS
from services.shared.kafka import KafkaDlqPublisher, KafkaSettings, handle_record_with_retry


class AuditEventConsumer:
    def __init__(self, consumer, handler, dlq_publisher):
        self.consumer = consumer
        self.handler = handler
        self.dlq_publisher = dlq_publisher

    def process_record(self, record):
        return handle_record_with_retry(self.consumer, record, self.handler.handle, self.dlq_publisher, service_name="svc-conformite-audit")

    def run_forever(self):
        for record in self.consumer:
            self.process_record(record)


def build_consumer():
    settings = KafkaSettings.from_env("svc-conformite-audit", consumer=True)
    return KafkaConsumer(
        *EVENT_TOPICS.values(),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        **settings.consumer_config(),
    )


def build_dlq_publisher():
    producer = KafkaProducer(**KafkaSettings.from_env("svc-conformite-audit-dlq").producer_config())
    return KafkaDlqPublisher(producer, "svc-conformite-audit")
