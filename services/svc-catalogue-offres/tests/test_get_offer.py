import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-catalogue-offres"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.main import create_app


class Offers:
    def list_active(self):
        return [
            {
                "offer_id": "forfait-5g-20gb",
                "name": "CanTelcoX 5G 20 Go",
                "monthly_price": 45.00,
                "data_gb": 20,
                "status": "ACTIVE",
            },
            {
                "offer_id": "forfait-5g-50gb",
                "name": "CanTelcoX 5G 50 Go",
                "monthly_price": 65.00,
                "data_gb": 50,
                "status": "ACTIVE",
            },
        ]

    def find_by_id(self, offer_id):
        if offer_id == "forfait-5g-20gb":
            return {
                "offer_id": offer_id,
                "name": "CanTelcoX 5G 20 Go",
                "monthly_price": 45.00,
                "data_gb": 20,
                "status": "ACTIVE",
            }
        return None


def test_get_offer_returns_seed_shape():
    app = create_app(Offers())
    response = app.test_client().get("/v1/offers/forfait-5g-20gb")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ACTIVE"


def test_list_offers_returns_active_offers():
    app = create_app(Offers())
    response = app.test_client().get("/v1/offers")

    assert response.status_code == 200
    body = response.get_json()
    assert len(body["offers"]) == 2
    assert body["offers"][0]["status"] == "ACTIVE"


def test_get_offer_returns_404_for_unknown_offer():
    app = create_app(Offers())
    response = app.test_client().get("/v1/offers/missing")

    assert response.status_code == 404
    assert response.get_json()["code"] == "offer_not_found"
