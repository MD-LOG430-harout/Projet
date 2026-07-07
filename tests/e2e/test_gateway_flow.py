import uuid

import pytest
import requests


BASE_URL = "http://localhost:8080"


def _gateway_available():
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(
    not _gateway_available(),
    reason="API Gateway is not running on http://localhost:8080",
)


def test_official_phase1_gateway_flow():
    trace_id = f"e2e-{uuid.uuid4()}"
    password = "Stronger123"
    email = f"e2e-{uuid.uuid4().hex[:12]}@example.test"

    register = requests.post(
        f"{BASE_URL}/v1/customers/register",
        json={
            "email": email,
            "password": password,
            "displayName": "E2E Test",
            "legalName": "E2E Test",
            "customerType": "individual",
            "address": {
                "line1": "123 Rue Test",
                "city": "Montreal",
                "province": "QC",
                "postalCode": "H1A1A1",
            },
            "identityDocument": {
                "type": "driver_license",
                "number": f"E2E-{uuid.uuid4().hex[:10]}",
            },
        },
        headers={"TraceId": trace_id},
        timeout=10,
    )
    assert register.status_code == 201
    customer_id = register.json()["customerId"]

    login = requests.post(
        f"{BASE_URL}/v1/auth/login",
        json={"email": email, "password": password},
        headers={"TraceId": trace_id},
        timeout=10,
    )
    assert login.status_code == 202
    login_body = login.json()

    mfa = requests.post(
        f"{BASE_URL}/v1/auth/mfa/verify",
        json={"challengeId": login_body["challengeId"], "otp": login_body["devOtp"]},
        headers={"TraceId": trace_id},
        timeout=10,
    )
    assert mfa.status_code == 200
    token = mfa.json()["sessionToken"]
    auth_headers = {"Authorization": f"Bearer {token}", "TraceId": trace_id}

    offers = requests.get(f"{BASE_URL}/v1/offers", headers=auth_headers, timeout=10)
    assert offers.status_code == 200
    offer_id = offers.json()["offers"][0]["offerId"]

    order_key = f"e2e-order-{uuid.uuid4()}"
    order_payload = {
        "customerId": customer_id,
        "offerId": offer_id,
        "quantity": 1,
        "orderType": "NEW_PLAN",
    }
    order_headers = {**auth_headers, "Idempotency-Key": order_key}
    order = requests.post(f"{BASE_URL}/v1/orders", json=order_payload, headers=order_headers, timeout=10)
    assert order.status_code == 201
    order_id = order.json()["orderId"]

    order_replay = requests.post(f"{BASE_URL}/v1/orders", json=order_payload, headers=order_headers, timeout=10)
    assert order_replay.status_code in (200, 201)
    assert order_replay.json()["orderId"] == order_id

    activation_key = f"e2e-activation-{uuid.uuid4()}"
    activation_payload = {
        "customerId": customer_id,
        "offerId": offer_id,
        "simType": "ESIM",
        "numberMode": "NEW",
        "msisdn": f"1438{str(uuid.uuid4().int)[:7]}",
    }
    activation_headers = {**auth_headers, "Idempotency-Key": activation_key}
    activation = requests.post(
        f"{BASE_URL}/v1/activations",
        json=activation_payload,
        headers=activation_headers,
        timeout=15,
    )
    assert activation.status_code == 201
    activation_id = activation.json()["activationId"]

    activation_replay = requests.post(
        f"{BASE_URL}/v1/activations",
        json=activation_payload,
        headers=activation_headers,
        timeout=15,
    )
    assert activation_replay.status_code in (200, 201)
    assert activation_replay.json()["activationId"] == activation_id

    invoices = requests.get(f"{BASE_URL}/v1/invoices?customerId={customer_id}", headers=auth_headers, timeout=10)
    assert invoices.status_code == 200
    invoice = invoices.json()["invoices"][0]

    payment_key = f"e2e-payment-{uuid.uuid4()}"
    payment_payload = {
        "customerId": customer_id,
        "paymentMethod": "SIMULATED_CARD",
        "amount": invoice["amountDue"],
        "currency": invoice["currency"],
    }
    payment_headers = {**auth_headers, "Idempotency-Key": payment_key}
    payment = requests.post(
        f"{BASE_URL}/v1/invoices/{invoice['invoiceId']}/payments",
        json=payment_payload,
        headers=payment_headers,
        timeout=10,
    )
    assert payment.status_code == 201
    payment_id = payment.json()["paymentId"]

    payment_replay = requests.post(
        f"{BASE_URL}/v1/invoices/{invoice['invoiceId']}/payments",
        json=payment_payload,
        headers=payment_headers,
        timeout=10,
    )
    assert payment_replay.status_code in (200, 201)
    assert payment_replay.json()["paymentId"] == payment_id

    audit = requests.get(f"{BASE_URL}/v1/audit-events?traceId={trace_id}", headers=auth_headers, timeout=10)
    assert audit.status_code == 200
    assert audit.json()["events"]
