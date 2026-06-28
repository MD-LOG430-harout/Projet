import requests


class AuditClient:
    def __init__(self, base_url, timeout_seconds=2):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def record(self, event, trace_id=None):
        headers = {}
        if trace_id:
            headers["TraceId"] = trace_id
        response = requests.post(
            f"{self.base_url}/v1/audit-events",
            json=event,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

