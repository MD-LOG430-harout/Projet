import requests

from app.adapters.outbound.http.service_client import ServiceClient


class OfferClient(ServiceClient):
    def get_offer(self, offer_id, trace_id=None):
        response = requests.get(f"{self.base_url}/v1/offers/{offer_id}", headers=self._headers(trace_id), timeout=5)
        if response.status_code != 200:
            self._raise(response, "offer_validation_failed")
        return response.json()
