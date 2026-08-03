import os
import time
import uuid
from datetime import datetime, timezone

import pymysql
import pytest
import requests


BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8080")
HUB_URL = os.getenv("E2E_HUB_URL", "http://localhost:8282")


def available():
    try:
        return requests.get(f"{BASE_URL}/health", timeout=2).status_code == 200 and requests.get(f"{HUB_URL}/actuator/health", timeout=2).status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not available(), reason="Full Phase 2 stack unavailable")


def connect_lines():
    return pymysql.connect(
        host=os.getenv("E2E_MYSQL_HOST", "127.0.0.1"), user="cantelcox",
        password=os.getenv("MYSQL_PASSWORD", "cantelcox_dev"), database="lignes_services",
        cursorclass=pymysql.cursors.DictCursor,
    )


def connect_payments():
    return pymysql.connect(
        host=os.getenv("E2E_MYSQL_HOST", "127.0.0.1"), user="cantelcox",
        password=os.getenv("MYSQL_PASSWORD", "cantelcox_dev"), database="usage_facturation",
        cursorclass=pymysql.cursors.DictCursor,
    )


def identity_and_offer():
    password = "Stronger123"
    email = f"port-{uuid.uuid4().hex[:12]}@example.test"
    trace_id = uuid.uuid4().hex
    registered = requests.post(
        f"{BASE_URL}/v1/customers/register",
        json={
            "email": email, "password": password, "displayName": "Portability Test", "legalName": "Portability Test",
            "customerType": "individual", "address": {"line1": "1 Test", "city": "Montreal", "province": "QC", "postalCode": "H1A1A1"},
            "identityDocument": {"type": "driver_license", "number": uuid.uuid4().hex},
        }, headers={"TraceId": trace_id}, timeout=10,
    )
    registered.raise_for_status()
    login = requests.post(f"{BASE_URL}/v1/auth/login", json={"email": email, "password": password}, timeout=10).json()
    mfa = requests.post(f"{BASE_URL}/v1/auth/mfa/verify", json={"challengeId": login["challengeId"], "otp": login["devOtp"]}, timeout=10)
    mfa.raise_for_status()
    headers = {"Authorization": f"Bearer {mfa.json()['sessionToken']}", "TraceId": trace_id}
    offer = requests.get(f"{BASE_URL}/v1/offers", headers=headers, timeout=10).json()["offers"][0]["offerId"]
    return registered.json()["customerId"], offer, headers


def place_port_order():
    customer_id, offer_id, headers = identity_and_offer()
    msisdn = f"15{uuid.uuid4().int % 10_000_000_000:010d}"
    response = requests.post(
        f"{BASE_URL}/v1/orders",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"customerId": customer_id, "offerId": offer_id, "quantity": 1, "orderType": "NEW_PLAN", "numberMode": "PORT_IN", "msisdnDemande": msisdn, "currentOperator": "BSS2"},
        timeout=10,
    )
    assert response.status_code == 202
    return response.json()["orderId"], headers


def wait_correlation(order_id):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        with connect_lines() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM portability_correlations WHERE id_commande=%s", (order_id,))
                row = cursor.fetchone()
                if row:
                    return row
        time.sleep(0.25)
    raise AssertionError("portability correlation was not created")


def wait_status(order_id, headers, expected):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = requests.get(f"{BASE_URL}/v1/orders/{order_id}/status", headers=headers, timeout=10)
        if response.status_code == 200 and response.json()["status"] == expected:
            return response.json()
        time.sleep(0.25)
    raise AssertionError(f"order did not reach {expected}")


def test_supplied_hub_portability_success():
    order_id, headers = place_port_order()
    correlation = wait_correlation(order_id)
    response = requests.post(
        f"{HUB_URL}/portability/order/{correlation['hub_order_id']}/validate-out",
        json={"status": "approved", "confirmedPortDate": datetime.now(timezone.utc).isoformat(), "notes": "E2E"},
        timeout=10,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "port_completed"
    wait_status(order_id, headers, "CONFIRMEE")


def test_supplied_hub_portability_rejection_compensates():
    order_id, headers = place_port_order()
    correlation = wait_correlation(order_id)
    response = requests.post(
        f"{HUB_URL}/portability/order/{correlation['hub_order_id']}/validate-out",
        json={"status": "rejected", "rejectionReason": "E2E rejection", "notes": "E2E"},
        timeout=10,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    wait_status(order_id, headers, "ANNULEE")


@pytest.mark.skipif(os.getenv("E2E_PAYMENT_REFUSAL") != "true", reason="payment refusal profile not enabled")
def test_payment_refusal_cancels_without_authorization():
    customer_id, offer_id, headers = identity_and_offer()
    response = requests.post(
        f"{BASE_URL}/v1/orders", headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"customerId": customer_id, "offerId": offer_id, "quantity": 1, "orderType": "NEW_PLAN"}, timeout=10,
    )
    assert response.status_code == 202
    order_id = response.json()["orderId"]
    wait_status(order_id, headers, "ANNULEE")
    with connect_payments() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM order_saga_payments WHERE order_id=%s", (order_id,))
            assert cursor.fetchone()["status"] == "REFUSE"


@pytest.mark.skipif(os.getenv("E2E_EXPECT_ACTIVATION_FAILURE") != "true", reason="free5GC failure profile not enabled")
def test_free5gc_failure_cancels_and_refunds():
    customer_id, offer_id, headers = identity_and_offer()
    response = requests.post(
        f"{BASE_URL}/v1/orders", headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"customerId": customer_id, "offerId": offer_id, "quantity": 1, "orderType": "NEW_PLAN"}, timeout=10,
    )
    assert response.status_code == 202
    order_id = response.json()["orderId"]
    wait_status(order_id, headers, "ANNULEE")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with connect_payments() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT status FROM order_saga_payments WHERE order_id=%s", (order_id,))
                row = cursor.fetchone()
                if row and row["status"] == "REMBOURSE":
                    return
        time.sleep(0.25)
    raise AssertionError("authorized payment was not refunded")
