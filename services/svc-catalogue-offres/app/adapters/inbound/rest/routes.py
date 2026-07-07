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
    cache = current_app.config.get("offer_cache")
    cache_key = f"catalogue:offer:{offer_id}"
    if cache:
        cached = cache.get_json(cache_key)
        if cached is not None:
            response = jsonify(cached)
            response.headers["X-Cache"] = "HIT"
            return response

    use_case = GetOffer(current_app.config["offer_repository"])
    payload = _offer_public(use_case.execute(offer_id))
    if cache:
        cache.set_json(cache_key, payload)
    response = jsonify(payload)
    response.headers["X-Cache"] = "MISS" if cache else "BYPASS"
    return response


@bp.get("/v1/offers")
def list_offers():
    cache = current_app.config.get("offer_cache")
    cache_key = "catalogue:offers:active"
    if cache:
        cached = cache.get_json(cache_key)
        if cached is not None:
            response = jsonify(cached)
            response.headers["X-Cache"] = "HIT"
            return response

    use_case = ListOffers(current_app.config["offer_repository"])
    payload = {"offers": [_offer_public(offer) for offer in use_case.execute()]}
    if cache:
        cache.set_json(cache_key, payload)
    response = jsonify(payload)
    response.headers["X-Cache"] = "MISS" if cache else "BYPASS"
    return response


@bp.get("/health")
def health():
    return jsonify({"status": "UP", "service": "svc-catalogue-offres"})
