"""
STRINGS ENDPOINT — UI labels per language. English fallback for missing keys.

Endpoint: GET /api/public/strings?lang=en
"""

from typing import Dict

from fastapi import APIRouter, Request

from app.services.strings.data import (
    STRINGS, STRINGS_VERSION, STRINGS_UPDATED_AT, SUPPORTED_LANGUAGES,
)


router = APIRouter(prefix="/public", tags=["Strings"])


@router.get('/strings')
async def get_strings(request: Request, lang: str = 'en') -> Dict:
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    lang_key = (lang or 'en').lower()
    if lang_key not in STRINGS:
        lang_key = 'en'

    # Merge English defaults with target language so missing keys fall back
    merged = {**STRINGS.get('en', {}), **STRINGS.get(lang_key, {})}

    return {
        'version': STRINGS_VERSION,
        'updated_at': STRINGS_UPDATED_AT,
        'language': lang_key,
        'supported_languages': SUPPORTED_LANGUAGES,
        'strings': merged,
        'cache_ttl_seconds': 86400,
    }


strings_router = router
