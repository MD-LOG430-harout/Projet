import requests
import hashlib

from services.shared.errors import ApiError
from services.shared.tracing import traceparent_from_trace_id


class ServiceClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _headers(self, trace_id=None):
        headers = {"Content-Type": "application/json"}
        if trace_id:
            headers["TraceId"] = trace_id
            candidate = trace_id.replace("-", "").lower()
            if len(candidate) != 32 or any(char not in "0123456789abcdef" for char in candidate):
                candidate = hashlib.sha256(trace_id.encode("utf-8")).hexdigest()[:32]
            headers["traceparent"] = traceparent_from_trace_id(candidate)
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
