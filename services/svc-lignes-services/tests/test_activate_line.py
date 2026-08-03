import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVICE = ROOT / "services" / "svc-lignes-services"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SERVICE))
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

from app.main import create_app  # noqa: E402


class Lines:
    def __init__(self):
        self.lines = {}
        self.by_msisdn = {}

    def create(self, line):
        row = line.__dict__.copy()
        self.lines[line.line_id] = row
        self.by_msisdn[line.msisdn] = row

    def find_by_id(self, line_id):
        return self.lines.get(line_id)

    def find_by_msisdn(self, msisdn):
        return self.by_msisdn.get(msisdn)

    def mark_active(self, line_id):
        self.lines[line_id]["status"] = "ACTIVE"
        self.lines[line_id]["hlr_status"] = "PROVISIONED"

    def mark_failed(self, line_id, reason):
        self.lines[line_id]["status"] = "FAILED"
        self.lines[line_id]["hlr_status"] = "FAILED"
        self.lines[line_id]["failure_reason"] = reason


class Hlr:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def provision(self, line, trace_id=None):
        self.calls.append((line, trace_id))
        if self.fail:
            raise RuntimeError("HLR unavailable")
        return True


def test_activate_line_assigns_msisdn_and_marks_active():
    hlr = Hlr()
    app = create_app(Lines(), hlr)
    response = app.test_client().post(
        "/v1/lines/activate",
        json={"customerId": "cust-1", "offerId": "forfait-5g-20gb", "simType": "ESIM"},
        headers={"TraceId": "trace-uc03"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "ACTIVE"
    assert body["hlrStatus"] == "PROVISIONED"
    assert body["msisdn"]
    assert body["numberMode"] == "NEW"
    assert body["portabilityStatus"] is None
    assert hlr.calls[0][1] == "trace-uc03"


def test_activate_line_accepts_simulated_portability_with_existing_number():
    app = create_app(Lines(), Hlr())
    response = app.test_client().post(
        "/v1/lines/activate",
        json={
            "customerId": "cust-1",
            "offerId": "forfait-5g-20gb",
            "simType": "ESIM",
            "numberMode": "PORT_IN",
            "msisdn": "14385551234",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "ACTIVE"
    assert body["msisdn"] == "14385551234"
    assert body["numberMode"] == "PORT_IN"
    assert body["portabilityStatus"] == "ACCEPTED"


def test_activate_line_requires_msisdn_for_simulated_portability():
    app = create_app(Lines(), Hlr())
    response = app.test_client().post(
        "/v1/lines/activate",
        json={
            "customerId": "cust-1",
            "offerId": "forfait-5g-20gb",
            "simType": "ESIM",
            "numberMode": "PORT_IN",
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == "validation_error"
    assert body["details"]["field"] == "msisdn"


def test_activate_line_returns_503_when_hlr_fails():
    app = create_app(Lines(), Hlr(fail=True))
    response = app.test_client().post(
        "/v1/lines/activate",
        json={"customerId": "cust-1", "offerId": "forfait-5g-20gb", "simType": "SIM"},
    )

    assert response.status_code == 503
    assert response.get_json()["code"] == "hlr_provisioning_failed"
