import time
from threading import Lock

from app.adapters.outbound.http.service_client import ServiceClient


class OfferClient(ServiceClient):
    def __init__(self, base_url, ttl_seconds=60):
        super().__init__(base_url)
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._lock = Lock()

    def get_offer(self, offer_id, trace_id=None):
        cached = self._get_cached(offer_id)
        if cached:
            return cached

        response = self.session.get(f"{self.base_url}/v1/offers/{offer_id}", headers=self._headers(trace_id), timeout=3)
        if response.status_code != 200:
            self._raise(response, "offer_validation_failed")
        offer = response.json()
        self._set_cached(offer_id, offer)
        return offer

    def _get_cached(self, offer_id):
        if self.ttl_seconds <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            item = self._cache.get(offer_id)
            if not item:
                return None
            expires_at, offer = item
            if expires_at <= now:
                self._cache.pop(offer_id, None)
                return None
            return dict(offer)

    def _set_cached(self, offer_id, offer):
        if self.ttl_seconds <= 0:
            return
        with self._lock:
            self._cache[offer_id] = (time.monotonic() + self.ttl_seconds, dict(offer))
