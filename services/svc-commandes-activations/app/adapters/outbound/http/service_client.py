import requests

from services.shared.errors import ApiError


class ServiceClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def _headers(self, trace_id=None):
        headers = {"Content-Type": "application/json"}
        if trace_id:
            headers["TraceId"] = trace_id
        return headers

    def _raise(self, response, fallback_code):
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        code = payload.get("code") or fallback_code
        message = payload.get("message") or response.text or fallback_code
        details = payload.get("details") or {}
        raise ApiError(response.status_code, code, message, details)
