from flask import Blueprint, current_app, g, jsonify, request

from app.application.commands.activate_line import ActivateLine
from app.application.queries.get_line import GetLine, GetLineByMsisdn
from app.application.handlers.portability_webhook_handler import InvalidWebhook, UnknownHubOrder


bp = Blueprint("lignes_services", __name__)


def _line_public(line):
    def value(name):
        return line.get(name) if isinstance(line, dict) else getattr(line, name)

    return {
        "lineId": value("line_id"),
        "customerId": value("customer_id"),
        "offerId": value("offer_id"),
        "msisdn": value("msisdn"),
        "simType": value("sim_type"),
        "simIdentifier": value("sim_identifier"),
        "imsi": value("imsi"),
        "supi": value("supi"),
        "status": value("status"),
        "hlrStatus": value("hlr_status"),
        "numberMode": value("number_mode"),
        "portabilityStatus": value("portability_status"),
        "failureReason": value("failure_reason"),
    }


@bp.post("/v1/lines/activate")
def activate_line():
    use_case = ActivateLine(current_app.config["line_repository"], current_app.config["hlr_adapter"])
    line = use_case.execute(request.get_json(silent=True) or {}, trace_id=g.trace_id)
    return jsonify(_line_public(line)), 201


@bp.get("/v1/lines/<line_id>")
def get_line(line_id):
    use_case = GetLine(current_app.config["line_repository"])
    return jsonify(_line_public(use_case.execute(line_id)))


@bp.get("/v1/lines/by-msisdn/<msisdn>")
def get_line_by_msisdn(msisdn):
    use_case = GetLineByMsisdn(current_app.config["line_repository"])
    return jsonify(_line_public(use_case.execute(msisdn)))


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-lignes-services"})


@bp.post("/v1/webhooks/portability")
def portability_webhook():
    try:
        result = current_app.config["portability_webhook_handler"].handle(request.get_json(silent=True) or {})
    except InvalidWebhook as exc:
        return jsonify({"code": "invalid_portability_webhook", "message": str(exc)}), 400
    except UnknownHubOrder:
        return jsonify({"code": "unknown_hub_order", "message": "Unknown PortabilityHub order"}), 404
    return jsonify({"status": "ACCEPTED", "result": result}), 200
