import random
import string
import time
import uuid
import os
from itertools import count
from threading import Lock

from locust import FastHttpUser, HttpUser, between, task


STEADY_STATE_ONLY = os.getenv("LOCUST_STEADY_STATE_ONLY", "false").lower() == "true"
PHASE2_ORDERS_ONLY = os.getenv("LOCUST_PHASE2_ORDERS_ONLY", "false").lower() == "true"

_msisdn_counter = count()


def _suffix(length=8):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def _msisdn():
    seed = int(time.time() * 1000) + next(_msisdn_counter) + (uuid.uuid4().int % 1_000_000_000)
    return f"1438{seed % 1_000_000_000:09d}"


def _json(response):
    try:
        return response.json()
    except ValueError:
        return {}


class CanTelcoXPhase1User(HttpUser):
    """Gateway-only Phase 1 Golden Signals load scenario.

    The teacher's section 5.2 load-test paths are UC-03, UC-04, UC-05, and
    UC-08, with UC-02 when MFA setup is needed. This project implements UC-03
    and UC-05, with UC-02 for authenticated setup. UC-04 and UC-08 are out of
    scope, so they are not included in the official load scenario.
    """

    wait_time = between(
        float(os.getenv("LOCUST_WAIT_MIN_SECONDS", "0.0")),
        float(os.getenv("LOCUST_WAIT_MAX_SECONDS", "0.02")),
    )

    def on_start(self):
        self.email = f"load-{_suffix()}@example.test"
        self.password = "Stronger123"
        self.customer_id = None
        self.session_token = None
        self.offer_id = "forfait-5g-20gb"
        self._register_and_login()

    def _auth_headers(self, trace):
        return {
            "Authorization": f"Bearer {self.session_token}",
            "TraceId": trace,
        }

    def _trace(self):
        return f"locust-{_suffix(12)}"

    def _register_and_login(self):
        trace = self._trace()
        with self.client.post(
            "/v1/customers/register",
            json={
                "email": self.email,
                "password": self.password,
                "displayName": "Load Test",
                "legalName": "Load Test",
                "address": {
                    "line1": "123 Rue Charge",
                    "city": "Montreal",
                    "province": "QC",
                    "postalCode": "H1A1A1",
                },
                "identityDocument": {
                    "type": "driver_license",
                    "number": f"SIM-QC-{_suffix(10)}",
                },
                "customerType": "individual",
            },
            headers={"TraceId": trace},
            name="UC-01 register",
            catch_response=True,
        ) as register_response:
            if register_response.status_code != 201:
                register_response.failure(f"expected 201, got {register_response.status_code}")
                return
            self.customer_id = _json(register_response).get("customerId")
            if not self.customer_id:
                register_response.failure("missing customerId")
                return

        if register_response.status_code != 201:
            return

        with self.client.post(
            "/v1/auth/login",
            json={"email": self.email, "password": self.password},
            headers={"TraceId": trace},
            name="UC-02 login",
            catch_response=True,
        ) as login_response:
            if login_response.status_code != 202:
                login_response.failure(f"expected 202, got {login_response.status_code}")
                return
            login_payload = _json(login_response)

        challenge_id = login_payload.get("challengeId")
        dev_otp = login_payload.get("devOtp")
        if not challenge_id or not dev_otp:
            return

        with self.client.post(
            "/v1/auth/mfa/verify",
            json={"challengeId": challenge_id, "otp": dev_otp},
            headers={"TraceId": trace},
            name="UC-02 MFA verify",
            catch_response=True,
        ) as verified_response:
            if verified_response.status_code != 200:
                verified_response.failure(f"expected 200, got {verified_response.status_code}")
                return
            self.session_token = _json(verified_response).get("sessionToken")
            if not self.session_token:
                verified_response.failure("missing sessionToken")

    @task(80)
    def consult_offers(self):
        if not self.session_token:
            return
        trace = self._trace()
        with self.client.get(
            "/v1/offers",
            headers=self._auth_headers(trace),
            name="UC-05 consult offers",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected 200, got {response.status_code}")

    @task(1)
    def create_order_idempotent_replay(self):
        if not self.customer_id or not self.session_token:
            return
        trace = self._trace()
        idempotency_key = f"locust-order-{_suffix(12)}"
        body = {
            "customerId": self.customer_id,
            "offerId": self.offer_id,
            "quantity": 1,
            "orderType": "NEW_PLAN",
        }
        headers = self._auth_headers(trace)
        headers["Idempotency-Key"] = idempotency_key
        order_id = None
        with self.client.post(
            "/v1/orders",
            json=body,
            headers=headers,
            name="UC-05 create order",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"expected 202, got {response.status_code}")
                return
            order_id = _json(response).get("orderId")
            if not order_id:
                response.failure("missing orderId")
                return

        with self.client.post(
            "/v1/orders",
            json=body,
            headers=headers,
            name="UC-05 order replay",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"expected 202, got {response.status_code}")
                return
            if _json(response).get("orderId") != order_id:
                response.failure("idempotency replay returned a different orderId")

    @task(1)
    def activate_line_idempotent_replay(self):
        if not self.customer_id or not self.session_token:
            return
        trace = self._trace()
        idempotency_key = f"locust-activation-{_suffix(12)}"
        body = {
            "customerId": self.customer_id,
            "offerId": self.offer_id,
            "simType": "ESIM",
            "numberMode": "NEW",
            "msisdn": _msisdn(),
        }
        headers = self._auth_headers(trace)
        headers["Idempotency-Key"] = idempotency_key
        activation_id = None
        with self.client.post(
            "/v1/activations",
            json=body,
            headers=headers,
            name="UC-03 activation",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"expected 201, got {response.status_code}")
                return
            activation_id = _json(response).get("activationId")
            if not activation_id:
                response.failure("missing activationId")
                return

        with self.client.post(
            "/v1/activations",
            json=body,
            headers=headers,
            name="UC-03 activation replay",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"expected 200/201, got {response.status_code}")
                return
            if _json(response).get("activationId") != activation_id:
                response.failure("idempotency replay returned a different activationId")


class CanTelcoXSteadyStateOffersUser(FastHttpUser):
    _shared_token = None
    _shared_token_lock = Lock()

    wait_time = between(
        float(os.getenv("LOCUST_WAIT_MIN_SECONDS", "0.0")),
        float(os.getenv("LOCUST_WAIT_MAX_SECONDS", "0.0")),
    )

    def on_start(self):
        self.session_token = self._get_shared_token()

    def _trace(self):
        return f"steady-{_suffix(12)}"

    def _get_shared_token(self):
        if CanTelcoXSteadyStateOffersUser._shared_token:
            return CanTelcoXSteadyStateOffersUser._shared_token
        with CanTelcoXSteadyStateOffersUser._shared_token_lock:
            if not CanTelcoXSteadyStateOffersUser._shared_token:
                CanTelcoXSteadyStateOffersUser._shared_token = self._register_and_login()
            return CanTelcoXSteadyStateOffersUser._shared_token

    def _register_and_login(self):
        trace = self._trace()
        email = f"steady-{_suffix()}@example.test"
        password = "Stronger123"
        register_response = self.client.post(
            "/v1/customers/register",
            json={
                "email": email,
                "password": password,
                "displayName": "Steady Test",
                "legalName": "Steady Test",
                "address": {
                    "line1": "123 Rue Charge",
                    "city": "Montreal",
                    "province": "QC",
                    "postalCode": "H1A1A1",
                },
                "identityDocument": {
                    "type": "driver_license",
                    "number": f"SIM-QC-{_suffix(10)}",
                },
                "customerType": "individual",
            },
            headers={"TraceId": trace},
            name="setup register",
        )
        if register_response.status_code != 201:
            return None
        login_response = self.client.post(
            "/v1/auth/login",
            json={"email": email, "password": password},
            headers={"TraceId": trace},
            name="setup login",
        )
        if login_response.status_code != 202:
            return None
        login_payload = _json(login_response)
        verified_response = self.client.post(
            "/v1/auth/mfa/verify",
            json={"challengeId": login_payload.get("challengeId"), "otp": login_payload.get("devOtp")},
            headers={"TraceId": trace},
            name="setup MFA verify",
        )
        if verified_response.status_code == 200:
            return _json(verified_response).get("sessionToken")
        return None

    @task
    def consult_offers(self):
        if not self.session_token:
            return
        with self.client.get(
            "/v1/offers",
            headers={"Authorization": f"Bearer {self.session_token}", "TraceId": self._trace()},
            name="steady consult offers",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected 200, got {response.status_code}")


class CanTelcoXPhase2OrdersUser(FastHttpUser):
    _shared_customer_id = None
    _shared_token = None
    _shared_setup_lock = Lock()

    wait_time = between(
        float(os.getenv("LOCUST_WAIT_MIN_SECONDS", "0.0")),
        float(os.getenv("LOCUST_WAIT_MAX_SECONDS", "0.0")),
    )

    def on_start(self):
        self.customer_id, self.session_token = self._get_shared_setup()
        self.offer_id = os.getenv("LOCUST_OFFER_ID", "forfait-5g-20gb")

    def _trace(self):
        return f"phase2-{_suffix(12)}"

    def _get_shared_setup(self):
        if CanTelcoXPhase2OrdersUser._shared_customer_id and CanTelcoXPhase2OrdersUser._shared_token:
            return CanTelcoXPhase2OrdersUser._shared_customer_id, CanTelcoXPhase2OrdersUser._shared_token
        with CanTelcoXPhase2OrdersUser._shared_setup_lock:
            if not CanTelcoXPhase2OrdersUser._shared_customer_id or not CanTelcoXPhase2OrdersUser._shared_token:
                customer_id, token = self._register_and_login()
                CanTelcoXPhase2OrdersUser._shared_customer_id = customer_id
                CanTelcoXPhase2OrdersUser._shared_token = token
            return CanTelcoXPhase2OrdersUser._shared_customer_id, CanTelcoXPhase2OrdersUser._shared_token

    def _register_and_login(self):
        trace = self._trace()
        email = f"phase2-{_suffix()}@example.test"
        password = "Stronger123"
        register_response = self.client.post(
            "/v1/customers/register",
            json={
                "email": email,
                "password": password,
                "displayName": "Phase 2 Locust",
                "legalName": "Phase 2 Locust",
                "address": {
                    "line1": "123 Rue Charge",
                    "city": "Montreal",
                    "province": "QC",
                    "postalCode": "H1A1A1",
                },
                "identityDocument": {
                    "type": "driver_license",
                    "number": f"SIM-QC-{_suffix(10)}",
                },
                "customerType": "individual",
            },
            headers={"TraceId": trace},
            name="setup phase2 register",
        )
        if register_response.status_code != 201:
            return None, None
        customer_id = _json(register_response).get("customerId")
        login_response = self.client.post(
            "/v1/auth/login",
            json={"email": email, "password": password},
            headers={"TraceId": trace},
            name="setup phase2 login",
        )
        if login_response.status_code != 202:
            return None, None
        login_payload = _json(login_response)
        verified_response = self.client.post(
            "/v1/auth/mfa/verify",
            json={"challengeId": login_payload.get("challengeId"), "otp": login_payload.get("devOtp")},
            headers={"TraceId": trace},
            name="setup phase2 MFA verify",
        )
        if verified_response.status_code != 200:
            return None, None
        return customer_id, _json(verified_response).get("sessionToken")

    @task
    def create_order(self):
        if not self.customer_id or not self.session_token:
            return
        trace = self._trace()
        headers = {
            "Authorization": f"Bearer {self.session_token}",
            "TraceId": trace,
            "Idempotency-Key": f"locust-phase2-order-{_suffix(16)}",
        }
        with self.client.post(
            "/v1/orders",
            json={
                "customerId": self.customer_id,
                "offerId": self.offer_id,
                "quantity": 1,
                "orderType": "NEW_PLAN",
                "numberMode": "NEW",
            },
            headers=headers,
            name="Phase2 event-driven create order",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"expected 202, got {response.status_code}")
                return
            body = _json(response)
            if not body.get("orderId") or not body.get("sagaId") or body.get("status") != "EN_COURS":
                response.failure("missing event-driven order acceptance fields")


if PHASE2_ORDERS_ONLY:
    CanTelcoXPhase1User.abstract = True
    CanTelcoXSteadyStateOffersUser.abstract = True
elif STEADY_STATE_ONLY:
    CanTelcoXPhase1User.abstract = True
    CanTelcoXPhase2OrdersUser.abstract = True
else:
    CanTelcoXSteadyStateOffersUser.abstract = True
    CanTelcoXPhase2OrdersUser.abstract = True
