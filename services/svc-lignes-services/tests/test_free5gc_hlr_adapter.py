import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-lignes-services"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.adapters.outbound.hlr.free5gc_hlr_adapter import Free5gcHlrAdapter  # noqa: E402
from app.domain.model.line import Line  # noqa: E402


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


def adapter(session=None):
    return Free5gcHlrAdapter(
        "http://free5gc", "admin", "free5gc", "20893",
        "key", "opc", "sequence", session=session,
    )


def test_complete_subscriber_lookup_does_not_write():
    calls = []

    class Session:
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url.endswith("/api/login"):
                return Response(200, {"token": "jwt"})
            return Response(200, {
                "ueId": "imsi-208930000000001",
                "AuthenticationSubscription": {
                    "authenticationMethod": "5G_AKA",
                    "permanentKey": {"permanentKeyValue": "key"},
                    "opc": {"opcValue": "opc"},
                },
                "AccessAndMobilitySubscriptionData": {"gpsis": ["msisdn-14385551234"]},
            })

    assert adapter(Session()).provision(line(), trace_id="1" * 32)["created"] is False
    assert [call[0] for call in calls] == ["POST", "GET"]


def test_conflicting_subscriber_fails_without_put():
    calls = []

    class Session:
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url.endswith("/api/login"):
                return Response(200, {"token": "jwt"})
            return Response(200, {
                "ueId": "imsi-208930000000001",
                "AuthenticationSubscription": {"authenticationMethod": "", "permanentKey": None},
                "AccessAndMobilitySubscriptionData": {},
            })

    import pytest
    with pytest.raises(RuntimeError, match="conflicts"):
        adapter(Session()).provision(line(), trace_id="1" * 32)
    assert [call[0] for call in calls] == ["POST", "GET"]


def test_missing_subscriber_is_created():
    calls = []

    class Session:
        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url.endswith("/api/login"):
                return Response(200, {"token": "jwt"})
            if method == "GET":
                return Response(404)
            return Response(201)

    assert adapter(Session()).provision(line(), trace_id="1" * 32)["created"] is True
    assert [call[0] for call in calls] == ["POST", "GET", "POST"]
