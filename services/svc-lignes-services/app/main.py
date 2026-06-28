import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import connect_from_env

from app.adapters.inbound.rest.routes import bp
from app.adapters.outbound.hlr.free5gc_hlr_adapter import Free5gcHlrAdapter
from app.adapters.outbound.hlr.mock_hlr_adapter import MockHlrAdapter
from app.adapters.outbound.persistence.mysql_line_repository import MysqlLineRepository


SERVICE_NAME = "svc-lignes-services"


def create_app(line_repository=None, hlr_adapter=None):
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
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "lignes_services"),
    }
    connection_factory = lambda: connect_from_env(db_config)
    app.config["line_repository"] = line_repository or MysqlLineRepository(connection_factory)
    app.config["hlr_adapter"] = hlr_adapter or _build_hlr_adapter()
    app.register_blueprint(bp)
    return app


def _build_hlr_adapter():
    if os.getenv("HLR_ENABLED", "false").lower() == "true":
        return Free5gcHlrAdapter(
            base_url=os.getenv("FREE5GC_WEBUI_URL", "http://host.docker.internal:5050"),
            username=os.getenv("FREE5GC_WEBUI_USERNAME", "admin"),
            password=os.getenv("FREE5GC_WEBUI_PASSWORD", "free5gc"),
            plmn_id=os.getenv("FREE5GC_PLMN_ID", "20893"),
        )
    return MockHlrAdapter(force_failure=os.getenv("HLR_FORCE_FAILURE", "false").lower() == "true")


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
