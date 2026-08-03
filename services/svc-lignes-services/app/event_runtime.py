import logging
import os
import threading
import time

from kafka import KafkaProducer

from services.shared.kafka import KafkaDlqPublisher, KafkaEnvelopePublisher, KafkaSettings
from services.shared.outbox import OutboxRelay

from app.adapters.inbound.kafka.line_event_consumer import LineEventConsumer, build_consumer
from app.application.handlers.line_saga_handler import LineSagaHandler
from app.application.handlers.portability_webhook_handler import PortabilityTimeoutScanner


LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "svc-lignes-services"


def start_event_runtime(connection_factory, hlr_adapter, portability_adapter):
    if os.getenv("LINE_EVENT_RUNTIME_ENABLED", "false").lower() != "true":
        return []
    producer = KafkaProducer(**KafkaSettings.from_env("svc-lignes-services").producer_config())
    relay = OutboxRelay(connection_factory, KafkaEnvelopePublisher(producer, SERVICE_NAME), service_name=SERVICE_NAME)
    consumer = LineEventConsumer(build_consumer(), LineSagaHandler(connection_factory, hlr_adapter, portability_adapter), KafkaDlqPublisher(producer, SERVICE_NAME))
    scanner = PortabilityTimeoutScanner(connection_factory)

    def relay_loop():
        interval = int(os.getenv("OUTBOX_POLL_INTERVAL_MS", "500")) / 1000
        while True:
            try:
                relay.publish_batch(int(os.getenv("OUTBOX_BATCH_SIZE", "100")))
            except Exception:
                LOGGER.exception("outbox_relay_iteration_failed")
            time.sleep(interval)

    def timeout_loop():
        while True:
            try:
                scanner.scan()
            except Exception:
                LOGGER.exception("portability_timeout_scan_failed")
            time.sleep(int(os.getenv("PORTABILITY_TIMEOUT_SCAN_SECONDS", "30")))

    threads = [
        threading.Thread(target=relay_loop, name="line-outbox-relay", daemon=True),
        threading.Thread(target=consumer.run_forever, name="line-event-consumer", daemon=True),
        threading.Thread(target=timeout_loop, name="portability-timeout", daemon=True),
    ]
    for thread in threads:
        thread.start()
    return threads
