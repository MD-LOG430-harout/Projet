from flask import Blueprint, current_app, g, jsonify, request

from services.shared.errors import ApiError

from app.application.commands.create_activation import CreateActivation
from app.application.commands.create_order import CreateOrder


bp = Blueprint("commandes_activations", __name__)


@bp.post("/v1/activations")
def create_activation():
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required")

    use_case = CreateActivation(
        current_app.config["activation_repository"],
        current_app.config["customer_client"],
        current_app.config["offer_client"],
        current_app.config["line_client"],
        current_app.config.get("audit_client"),
        audit_level=current_app.config.get("command_audit_level", "detailed"),
    )
    body, status_code, replayed = use_case.execute(request.get_json(silent=True) or {}, idempotency_key, trace_id=g.trace_id)
    response = jsonify(body)
    response.status_code = status_code
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return response


@bp.post("/v1/orders")
def create_order():
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required")

    use_case = CreateOrder(
        current_app.config["order_repository"],
        current_app.config["customer_client"],
        current_app.config["offer_client"],
        current_app.config.get("audit_client"),
        audit_level=current_app.config.get("command_audit_level", "detailed"),
    )
    body, status_code, replayed = use_case.execute(request.get_json(silent=True) or {}, idempotency_key, trace_id=g.trace_id)
    response = jsonify(body)
    response.status_code = status_code
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return response


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-commandes-activations"})
