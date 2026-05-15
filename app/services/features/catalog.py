"""
CATALOG ENDPOINT — Returns the filtered, ordered list of sections + groups.

Endpoint: GET /api/public/catalog?lang=en&app_version=2.5.0&platform=ios

Frontend boot: fetch this, render every section in order, call its endpoint
to populate. Hide whatever isn't in the response.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict

from fastapi import APIRouter, Request

from app.services.catalog.data import SECTIONS, GROUPS, CATALOG_VERSION, CATALOG_UPDATED_AT


router = APIRouter(prefix="/public", tags=["Catalog"])


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def _version_tuple(v: str) -> tuple:
    """Best-effort semver parse. '2.5.0' → (2, 5, 0). Bad input → (0,)."""
    try:
        return tuple(int(p) for p in v.split('.') if p.isdigit())
    except (AttributeError, ValueError):
        return (0,)


def _within_window(section: Dict, now: datetime) -> bool:
    sd = _parse_iso(section.get('start_date'))
    ed = _parse_iso(section.get('end_date'))
    if sd and now < sd:
        return False
    if ed and now > ed:
        return False
    return True


def _passes_version(section: Dict, app_version: Optional[str]) -> bool:
    mav = section.get('min_app_version')
    if not mav or not app_version:
        return True
    return _version_tuple(app_version) >= _version_tuple(mav)


def _passes_platform(section: Dict, platform: Optional[str]) -> bool:
    allowed = section.get('platforms')
    if not allowed:
        return True
    if not platform:
        return True
    return platform.lower() in [p.lower() for p in allowed]


@router.get('/catalog')
async def get_catalog(
    request: Request,
    lang: str = 'en',
    app_version: Optional[str] = None,
    platform: Optional[str] = None,
) -> Dict:
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    now = datetime.now(timezone.utc)

    filtered: List[Dict] = []
    for s in SECTIONS:
        if not s.get('visible', True):
            continue
        if not _within_window(s, now):
            continue
        if not _passes_version(s, app_version):
            continue
        if not _passes_platform(s, platform):
            continue
        filtered.append(s)

    filtered.sort(key=lambda s: (s.get('group', ''), s.get('position', 9999)))
    groups_sorted = sorted(GROUPS, key=lambda g: g.get('position', 9999))

    return {
        'version': CATALOG_VERSION,
        'updated_at': CATALOG_UPDATED_AT,
        'language': lang,
        'app_version': app_version,
        'platform': platform,
        'now': now.isoformat(),
        'groups': groups_sorted,
        'sections': filtered,
        'cache_ttl_seconds': 3600,  # frontend re-fetches every hour
    }


catalog_router = router
