"""
Simple in-memory rate limiter for API endpoints.
"""

import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException


class RateLimiter:

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup(self):
        now = time.time()
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        cutoff = now - 3600
        keys_to_delete = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._requests[key]

    def check(self, key: str, limit: int, window: int = 3600) -> bool:
        now = time.time()
        cutoff = now - window

        with self._lock:
            self._cleanup()
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]

            if len(self._requests[key]) >= limit:
                return False

            self._requests[key].append(now)
            return True

    def remaining(self, key: str, limit: int, window: int = 3600) -> int:
        now = time.time()
        cutoff = now - window
        with self._lock:
            active = [t for t in self._requests.get(key, []) if t > cutoff]
            return max(0, limit - len(active))


rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request, endpoint: str, limit: int):
    # Bypass for localhost (development/testing)
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "localhost", "::1"):
        return
    ip = get_client_ip(request)
    key = f"{endpoint}:{ip}"

    if not rate_limiter.check(key, limit):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {limit}/hour.",
                "retry_after_seconds": 60,
            },
        )
