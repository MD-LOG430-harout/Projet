"""Contrast: POST /v1/orders validates the offer with a SYNCHRONOUS call to
svc-catalogue-offres, then hands the rest of the flow to Kafka. Establish a
session while everything is up, wait for the operator to stop the catalogue,
then measure what the same endpoint returns.
"""
import json
import os
import sys
import time
import uuid

import requests

BASE = os.environ.get("BASE", "http://api-gateway")


def main():
    suffix = uuid.uuid4().hex[:12]
    trace = uuid.uuid4().hex
    email = f"syncdown-{suffix}@example.test"
    password = "Stronger123"
    headers = {"TraceId": trace}
    reg = requests.post(
        f"{BASE}/v1/customers/register",
        json={
            "email": email, "password": password, "displayName": "SyncDown",
            "legalName": "SyncDown", "customerType": "individual",
            "address": {"line1": "1 Rue Demo", "city": "Montreal", "province": "QC", "postalCode": "H1A1A1"},
            "identityDocument": {"type": "driver_license", "number": f"SD-{suffix}"},
        },
        headers=headers, timeout=30,
    )
    reg.raise_for_status()
    customer_id = reg.json()["customerId"]
    login = requests.post(f"{BASE}/v1/auth/login", json={"email": email, "password": password}, headers=headers, timeout=30).json()
    mfa = requests.post(f"{BASE}/v1/auth/mfa/verify", json={"challengeId": login["challengeId"], "otp": login["devOtp"]}, headers=headers, timeout=30).json()
    auth = {"Authorization": f"Bearer {mfa['sessionToken']}", "TraceId": trace}
    offer_id = requests.get(f"{BASE}/v1/offers", headers=auth, timeout=30).json()["offers"][0]["offerId"]

    print(json.dumps({"step": "session ready", "offerId": offer_id}), flush=True)
    # The caller stops svc-catalogue-offres during this window.
    time.sleep(int(os.environ.get("WAIT_SECONDS", "20")))

    outcomes = []
    for _ in range(5):
        request_headers = dict(auth)
        request_headers["Idempotency-Key"] = str(uuid.uuid4())
        body = {"customerId": customer_id, "offerId": offer_id, "quantity": 1,
                "orderType": "NEW_PLAN", "numberMode": "NEW"}
        started = time.perf_counter()
        try:
            response = requests.post(f"{BASE}/v1/orders", json=body, headers=request_headers, timeout=60)
            outcomes.append({"status": response.status_code, "ms": round((time.perf_counter() - started) * 1000, 1),
                             "body": response.text[:160]})
        except Exception as exc:
            outcomes.append({"status": "EXCEPTION", "ms": round((time.perf_counter() - started) * 1000, 1),
                             "body": f"{type(exc).__name__}: {exc}"[:160]})
    print(json.dumps({"label": sys.argv[1] if len(sys.argv) > 1 else "sync-dependency-down",
                      "outcomes": outcomes}, indent=2))


if __name__ == "__main__":
    main()
