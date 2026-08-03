import logging
import os
import threading
import time

from kafka import KafkaProducer

from services.shared.kafka import KafkaDlqPublisher, KafkaEnvelopePublisher, KafkaSettings
from services.shared.outbox import OutboxRelay

from app.adapters.inbound.kafka.payment_event_consumer import PaymentEventConsumer, build_consumer
from app.application.handlers.order_payment_handler import OrderPaymentHandler


LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "svc-usage-facturation"


def start_event_runtime(connection_factory, gateway):
    if os.getenv("PAYMENT_EVENT_RUNTIME_ENABLED", "false").lower() != "true":
        return []
    producer = KafkaProducer(**KafkaSettings.from_env("svc-usage-facturation").producer_config())
    relay = OutboxRelay(connection_factory, KafkaEnvelopePublisher(producer, SERVICE_NAME), service_name=SERVICE_NAME)
    consumer = PaymentEventConsumer(build_consumer(), OrderPaymentHandler(connection_factory, gateway), KafkaDlqPublisher(producer, SERVICE_NAME))

    def relay_loop():
        interval = int(os.getenv("OUTBOX_POLL_INTERVAL_MS", "500")) / 1000
        while True:
            try:
                relay.publish_batch(int(os.getenv("OUTBOX_BATCH_SIZE", "100")))
            except Exception:
                LOGGER.exception("outbox_relay_iteration_failed")
            time.sleep(interval)

    threads = [
        threading.Thread(target=relay_loop, name="payment-outbox-relay", daemon=True),
        threading.Thread(target=consumer.run_forever, name="payment-event-consumer", daemon=True),
    ]
    for thread in threads:
        thread.start()
    return threads
