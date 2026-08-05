import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import build_pooled_connection_factory
from services.shared.tracing import initialize_tracing, OtelSettings

from app.adapters.inbound.rest.routes import bp
from app.adapters.outbound.hlr.free5gc_hlr_adapter import Free5gcHlrAdapter
from app.adapters.outbound.hlr.mock_hlr_adapter import MockHlrAdapter
from app.adapters.outbound.persistence.mysql_line_repository import MysqlLineRepository
from app.adapters.outbound.http.customer_client import CustomerClient
from app.adapters.outbound.portability.portability_hub_adapter import PortabilityHubAdapter
from app.application.handlers.portability_webhook_handler import PortabilityWebhookHandler
from app.event_runtime import start_event_runtime


SERVICE_NAME = "svc-lignes-services"


def create_app(line_repository=None, hlr_adapter=None, portability_adapter=None, customer_client=None, connection_factory_override=None):
    app = Flask(__name__)
    initialize_tracing(OtelSettings.from_env(SERVICE_NAME))
    configure_json_logging(app, SERVICE_NAME)
    register_request_hooks(app, SERVICE_NAME)
    register_metrics(app, SERVICE_NAME)
    register_error_handlers(app)

    db_config = {
        "MYSQL_HOST": os.getenv("MYSQL_HOST", "mysql"),
        "MYSQL_PORT": os.getenv("MYSQL_PORT", "3306"),
        "MYSQL_USER": os.getenv("MYSQL_USER", "cantelcox"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", "cantelcox_dev"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "lignes_services"),
    }
    default_connection_factory = build_pooled_connection_factory(db_config, size=int(os.getenv("MYSQL_POOL_SIZE", "10")))
    connection_factory = connection_factory_override or default_connection_factory
    app.config["line_repository"] = line_repository or MysqlLineRepository(connection_factory)
    app.config["hlr_adapter"] = hlr_adapter or _build_hlr_adapter()
    customer_client = customer_client or CustomerClient(os.getenv("CUSTOMER_SERVICE_URL", "http://svc-clients-identite:5000"))
    app.config["portability_adapter"] = portability_adapter or PortabilityHubAdapter(
        base_url=os.getenv("PORTABILITY_HUB_URL", "http://portabilityhub-gateway:8080"),
        customer_client=customer_client,
        recipient_operator=os.getenv("PORTABILITY_RECIPIENT_OPERATOR", "CanTelcoX"),
        lead_time_hours=int(os.getenv("PORTABILITY_LEAD_TIME_HOURS", "24")),
        timeout_seconds=float(os.getenv("PORTABILITY_HTTP_TIMEOUT_SECONDS", "3")),
        max_attempts=int(os.getenv("PORTABILITY_HTTP_MAX_ATTEMPTS", "3")),
    )
    if connection_factory_override or line_repository is None:
        app.config["portability_webhook_handler"] = PortabilityWebhookHandler(connection_factory, app.config["hlr_adapter"])
    app.register_blueprint(bp)
    app.extensions["event_runtime_threads"] = start_event_runtime(connection_factory, app.config["hlr_adapter"], app.config["portability_adapter"])
    return app


def _build_hlr_adapter():
    if os.getenv("HLR_ENABLED", "false").lower() == "true":
        return Free5gcHlrAdapter(
            base_url=os.getenv("FREE5GC_WEBUI_URL", "http://host.docker.internal:5050"),
            username=os.getenv("FREE5GC_WEBUI_USERNAME", "admin"),
            password=os.getenv("FREE5GC_WEBUI_PASSWORD", "free5gc"),
            plmn_id=os.getenv("FREE5GC_PLMN_ID", "20893"),
            permanent_key=os.environ["FREE5GC_SUBSCRIBER_PERMANENT_KEY"],
            opc=os.environ["FREE5GC_SUBSCRIBER_OPC"],
            sequence_number=os.environ["FREE5GC_SUBSCRIBER_SEQUENCE_NUMBER"],
            amf=os.getenv("FREE5GC_SUBSCRIBER_AMF", "8000"),
            timeout_seconds=float(os.getenv("FREE5GC_HTTP_TIMEOUT_SECONDS", "3")),
            max_attempts=int(os.getenv("FREE5GC_HTTP_MAX_ATTEMPTS", "3")),
        )
    return MockHlrAdapter(force_failure=os.getenv("HLR_FORCE_FAILURE", "false").lower() == "true")


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
