import json

from kafka import KafkaConsumer

from services.shared.events import EVENT_TOPICS
from services.shared.kafka import KafkaSettings, handle_record_with_retry


ORDER_EVENT_TYPES = (
    "PaiementAutorise",
    "PaiementRefuse",
    "PaiementRembourse",
    "LigneActivee",
    "ActivationEchouee",
    "NumeroPorte",
    "PortabiliteEchouee",
)


class OrderEventConsumer:
    def __init__(self, consumer, handler, dlq_publisher):
        self.consumer = consumer
        self.handler = handler
        self.dlq_publisher = dlq_publisher

    def process_record(self, record):
        return handle_record_with_retry(self.consumer, record, self.handler.handle, self.dlq_publisher, service_name="svc-commandes-activations")

    def run_forever(self):
        for record in self.consumer:
            self.process_record(record)


def build_consumer(service_name="svc-commandes-activations"):
    settings = KafkaSettings.from_env(service_name, consumer=True)
    return KafkaConsumer(
        *(EVENT_TOPICS[event_type] for event_type in ORDER_EVENT_TYPES),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        **settings.consumer_config(),
    )
