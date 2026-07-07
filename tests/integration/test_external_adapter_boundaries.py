import importlib
import os
import pathlib
import sys
import uuid
from contextlib import contextmanager

import pytest
import requests


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE_DIRS = {
    "lines": ROOT / "services" / "svc-lignes-services",
    "billing": ROOT / "services" / "svc-usage-facturation",
}


@contextmanager
def _service_import(service_key):
    service_path = str(SERVICE_DIRS[service_key])
    root_path = str(ROOT)
    previous_path = list(sys.path)
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.path.insert(0, root_path)
    sys.path.insert(0, service_path)
    try:
        yield importlib.import_module
    finally:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.path[:] = previous_path


def test_simulated_payment_gateway_adapter_accepts_and_rejects_payments():
    with _service_import("billing") as module:
        SimulatedPaymentGateway = module(
            "app.adapters.outbound.payment.simulated_payment_gateway"
        ).SimulatedPaymentGateway

        accepted = SimulatedPaymentGateway().charge({"invoiceId": "inv-integration"}, trace_id="it-payment")
        assert accepted["status"] == "ACCEPTED"
        assert accepted["gatewayTransactionId"] == "sim-inv-integration"

        with pytest.raises(RuntimeError, match="simulated payment gateway unavailable"):
            SimulatedPaymentGateway(force_failure=True).charge(
                {"invoiceId": "inv-integration"},
                trace_id="it-payment-failure",
            )


def _free5gc_live_enabled():
    return os.getenv("FREE5GC_LIVE_TEST") == "1"


def _free5gc_available(base_url):
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/login",
            json={
                "username": os.getenv("FREE5GC_USERNAME", "admin"),
                "password": os.getenv("FREE5GC_PASSWORD", "free5gc"),
            },
            timeout=2,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


@pytest.mark.skipif(
    not _free5gc_live_enabled()
    or not _free5gc_available(os.getenv("FREE5GC_WEBUI_URL", "http://localhost:5050")),
    reason="Set FREE5GC_LIVE_TEST=1 and start free5GC WebConsole to run live adapter integration",
)
def test_free5gc_hlr_adapter_live_provisions_subscriber_boundary():
    suffix = int(uuid.uuid4().hex[:10], 16) % 10_000_000_000
    imsi = f"20893{suffix:010d}"
    supi = f"imsi-{imsi}"
    msisdn = f"1438{suffix % 1_000_000_000:09d}"

    with _service_import("lines") as module:
        Line = module("app.domain.model.line").Line
        Free5gcHlrAdapter = module("app.adapters.outbound.hlr.free5gc_hlr_adapter").Free5gcHlrAdapter

        adapter = Free5gcHlrAdapter(
            os.getenv("FREE5GC_WEBUI_URL", "http://localhost:5050"),
            os.getenv("FREE5GC_USERNAME", "admin"),
            os.getenv("FREE5GC_PASSWORD", "free5gc"),
            os.getenv("FREE5GC_PLMN", "20893"),
        )

        assert adapter.provision(
            Line(
                line_id=str(uuid.uuid4()),
                customer_id=str(uuid.uuid4()),
                offer_id="forfait-5g-20gb",
                msisdn=msisdn,
                sim_type="ESIM",
                sim_identifier=f"EID-{uuid.uuid4().hex[:18].upper()}",
                imsi=imsi,
                supi=supi,
                status="PENDING",
                hlr_status="PENDING",
            ),
            trace_id=f"it-free5gc-{uuid.uuid4()}",
        )

