from flask import Blueprint, current_app, g, jsonify, request

from services.shared.errors import ApiError

from app.application.commands.login import Login
from app.application.commands.register_customer import RegisterCustomer
from app.application.commands.verify_mfa import VerifyMfa
from app.application.queries.get_customer import GetCustomer


bp = Blueprint("clients_identite", __name__)


def _customer_public(customer):
    def value(name):
        if isinstance(customer, dict):
            return customer.get(name)
        return getattr(customer, name)

    return {
        "customerId": value("customer_id"),
        "email": value("email"),
        "displayName": value("display_name"),
        "legalName": value("legal_name"),
        "address": {
            "line1": value("address_line1"),
            "city": value("city"),
            "province": value("province"),
            "postalCode": value("postal_code"),
        },
        "identityDocument": {
            "type": value("identity_document_type"),
            "verified": value("identity_status") == "VERIFIED",
        },
        "customerType": value("customer_type"),
        "status": value("status"),
        "identityStatus": value("identity_status"),
        "riskLevel": value("risk_level"),
    }


@bp.post("/v1/customers/register")
def register_customer():
    use_case = RegisterCustomer(current_app.config["customer_repository"], current_app.config.get("audit_client"))
    customer = use_case.execute(request.get_json(silent=True) or {}, trace_id=g.trace_id)
    return jsonify(_customer_public(customer)), 201


@bp.get("/v1/customers/<customer_id>")
def get_customer(customer_id):
    use_case = GetCustomer(current_app.config["customer_repository"])
    customer = use_case.execute(customer_id)
    return jsonify(_customer_public(customer))


@bp.post("/v1/auth/login")
def login():
    use_case = Login(
        current_app.config["customer_repository"],
        current_app.config["mfa_repository"],
        current_app.config.get("audit_client"),
    )
    return jsonify(use_case.execute(request.get_json(silent=True) or {}, trace_id=g.trace_id)), 202


@bp.post("/v1/auth/mfa/verify")
def verify_mfa():
    use_case = VerifyMfa(
        current_app.config["mfa_repository"],
        current_app.config["customer_repository"],
        current_app.config.get("audit_client"),
    )
    return jsonify(use_case.execute(request.get_json(silent=True) or {}, trace_id=g.trace_id))


@bp.get("/v1/auth/introspect")
def introspect_token():
    token = _bearer_token()
    if not token.startswith("dev-session-"):
        raise ApiError(401, "invalid_token", "Invalid access token")

    challenge_id = token.removeprefix("dev-session-")
    challenge = current_app.config["mfa_repository"].find_by_id(challenge_id)
    if not challenge or challenge["status"] != "VERIFIED":
        raise ApiError(401, "invalid_token", "Invalid access token")

    return ("", 204)


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-clients-identite"})


def _bearer_token():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "missing_token", "Missing bearer access token")
    return token.strip()
