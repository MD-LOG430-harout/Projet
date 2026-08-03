import logging
import os
import threading
import time

from kafka import KafkaProducer

from services.shared.kafka import KafkaDlqPublisher, KafkaEnvelopePublisher, KafkaSettings
from services.shared.outbox import OutboxRelay

from app.adapters.inbound.kafka.order_event_consumer import OrderEventConsumer, build_consumer
from app.application.handlers.order_saga_handler import OrderSagaHandler


LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "svc-commandes-activations"


def start_event_runtime(connection_factory):
    if os.getenv("COMMAND_EVENT_RUNTIME_ENABLED", "false").lower() != "true":
        return []

    producer = KafkaProducer(**KafkaSettings.from_env("svc-commandes-activations").producer_config())
    relay = OutboxRelay(connection_factory, KafkaEnvelopePublisher(producer, SERVICE_NAME), service_name=SERVICE_NAME)
    consumer = OrderEventConsumer(build_consumer(), OrderSagaHandler(connection_factory), KafkaDlqPublisher(producer, SERVICE_NAME))

    def relay_loop():
        interval = int(os.getenv("OUTBOX_POLL_INTERVAL_MS", "500")) / 1000
        batch_size = int(os.getenv("OUTBOX_BATCH_SIZE", "100"))
        while True:
            try:
                relay.publish_batch(batch_size)
            except Exception:
                LOGGER.exception("outbox_relay_iteration_failed")
            time.sleep(interval)

    threads = [
        threading.Thread(target=relay_loop, name="order-outbox-relay", daemon=True),
        threading.Thread(target=consumer.run_forever, name="order-event-consumer", daemon=True),
    ]
    for thread in threads:
        thread.start()
    return threads
