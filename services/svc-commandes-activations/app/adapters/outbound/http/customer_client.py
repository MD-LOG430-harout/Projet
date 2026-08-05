import time
from collections import OrderedDict
from threading import Lock

from app.adapters.outbound.http.service_client import ServiceClient


class CustomerClient(ServiceClient):
    def __init__(self, base_url, ttl_seconds=60, max_entries=10000):
        super().__init__(base_url)
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache = OrderedDict()
        self._lock = Lock()

    def get_customer(self, customer_id, trace_id=None):
        cached = self._get_cached(customer_id)
        if cached:
            return cached

        response = self.session.get(f"{self.base_url}/v1/customers/{customer_id}", headers=self._headers(trace_id), timeout=3)
        if response.status_code != 200:
            self._raise(response, "customer_validation_failed")
        customer = response.json()
        self._set_cached(customer_id, customer)
        return customer

    def _get_cached(self, customer_id):
        if self.ttl_seconds <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            item = self._cache.get(customer_id)
            if not item:
                return None
            expires_at, customer = item
            if expires_at <= now:
                self._cache.pop(customer_id, None)
                return None
            self._cache.move_to_end(customer_id)
            return dict(customer)

    def _set_cached(self, customer_id, customer):
        if self.ttl_seconds <= 0:
            return
        with self._lock:
            self._cache[customer_id] = (time.monotonic() + self.ttl_seconds, dict(customer))
            self._cache.move_to_end(customer_id)
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)
