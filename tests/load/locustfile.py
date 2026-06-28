import random
import string

from locust import HttpUser, between, task


def _suffix(length=8):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


class CanTelcoXFirstSliceUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self):
        self.email = f"load-{_suffix()}@example.test"
        self.password = "Stronger123"
        self.customer_id = None
        self.challenge_id = None
        self.dev_otp = None
        self.session_token = None

    @task(3)
    def register_login_and_mfa(self):
        trace = f"locust-{_suffix()}"
        register_response = self.client.post(
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
        )
        if register_response.status_code in (201, 409):
            if register_response.status_code == 201:
                self.customer_id = register_response.json().get("customerId")
        else:
            return

        login_response = self.client.post(
            "/v1/auth/login",
            json={"email": self.email, "password": self.password},
            headers={"TraceId": trace},
            name="UC-02 login",
        )
        if login_response.status_code != 202:
            return

        login_payload = login_response.json()
        self.challenge_id = login_payload.get("challengeId")
        self.dev_otp = login_payload.get("devOtp")
        if not self.challenge_id or not self.dev_otp:
            return

        verified_response = self.client.post(
            "/v1/auth/mfa/verify",
            json={"challengeId": self.challenge_id, "otp": self.dev_otp},
            headers={"TraceId": trace},
            name="UC-02 MFA verify",
        )
        if verified_response.status_code == 200:
            self.session_token = verified_response.json().get("sessionToken")

    @task(2)
    def append_audit_event(self):
        if not self.session_token:
            return
        self.client.post(
            "/v1/audit-events",
            json={
                "eventType": "LOAD_TEST_EVENT",
                "actorId": "locust",
                "customerId": self.customer_id,
                "resourceId": "load-test",
                "sourceService": "locust",
                "result": "SUCCESS",
                "metadata": {"scenario": "first-slice"},
            },
            headers={
                "Authorization": f"Bearer {self.session_token}",
                "TraceId": f"locust-{_suffix()}",
            },
            name="Audit append",
        )

    @task(1)
    def validate_customer(self):
        if not self.customer_id:
            return
        if not self.session_token:
            return
        self.client.get(
            f"/v1/customers/{self.customer_id}",
            headers={
                "Authorization": f"Bearer {self.session_token}",
                "TraceId": f"locust-{_suffix()}",
            },
            name="Customer validation",
        )
