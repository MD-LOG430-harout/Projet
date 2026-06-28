import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-lignes-services"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.adapters.outbound.hlr import free5gc_hlr_adapter
from app.adapters.outbound.hlr.free5gc_hlr_adapter import Free5gcHlrAdapter
from app.domain.model.line import Line


class Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def line():
    return Line(
        line_id="line-1",
        customer_id="cust-1",
        offer_id="forfait-5g-20gb",
        msisdn="14385551234",
        sim_type="ESIM",
        sim_identifier="EID-1",
        imsi="208930000000001",
        supi="imsi-208930000000001",
        status="PENDING",
        hlr_status="PENDING",
    )


def adapter():
    return Free5gcHlrAdapter("http://free5gc", "admin", "free5gc", "20893")


def test_complete_subscriber_lookup_does_not_write(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return Response(200, {"token": "jwt"})

    def get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return Response(
            200,
            {
                "AuthenticationSubscription": {
                    "authenticationMethod": "5G_AKA",
                    "permanentKey": {"permanentKeyValue": "key"},
                },
                "AccessAndMobilitySubscriptionData": {"gpsis": ["msisdn-14385551234"]},
            },
        )

    monkeypatch.setattr(free5gc_hlr_adapter.requests, "post", post)
    monkeypatch.setattr(free5gc_hlr_adapter.requests, "get", get)

    assert adapter().provision(line()) is True
    assert [call[0] for call in calls] == ["POST", "GET"]


def test_empty_subscriber_shell_is_updated_with_full_profile(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return Response(200, {"token": "jwt"})

    def get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return Response(
            200,
            {
                "ueId": "imsi-208930000000001",
                "AuthenticationSubscription": {"authenticationMethod": "", "permanentKey": None},
                "AccessAndMobilitySubscriptionData": {},
            },
        )

    def put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return Response(200)

    monkeypatch.setattr(free5gc_hlr_adapter.requests, "post", post)
    monkeypatch.setattr(free5gc_hlr_adapter.requests, "get", get)
    monkeypatch.setattr(free5gc_hlr_adapter.requests, "put", put)

    assert adapter().provision(line()) is True

    methods = [call[0] for call in calls]
    assert methods == ["POST", "GET", "PUT"]
    payload = calls[-1][2]["json"]
    assert payload["ueId"] == "imsi-208930000000001"
    assert payload["AccessAndMobilitySubscriptionData"]["gpsis"] == ["msisdn-14385551234"]


def test_missing_subscriber_is_created(monkeypatch):
    calls = []

    def post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return Response(200, {"token": "jwt"} if url.endswith("/api/login") else {})

    def get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return Response(404)

    monkeypatch.setattr(free5gc_hlr_adapter.requests, "post", post)
    monkeypatch.setattr(free5gc_hlr_adapter.requests, "get", get)

    assert adapter().provision(line()) is True
    assert [call[0] for call in calls] == ["POST", "GET", "POST"]
