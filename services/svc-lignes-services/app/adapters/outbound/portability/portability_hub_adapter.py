import time
from datetime import datetime, timedelta, timezone

import requests


class PortabilityHubError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class PortabilityHubAdapter:
    STATUSES = {"pending_out_validation", "approved", "rejected", "port_completed", "cancelled"}

    def __init__(
        self,
        base_url,
        customer_client,
        recipient_operator,
        lead_time_hours=24,
        timeout_seconds=3,
        max_attempts=3,
        session=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.customer_client = customer_client
        self.recipient_operator = recipient_operator
        self.lead_time_hours = lead_time_hours
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.session = session or requests.Session()

    def initiate(self, *, customer_id, msisdn, current_operator, traceparent):
        customer_name = self.customer_client.get_name(customer_id, traceparent)
        requested = datetime.now(timezone.utc) + timedelta(hours=self.lead_time_hours)
        body = {
            "requestType": "port-in",
            "number": msisdn,
            "recipientOperator": self.recipient_operator,
            "currentOperator": current_operator,
            "customerInfo": {"name": customer_name, "accountId": customer_id},
            "requestedPortDate": requested.isoformat().replace("+00:00", "Z"),
        }
        response = self._post("/portability/order", body, traceparent)
        if response.status_code != 201:
            raise PortabilityHubError("HUB_INITIATION_FAILED", f"PortabilityHub HTTP {response.status_code}")
        result = response.json()
        if not result.get("orderId") or result.get("status") not in self.STATUSES:
            raise PortabilityHubError("HUB_INVALID_RESPONSE", "PortabilityHub returned an invalid creation response")
        return result

    def register_webhook(self, callback_url, traceparent, query="PortabilityOrderStateChangeEvent"):
        response = self._post(
            "/portability/hub",
            {"callback": callback_url, "query": query, "@type": "Hub"},
            traceparent,
        )
        if response.status_code != 201:
            raise PortabilityHubError("HUB_SUBSCRIPTION_FAILED", f"PortabilityHub HTTP {response.status_code}")
        return response.json()

    def _post(self, path, body, traceparent):
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.post(
                    f"{self.base_url}{path}",
                    json=body,
                    headers={"Content-Type": "application/json", "traceparent": traceparent},
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                if attempt == self.max_attempts:
                    raise PortabilityHubError("HUB_UNAVAILABLE", "PortabilityHub unavailable") from exc
            else:
                if response.status_code < 500 or attempt == self.max_attempts:
                    return response
            time.sleep(min(0.25 * (2 ** (attempt - 1)), 1.0))
        raise PortabilityHubError("HUB_UNAVAILABLE", "PortabilityHub retry budget exhausted")
