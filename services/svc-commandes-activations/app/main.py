import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import connect_from_env
from services.shared.tracing import initialize_tracing, OtelSettings

from app.adapters.inbound.rest.routes import bp
from app.adapters.outbound.http.audit_client import AuditClient
from app.adapters.outbound.http.customer_client import CustomerClient
from app.adapters.outbound.http.line_client import LineClient
from app.adapters.outbound.http.offer_client import OfferClient
from app.adapters.outbound.persistence.mysql_activation_repository import MysqlActivationRepository
from app.event_runtime import start_event_runtime


SERVICE_NAME = "svc-commandes-activations"


def create_app(
    activation_repository=None,
    customer_client=None,
    offer_client=None,
    line_client=None,
    audit_client=None,
    order_repository=None,
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
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "commandes_activations"),
    }
    def connection_factory():
        return connect_from_env(db_config)
    repository = activation_repository or MysqlActivationRepository(connection_factory)
    app.config["activation_repository"] = repository
    app.config["order_repository"] = order_repository or repository
    app.config["customer_client"] = customer_client or CustomerClient(os.getenv("CUSTOMER_SERVICE_URL", "http://svc-clients-identite:5000"))
    offer_cache_ttl = int(os.getenv("OFFER_CACHE_TTL_SECONDS", "60"))
    app.config["offer_client"] = offer_client or OfferClient(
        os.getenv("CATALOGUE_SERVICE_URL", "http://svc-catalogue-offres:5000"),
        ttl_seconds=offer_cache_ttl,
    )
    app.config["line_client"] = line_client or LineClient(os.getenv("LINES_SERVICE_URL", "http://svc-lignes-services:5000"))
    app.config["audit_client"] = audit_client or AuditClient(os.getenv("AUDIT_SERVICE_URL", "http://svc-conformite-audit:5000"))
    app.config["command_audit_level"] = os.getenv("COMMAND_AUDIT_LEVEL", "detailed").lower()
    app.register_blueprint(bp)
    app.extensions["event_runtime_threads"] = start_event_runtime(connection_factory)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
