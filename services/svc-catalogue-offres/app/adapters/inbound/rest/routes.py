from decimal import Decimal

from flask import Blueprint, current_app, jsonify

from app.application.queries.get_offer import GetOffer
from app.application.queries.list_offers import ListOffers


bp = Blueprint("catalogue_offres", __name__)


def _offer_public(offer):
    def value(name):
        return offer.get(name) if isinstance(offer, dict) else getattr(offer, name)

    monthly_price = value("monthly_price")
    if isinstance(monthly_price, Decimal):
        monthly_price = float(monthly_price)
    return {
        "offerId": value("offer_id"),
        "name": value("name"),
        "monthlyPrice": monthly_price,
        "dataGb": value("data_gb"),
        "status": value("status"),
    }


@bp.get("/v1/offers/<offer_id>")
def get_offer(offer_id):
    use_case = GetOffer(current_app.config["offer_repository"])
    return jsonify(_offer_public(use_case.execute(offer_id)))


@bp.get("/v1/offers")
def list_offers():
    use_case = ListOffers(current_app.config["offer_repository"])
    return jsonify({"offers": [_offer_public(offer) for offer in use_case.execute()]})


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-catalogue-offres"})
