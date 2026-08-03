from prometheus_client import Counter, Gauge, Histogram


EVENTS_PRODUCED = Counter(
    "cantelcox_events_produced_total",
    "Internal events acknowledged by Kafka",
    ["service", "event_type", "topic"],
)
EVENTS_CONSUMED = Counter(
    "cantelcox_events_consumed_total",
    "Internal events processed locally",
    ["service", "event_type", "topic", "result"],
)
EVENT_PROCESSING_DURATION = Histogram(
    "cantelcox_event_processing_duration_seconds",
    "Local event handler duration",
    ["service", "event_type"],
)
OUTBOX_PENDING = Gauge(
    "cantelcox_outbox_pending",
    "Pending Outbox rows",
    ["service"],
)
OUTBOX_OLDEST_AGE = Gauge(
    "cantelcox_outbox_oldest_event_age_seconds",
    "Age of the oldest pending Outbox row",
    ["service"],
)
EVENT_RETRIES = Counter(
    "cantelcox_event_retries_total",
    "Event handling or publication retries",
    ["service", "stage", "event_type"],
)
EVENTS_DLQ = Counter(
    "cantelcox_events_dlq_total",
    "Events published to a DLQ",
    ["service", "source_topic"],
)
CONSUMER_LAG = Gauge("cantelcox_consumer_lag", "Consumer lag", ["service", "topic"])
SAGA_DURATION = Histogram("cantelcox_saga_duration_seconds", "Saga convergence duration", ["outcome"])
SAGA_TRANSITIONS = Counter("cantelcox_saga_transitions_total", "Saga transitions", ["service", "result"])
SAGA_TIMEOUTS = Counter("cantelcox_saga_timeouts_total", "Detected saga timeouts", ["service"])
EXTERNAL_CALL_DURATION = Histogram(
    "cantelcox_external_call_duration_seconds", "External request duration", ["service", "dependency", "operation"]
)
EXTERNAL_CALL_ERRORS = Counter(
    "cantelcox_external_call_errors_total", "External request errors", ["service", "dependency", "operation", "code"]
)
PAYMENT_RESULTS = Counter(
    "cantelcox_payment_saga_results_total", "Saga payment results", ["operation", "result"]
)
