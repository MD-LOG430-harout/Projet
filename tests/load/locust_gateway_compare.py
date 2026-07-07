import os
import uuid

from locust import between, task
from locust.contrib.fasthttp import FastHttpUser


WAIT_MIN_SECONDS = float(os.getenv("WAIT_MIN_SECONDS", "0.01"))
WAIT_MAX_SECONDS = float(os.getenv("WAIT_MAX_SECONDS", "0.05"))


class GatewayComparisonUser(FastHttpUser):
    """Direct-vs-gateway comparison for the same read endpoint.

    This scenario intentionally measures only GET /v1/offers so section 10.8
    compares routing overhead and traceability without mixing in workflow setup.
    """

    wait_time = between(WAIT_MIN_SECONDS, WAIT_MAX_SECONDS)

    def _headers(self):
        headers = {"TraceId": f"gateway-compare-{uuid.uuid4()}"}
        token = os.getenv("AUTH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @task
    def consult_offers(self):
        with self.client.get(
            "/v1/offers",
            headers=self._headers(),
            name="GET /v1/offers",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected 200, got {response.status_code}")
