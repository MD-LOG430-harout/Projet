from app.adapters.outbound.http.service_client import ServiceClient


class LineClient(ServiceClient):
    def activate_line(self, payload, trace_id=None):
        response = self.session.post(f"{self.base_url}/v1/lines/activate", headers=self._headers(trace_id), json=payload, timeout=5)
        if response.status_code != 201:
            self._raise(response, "line_activation_failed")
        return response.json()
