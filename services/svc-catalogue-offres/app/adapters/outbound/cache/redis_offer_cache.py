import json
import time
from threading import Lock


class RedisOfferCache:
    def __init__(self, redis_url, ttl_seconds):
        import redis

        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = int(ttl_seconds)
        self._local = {}
        self._lock = Lock()

    def get_json(self, key):
        cached = self._get_local(key)
        if cached is not None:
            return cached

        try:
            raw = self.client.get(key)
            if raw is None:
                return None
            value = json.loads(raw)
            self._set_local(key, value)
            return value
        except Exception:
            return None

    def set_json(self, key, value):
        self._set_local(key, value)
        try:
            self.client.setex(key, self.ttl_seconds, json.dumps(value))
        except Exception:
            return

    def _get_local(self, key):
        now = time.monotonic()
        with self._lock:
            item = self._local.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._local.pop(key, None)
                return None
            return value

    def _set_local(self, key, value):
        with self._lock:
            self._local[key] = (time.monotonic() + self.ttl_seconds, value)
