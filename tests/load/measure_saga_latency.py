"""Measure the synchronous vs event-driven behaviour of the running CanTelcoX stack.

Run inside the test container, on the compose network:
  BASE=http://api-gateway python measure.py <label>
"""
import json
import os
import statistics
import sys
import time
import uuid

import requests

BASE = os.environ.get("BASE", "http://api-gateway")
N = int(os.environ.get("N", "20"))


def session():
    suffix = uuid.uuid4().hex[:12]
    trace = uuid.uuid4().hex
    email = f"perf-{suffix}@example.test"
    password = "Stronger123"
    headers = {"TraceId": trace}
    reg = requests.post(
        f"{BASE}/v1/customers/register",
        json={
            "email": email, "password": password, "displayName": "Perf",
            "legalName": "Perf", "customerType": "individual",
            "address": {"line1": "1 Rue Demo", "city": "Montreal", "province": "QC", "postalCode": "H1A1A1"},
            "identityDocument": {"type": "driver_license", "number": f"PERF-{suffix}"},
        },
        headers=headers, timeout=30,
    )
    reg.raise_for_status()
    customer_id = reg.json()["customerId"]
    login = requests.post(f"{BASE}/v1/auth/login", json={"email": email, "password": password}, headers=headers, timeout=30).json()
    mfa = requests.post(f"{BASE}/v1/auth/mfa/verify", json={"challengeId": login["challengeId"], "otp": login["devOtp"]}, headers=headers, timeout=30).json()
    auth = {"Authorization": f"Bearer {mfa['sessionToken']}", "TraceId": trace}
    offers = requests.get(f"{BASE}/v1/offers", headers=auth, timeout=30).json()["offers"]
    return customer_id, offers[0]["offerId"], auth


def percentile(values, p):
    ordered = sorted(values)
    index = min(int(round((p / 100) * len(ordered) + 0.5)) - 1, len(ordered) - 1)
    return ordered[index]


def post_order(customer_id, offer_id, auth):
    headers = dict(auth)
    headers["Idempotency-Key"] = str(uuid.uuid4())
    body = {"customerId": customer_id, "offerId": offer_id, "quantity": 1,
            "orderType": "NEW_PLAN", "numberMode": "NEW"}
    started = time.perf_counter()
    response = requests.post(f"{BASE}/v1/orders", json=body, headers=headers, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    return response, elapsed


def wait_terminal(order_id, auth, timeout=60):
    started = time.perf_counter()
    while time.perf_counter() - started < timeout:
        status = requests.get(f"{BASE}/v1/orders/{order_id}/status", headers=auth, timeout=30).json()["status"]
        if status != "EN_COURS":
            return status, (time.perf_counter() - started) * 1000
        time.sleep(0.1)
    return "TIMEOUT", timeout * 1000


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    customer_id, offer_id, auth = session()
    acceptance, completion, statuses, codes = [], [], [], []
    for _ in range(N):
        response, elapsed = post_order(customer_id, offer_id, auth)
        codes.append(response.status_code)
        acceptance.append(elapsed)
        if response.status_code == 202:
            status, converged = wait_terminal(response.json()["orderId"], auth)
            statuses.append(status)
            completion.append(converged)
    result = {
        "label": label,
        "samples": N,
        "statusCodes": {str(code): codes.count(code) for code in sorted(set(codes))},
        "acceptanceMsP50": round(percentile(acceptance, 50), 1),
        "acceptanceMsP95": round(percentile(acceptance, 95), 1),
        "acceptanceMsMean": round(statistics.mean(acceptance), 1),
        "terminalStates": {state: statuses.count(state) for state in sorted(set(statuses))},
        "completionMsP50": round(percentile(completion, 50), 1) if completion else None,
        "completionMsP95": round(percentile(completion, 95), 1) if completion else None,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
