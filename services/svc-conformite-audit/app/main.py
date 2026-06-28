import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import connect_from_env

from app.adapters.inbound.rest.routes import bp
from app.adapters.outbound.persistence.mysql_audit_repository import MysqlAuditRepository


SERVICE_NAME = "svc-conformite-audit"


def create_app(audit_repository=None):
    app = Flask(__name__)
    configure_json_logging(app, SERVICE_NAME)
    register_request_hooks(app, SERVICE_NAME)
    register_metrics(app, SERVICE_NAME)
    register_error_handlers(app)

    db_config = {
        "MYSQL_HOST": os.getenv("MYSQL_HOST", "mysql"),
        "MYSQL_PORT": os.getenv("MYSQL_PORT", "3306"),
        "MYSQL_USER": os.getenv("MYSQL_USER", "cantelcox"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", "cantelcox_dev"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "conformite_audit"),
    }
    connection_factory = lambda: connect_from_env(db_config)
    app.config["audit_repository"] = audit_repository or MysqlAuditRepository(connection_factory)
    app.register_blueprint(bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))

