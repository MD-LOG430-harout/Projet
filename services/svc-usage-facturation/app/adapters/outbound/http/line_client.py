import requests

from app.adapters.outbound.http.service_client import ServiceClient


class LineClient(ServiceClient):
    def get_line_by_msisdn(self, msisdn, trace_id=None):
        response = requests.get(f"{self.base_url}/v1/lines/by-msisdn/{msisdn}", headers=self._headers(trace_id), timeout=5)
        if response.status_code != 200:
            self._raise(response, "line_validation_failed")
        return response.json()
