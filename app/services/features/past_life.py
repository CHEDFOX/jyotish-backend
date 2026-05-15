"""
PAST LIFE — Who you were before this birth.

Endpoint: POST /api/public/past-life
"""

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, split_segments,
)


router = APIRouter(prefix="/public", tags=["Past Life"])


def build_past_life(engine) -> Dict:
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    def _pl(name):
        p = planets.get(name, {})
        return p if isinstance(p, dict) else {}

    ketu = _pl('Ketu')
    rahu = _pl('Rahu')
    saturn = _pl('Saturn')
    moon = _pl('Moon')
    sun = _pl('Sun')

    dignity = safe(engine.get_planetary_dignity, {}) or {}
    house_lords = dignity.get('house_lords', {}) or {}
    lord_12 = house_lords.get('12') or house_lords.get(12) or ''
    lord_5 = house_lords.get('5') or house_lords.get(5) or ''

    planets_in_12 = [n for n, d in planets.items() if isinstance(d, dict) and d.get('house') == 12]
    planets_in_5 = [n for n, d in planets.items() if isinstance(d, dict) and d.get('house') == 5]

    return {
        'ketu': {'sign': ketu.get('rashi_name', ''), 'house': ketu.get('house', 0), 'nakshatra': ketu.get('nakshatra_name', '')},
        'rahu': {'sign': rahu.get('rashi_name', ''), 'house': rahu.get('house', 0), 'nakshatra': rahu.get('nakshatra_name', '')},
        'saturn': {'sign': saturn.get('rashi_name', ''), 'house': saturn.get('house', 0)},
        'moon_sign': moon.get('rashi_name', ''),
        'sun_sign': sun.get('rashi_name', ''),
        'house_12_lord': lord_12,
        'planets_in_12': planets_in_12,
        'house_5_lord': lord_5,
        'planets_in_5': planets_in_5,
    }


def build_past_life_prompt(data: Dict, language: str = 'en') -> str:
    p12 = ', '.join(data['planets_in_12']) or 'none'
    p5 = ', '.join(data['planets_in_5']) or 'none'

    return f"""{voice_card(language)}

You are revealing this person's past life.

INDICATORS:
- Ketu (what the soul mastered, who they were): {data['ketu']['sign']}, house {data['ketu']['house']}, nakshatra {data['ketu']['nakshatra']}
- Rahu (what they lacked, what they crave now): {data['rahu']['sign']}, house {data['rahu']['house']}
- Saturn (karmic debt carried forward): {data['saturn']['sign']}, house {data['saturn']['house']}
- 12th house lord (past life dissolution): {data['house_12_lord']}
- Planets in 12th: {p12}
- 5th house lord (purva punya, past life merit): {data['house_5_lord']}
- Planets in 5th: {p5}
- Moon (emotional memory): {data['moon_sign']}
- Sun (soul continuity): {data['sun_sign']}

Write a CINEMATIC past life story in EXACTLY 5 short segments, separated by ---

1. Set the scene. Where and when. The world they lived in.
2. Who they were. Their daily life. Their nature.
3. The peak — a vivid moment, a scene worth painting. (Image-break segment.)
4. The fall or departure. What was left unfinished.
5. The thread to now. Why this soul chose THIS life.

Rules:
- 2-3 SHORT lines per segment. Not paragraphs.
- Separate segments with exactly ---
- No headers, no "Segment 1:" labels
- Second person ("You were...")
- Specific to THIS chart. Not generic.
- Total under 200 words."""


class _PastLifeRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/past-life')
async def get_past_life(request_body: _PastLifeRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'
        data = build_past_life(engine)
        prompt = build_past_life_prompt(data, language)
        raw = await call_llm(prompt, settings, user_message='Reveal this past life.',
                             max_tokens=1200, temperature=0.85)
        segments = split_segments(raw)

        return {
            'segments': segments,
            'past_life_data': {
                'ketu': data['ketu'],
                'rahu': data['rahu'],
                'saturn': data['saturn'],
            },
            'version': 1,
            'cache_ttl_seconds': 604800,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


past_life_router = router
