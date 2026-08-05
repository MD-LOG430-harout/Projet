import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import build_pooled_connection_factory
from services.shared.tracing import initialize_tracing, OtelSettings

from app.adapters.inbound.rest.routes import bp
from app.adapters.outbound.http.audit_client import AuditClient
from app.adapters.outbound.http.customer_client import CustomerClient
from app.adapters.outbound.payment.simulated_payment_gateway import SimulatedPaymentGateway
from app.adapters.outbound.persistence.mysql_usage_billing_repository import MysqlUsageBillingRepository
from app.event_runtime import start_event_runtime


SERVICE_NAME = "svc-usage-facturation"


def create_app(
    repository=None,
    customer_client=None,
    payment_gateway=None,
    audit_client=None,
):
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
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "usage_facturation"),
    }
    connection_factory = build_pooled_connection_factory(db_config, size=int(os.getenv("MYSQL_POOL_SIZE", "10")))
    app.config["repository"] = repository or MysqlUsageBillingRepository(connection_factory)
    app.config["customer_client"] = customer_client or CustomerClient(os.getenv("CUSTOMER_SERVICE_URL", "http://svc-clients-identite:5000"))
    app.config["payment_gateway"] = payment_gateway or SimulatedPaymentGateway(
        force_failure=os.getenv("PAYMENT_GATEWAY_FORCE_FAILURE", "false").lower() == "true",
        force_refusal=os.getenv("PAYMENT_GATEWAY_FORCE_REFUSAL", "false").lower() == "true",
    )
    app.config["audit_client"] = audit_client or AuditClient(os.getenv("AUDIT_SERVICE_URL", "http://svc-conformite-audit:5000"))
    app.register_blueprint(bp)
    app.extensions["event_runtime_threads"] = start_event_runtime(connection_factory, app.config["payment_gateway"])
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
