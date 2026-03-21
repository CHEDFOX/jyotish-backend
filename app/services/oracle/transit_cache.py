"""
ORACLE — TRANSIT CACHE
Current sky is same for everyone. Calculate once, share.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from ..core.ephemeris import get_ephemeris


class TransitCache:
    def __init__(self, ttl_hours: int = 6):
        self._transits = None
        self._timestamp = None
        self._ttl = timedelta(hours=ttl_hours)

    def get(self) -> Optional[Dict]:
        if self._transits and self._timestamp and datetime.now() - self._timestamp < self._ttl:
            return self._transits
        return None

    def refresh(self) -> Dict:
        eph = get_ephemeris()
        self._transits = eph.get_current_transits()
        self._timestamp = datetime.now()
        return self._transits

    def get_or_refresh(self) -> Dict:
        cached = self.get()
        if cached:
            return cached
        return self.refresh()


_transit_cache = TransitCache()


def get_current_transits():
    return _transit_cache.get_or_refresh()
