"""
PANCHANGA — Daily astro snapshot (tithi, nakshatra, yoga, karana + muhurta windows).

Cached by (date, hour-bucket, ~1km coordinates) for fast repeat hits.

Endpoint: GET /api/public/panchanga?lat=...&lon=...
"""

from datetime import datetime
from functools import lru_cache
from typing import Dict

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/public", tags=["Panchanga"])


@lru_cache(maxsize=256)
def _engine_for_panchanga(year: int, month: int, day: int, hour: int, lat_x100: int, lon_x100: int):
    from app.services.jyotish_engine import JyotishEngine
    return JyotishEngine(
        datetime(year, month, day, hour, 0),
        lat_x100 / 100.0,
        lon_x100 / 100.0,
    )


def _get_lean_panchanga(lat: float, lon: float) -> Dict:
    now = datetime.now()
    # Round to ~1km lat/lon + hour bucket so two requests from the same city
    # in the same hour share the same engine instance.
    lat_x = int(round(lat * 100))
    lon_x = int(round(lon * 100))
    engine = _engine_for_panchanga(now.year, now.month, now.day, now.hour, lat_x, lon_x)

    panch = engine.get_panchanga() or {}
    muhurta = engine.get_muhurta() or {}
    if not isinstance(panch, dict): panch = {}
    if not isinstance(muhurta, dict): muhurta = {}

    auspicious = muhurta.get('auspicious', {}) if isinstance(muhurta.get('auspicious'), dict) else {}
    inauspicious = muhurta.get('inauspicious', {}) if isinstance(muhurta.get('inauspicious'), dict) else {}

    tithi = panch.get('tithi', {}) if isinstance(panch.get('tithi'), dict) else {}

    return {
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M'),
        'lat': lat,
        'lon': lon,
        'tithi': {
            'name': tithi.get('name') or tithi.get('tithi_name', ''),
            'number': tithi.get('number', 0),
            'paksha': tithi.get('paksha', ''),
        },
        'nakshatra': panch.get('nakshatra', {}),
        'yoga': panch.get('yoga', {}),
        'karana': panch.get('karana', {}),
        'sunrise': muhurta.get('sunrise', ''),
        'sunset': muhurta.get('sunset', ''),
        'auspicious': {
            'abhijit': auspicious.get('abhijit', ''),
            'brahma_muhurta': auspicious.get('brahma_muhurta', ''),
        },
        'inauspicious': {
            'rahu_kalam': inauspicious.get('rahu_kalam', ''),
            'yamaganda': inauspicious.get('yamaganda', ''),
            'gulika': inauspicious.get('gulika', ''),
        },
        'version': 1,
        'cache_ttl_seconds': 1800,  # 30 min; panchanga shifts slowly
    }


@router.get('/panchanga')
async def get_panchanga(lat: float = 28.6139, lon: float = 77.2090):
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail='Invalid coordinates')
    try:
        return _get_lean_panchanga(lat, lon)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


panchanga_router = router
