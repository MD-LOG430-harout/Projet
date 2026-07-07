from app.adapters.outbound.http.service_client import ServiceClient


class LineClient(ServiceClient):
    def get_line_by_msisdn(self, msisdn, trace_id=None):
        response = self.session.get(f"{self.base_url}/v1/lines/by-msisdn/{msisdn}", headers=self._headers(trace_id), timeout=3)
        if response.status_code != 200:
            self._raise(response, "line_validation_failed")
        return response.json()
