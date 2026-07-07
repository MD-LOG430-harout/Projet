import requests


class AuditClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def record(self, event, trace_id=None):
        headers = {"Content-Type": "application/json"}
        if trace_id:
            headers["TraceId"] = trace_id
        try:
            self.session.post(f"{self.base_url}/v1/audit-events", json=event, headers=headers, timeout=2)
        except requests.RequestException:
            return None
        return None
