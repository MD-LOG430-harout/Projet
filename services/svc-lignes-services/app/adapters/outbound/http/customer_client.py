import requests


class CustomerLookupError(RuntimeError):
    pass


class CustomerClient:
    def __init__(self, base_url, timeout_seconds=3, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def get_name(self, customer_id, traceparent):
        try:
            response = self.session.get(
                f"{self.base_url}/v1/customers/{customer_id}",
                headers={"traceparent": traceparent},
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise CustomerLookupError("customer lookup unavailable") from exc
        if response.status_code != 200:
            raise CustomerLookupError(f"customer lookup HTTP {response.status_code}")
        body = response.json()
        name = body.get("legalName") or body.get("displayName")
        if not name:
            raise CustomerLookupError("customer lookup returned no name")
        return name
