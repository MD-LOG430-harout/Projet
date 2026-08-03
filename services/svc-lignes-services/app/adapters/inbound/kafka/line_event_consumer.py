import json

from kafka import KafkaConsumer

from services.shared.events import EVENT_TOPICS
from services.shared.kafka import KafkaSettings, handle_record_with_retry


LINE_EVENT_TYPES = ("PaiementAutorise", "CommandeAnnulee")


class LineEventConsumer:
    def __init__(self, consumer, handler, dlq_publisher):
        self.consumer = consumer
        self.handler = handler
        self.dlq_publisher = dlq_publisher

    def process_record(self, record):
        return handle_record_with_retry(self.consumer, record, self.handler.handle, self.dlq_publisher, service_name="svc-lignes-services")

    def run_forever(self):
        for record in self.consumer:
            self.process_record(record)


def build_consumer():
    settings = KafkaSettings.from_env("svc-lignes-services", consumer=True)
    return KafkaConsumer(
        *(EVENT_TOPICS[event_type] for event_type in LINE_EVENT_TYPES),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        **settings.consumer_config(),
    )
