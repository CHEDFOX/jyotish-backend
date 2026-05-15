"""
TODAY'S SKY — Single-day reading.

Quick read of the day's energy: day lord, Moon transit, tithi, yoga, retrogrades.
LLM produces ONE flowing 80-word reading.

Endpoint: POST /api/public/today-sky
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm,
)


router = APIRouter(prefix="/public", tags=["Today Sky"])


WEEKDAY_LORDS = {
    0: ('Moon', 'Monday'), 1: ('Mars', 'Tuesday'), 2: ('Mercury', 'Wednesday'),
    3: ('Jupiter', 'Thursday'), 4: ('Venus', 'Friday'), 5: ('Saturn', 'Saturday'),
    6: ('Sun', 'Sunday'),
}


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


def build_today_sky(engine) -> Dict:
    now = datetime.now()
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    transits = safe(engine.get_current_transits, {}) or {}
    if not isinstance(transits, dict): transits = {}

    day_idx = now.weekday()
    day_lord, day_name = WEEKDAY_LORDS.get(day_idx, ('', ''))

    t_moon = transits.get('Moon', {}) if isinstance(transits.get('Moon'), dict) else {}
    t_sun = transits.get('Sun', {}) if isinstance(transits.get('Sun'), dict) else {}

    natal_moon = _pl(planets, 'Moon')
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}

    dasha = safe(engine.get_vimshottari_dasha, {}) or {}
    if not isinstance(dasha, dict): dasha = {}
    maha = dasha.get('mahadasha', {}) if isinstance(dasha.get('mahadasha'), dict) else {}

    panchanga = safe(engine.get_panchanga, {}) or {}
    if not isinstance(panchanga, dict): panchanga = {}
    tithi = panchanga.get('tithi', {}) if isinstance(panchanga.get('tithi'), dict) else {}
    yoga_p = panchanga.get('yoga', {}) if isinstance(panchanga.get('yoga'), dict) else {}
    karana = panchanga.get('karana', {}) if isinstance(panchanga.get('karana'), dict) else {}

    retros = [
        p for p, d in transits.items()
        if isinstance(d, dict) and (d.get('retrograde') or d.get('is_retrograde'))
    ]

    natal_day_lord = _pl(planets, day_lord)

    return {
        'date': now.strftime('%A, %B %d, %Y'),
        'day_lord': day_lord,
        'day_name': day_name,
        'day_lord_house': natal_day_lord.get('house', 0),
        'day_lord_sign': natal_day_lord.get('rashi_name', ''),
        'moon_transit': t_moon.get('rashi_name', ''),
        'moon_nakshatra': t_moon.get('nakshatra_name', ''),
        'sun_transit': t_sun.get('rashi_name', ''),
        'natal_moon': natal_moon.get('rashi_name', ''),
        'tithi': tithi.get('name', ''),
        'paksha': tithi.get('paksha', ''),
        'yoga': yoga_p.get('name', ''),
        'karana': karana.get('name', ''),
        'dasha': dasha.get('dasha_string', ''),
        'maha_lord': maha.get('lord', ''),
        'retro_planets': retros,
        'ascendant': asc.get('rashi_name', ''),
    }


def build_today_prompt(data: Dict, language: str = 'en') -> str:
    return f"""{voice_card(language)}

You are telling this person about TODAY.

DATE: {data['date']}
PERSON: {data['ascendant']} ascendant, natal Moon in {data['natal_moon']}
Active dasha: {data['dasha']} (maha lord {data['maha_lord']})

TODAY:
- Day lord: {data['day_lord']} ({data['day_name']}) — in their chart at house {data['day_lord_house']} in {data['day_lord_sign']}
- Moon transiting: {data['moon_transit']} ({data['moon_nakshatra']})
- Sun transiting: {data['sun_transit']}
- Tithi: {data['tithi']} {data['paksha']} | Yoga: {data['yoga']} | Karana: {data['karana']}
- Retrograde: {', '.join(data['retro_planets']) or 'none'}

Write a SHORT reading about today. 3-5 sentences, under 80 words.
Flowing text — like a wise friend telling them what to expect.
Mention the day lord and how it touches their chart, plus the Moon's transit.
If a planet is retrograde, mention it briefly.
End with one gentle suggestion or affirmation.

No headers, no bullets, no labels. Just warm precise prose."""


class _SkyRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/today-sky')
async def get_today_sky(request_body: _SkyRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_today_sky(engine)
        prompt = build_today_prompt(data, language)
        reading = await call_llm(prompt, settings,
                                 user_message="What does today hold?",
                                 max_tokens=400, temperature=0.85)

        return {
            **data,
            'reading': reading,
            'version': 1,
            'cache_ttl_seconds': 3600,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


today_sky_router = router
