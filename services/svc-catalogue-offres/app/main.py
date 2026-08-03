import os

from flask import Flask

from services.shared.errors import register_error_handlers
from services.shared.http import register_request_hooks
from services.shared.logging import configure_json_logging
from services.shared.metrics import register_metrics
from services.shared.mysql import connect_from_env
from services.shared.tracing import initialize_tracing, OtelSettings

from app.adapters.inbound.rest.routes import bp
from app.adapters.outbound.cache.redis_offer_cache import RedisOfferCache
from app.adapters.outbound.persistence.mysql_offer_repository import MysqlOfferRepository


SERVICE_NAME = "svc-catalogue-offres"


def create_app(offer_repository=None, offer_cache=None):
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
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "catalogue_offres"),
    }
    def connection_factory():
        return connect_from_env(db_config)
    app.config["offer_repository"] = offer_repository or MysqlOfferRepository(connection_factory)
    app.config["offer_cache"] = offer_cache
    redis_url = os.getenv("REDIS_URL")
    if offer_cache is None and redis_url:
        app.config["offer_cache"] = RedisOfferCache(
            redis_url,
            os.getenv("OFFER_CACHE_TTL_SECONDS", "60"),
        )
    app.config["offer_cache_ttl_seconds"] = int(os.getenv("OFFER_CACHE_TTL_SECONDS", "60"))
    app.register_blueprint(bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
