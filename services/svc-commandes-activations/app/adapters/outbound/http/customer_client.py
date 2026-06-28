import requests

from app.adapters.outbound.http.service_client import ServiceClient


class CustomerClient(ServiceClient):
    def get_customer(self, customer_id, trace_id=None):
        response = requests.get(f"{self.base_url}/v1/customers/{customer_id}", headers=self._headers(trace_id), timeout=5)
        if response.status_code != 200:
            self._raise(response, "customer_validation_failed")
        return response.json()
