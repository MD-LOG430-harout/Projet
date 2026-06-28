from flask import Blueprint, current_app, g, jsonify, request

from services.shared.errors import ApiError

from app.application.commands.pay_invoice import PayInvoice
from app.application.queries.get_invoices import GetInvoice, ListInvoices


bp = Blueprint("usage_facturation", __name__)


@bp.get("/v1/invoices")
def list_invoices():
    use_case = ListInvoices(
        current_app.config["repository"],
        current_app.config["customer_client"],
        current_app.config.get("audit_client"),
    )
    return jsonify(use_case.execute(request.args.get("customerId"), trace_id=g.trace_id))


@bp.get("/v1/invoices/<invoice_id>")
def get_invoice(invoice_id):
    use_case = GetInvoice(current_app.config["repository"], current_app.config.get("audit_client"))
    return jsonify(use_case.execute(invoice_id, trace_id=g.trace_id))


@bp.post("/v1/invoices/<invoice_id>/payments")
def pay_invoice(invoice_id):
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required")
    use_case = PayInvoice(
        current_app.config["repository"],
        current_app.config["payment_gateway"],
        current_app.config.get("audit_client"),
    )
    body, status, replayed = use_case.execute(invoice_id, request.get_json(silent=True) or {}, idempotency_key, trace_id=g.trace_id)
    response = jsonify(body)
    response.status_code = status
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return response


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-usage-facturation"})
