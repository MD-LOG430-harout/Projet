import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import build_pooled_connection_factory
from services.shared.tracing import initialize_tracing, OtelSettings

from app.adapters.inbound.rest.routes import VerifiedChallengeCache, bp
from app.adapters.outbound.http.audit_client import AuditClient
from app.adapters.outbound.persistence.mysql_customer_repository import MysqlCustomerRepository
from app.adapters.outbound.persistence.mysql_mfa_repository import MysqlMfaRepository


SERVICE_NAME = "svc-clients-identite"


def create_app(customer_repository=None, mfa_repository=None, audit_client=None):
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
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "clients_identite"),
    }
    connection_factory = build_pooled_connection_factory(db_config, size=int(os.getenv("MYSQL_POOL_SIZE", "10")))
    app.config["customer_repository"] = customer_repository or MysqlCustomerRepository(connection_factory)
    app.config["mfa_repository"] = mfa_repository or MysqlMfaRepository(connection_factory)
    app.config["verified_challenge_cache"] = VerifiedChallengeCache()

    audit_url = os.getenv("AUDIT_SERVICE_URL")
    if audit_client is not None:
        app.config["audit_client"] = audit_client
    elif audit_url:
        app.config["audit_client"] = AuditClient(audit_url)
    else:
        app.config["audit_client"] = None

    app.register_blueprint(bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
