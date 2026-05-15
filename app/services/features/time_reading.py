"""
TIME — Today, this week, this month.

Calculates current transits, dasha, panchanga, and day lord.
LLM produces 3 segments: today + week + month readings.

Endpoint: POST /api/public/time-reading
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, split_segments,
)


router = APIRouter(prefix="/public", tags=["Time Reading"])


WEEKDAY_LORDS = {0: 'Moon', 1: 'Mars', 2: 'Mercury', 3: 'Jupiter', 4: 'Venus', 5: 'Saturn', 6: 'Sun'}


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


def build_time_reading(engine) -> Dict:
    now = datetime.now()
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    transits = safe(engine.get_current_transits, {}) or {}
    if not isinstance(transits, dict): transits = {}

    natal_moon = _pl(planets, 'Moon')
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}

    dasha = safe(engine.get_vimshottari_dasha, {}) or {}
    if not isinstance(dasha, dict): dasha = {}
    maha = dasha.get('mahadasha', {}) or {}
    if not isinstance(maha, dict): maha = {}

    day_lord = WEEKDAY_LORDS.get(now.weekday(), '')

    t_moon = transits.get('Moon', {}) if isinstance(transits.get('Moon'), dict) else {}
    t_sun = transits.get('Sun', {}) if isinstance(transits.get('Sun'), dict) else {}

    retros = [
        p for p, d in transits.items()
        if isinstance(d, dict) and (d.get('retrograde') or d.get('is_retrograde'))
    ]

    panchanga = safe(engine.get_panchanga, {}) or {}
    if not isinstance(panchanga, dict): panchanga = {}
    tithi = panchanga.get('tithi', {}) if isinstance(panchanga.get('tithi'), dict) else {}

    transit_positions = {}
    for pname in ('Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu'):
        tp = transits.get(pname, {})
        if isinstance(tp, dict):
            transit_positions[pname] = {
                'sign': tp.get('rashi_name', ''),
                'retro': bool(tp.get('retrograde') or tp.get('is_retrograde')),
            }

    week_end = now + timedelta(days=7)
    if now.month < 12:
        next_month_first = datetime(now.year, now.month + 1, 1)
    else:
        next_month_first = datetime(now.year + 1, 1, 1)
    days_left = (next_month_first - now).days

    return {
        'today': {
            'date': now.strftime('%A, %B %d'),
            'day_lord': day_lord,
            'moon_sign': t_moon.get('rashi_name', ''),
            'moon_nakshatra': t_moon.get('nakshatra_name', ''),
            'sun_sign': t_sun.get('rashi_name', ''),
            'tithi': tithi.get('name', ''),
            'paksha': tithi.get('paksha', ''),
            'retrogrades': retros,
        },
        'week': {
            'range': f"{now.strftime('%b %d')} – {week_end.strftime('%b %d')}",
            'transit_positions': transit_positions,
        },
        'month': {
            'name': now.strftime('%B %Y'),
            'days_left': days_left,
            'sun_sign': t_sun.get('rashi_name', ''),
            'dasha': dasha.get('dasha_string', ''),
            'maha_lord': maha.get('lord', ''),
        },
        'natal': {
            'ascendant': asc.get('rashi_name', ''),
            'moon_sign': natal_moon.get('rashi_name', ''),
        },
    }


def build_time_prompt(data: Dict, language: str = 'en') -> str:
    t = data['today']
    w = data['week']
    m = data['month']
    n = data['natal']

    transit_str = ', '.join(
        f"{k} in {v['sign']}{' (R)' if v['retro'] else ''}"
        for k, v in w['transit_positions'].items()
    )

    return f"""{voice_card(language)}

You are reading time for this person — today, this week, this month.

PERSON: {n['ascendant']} ascendant, natal Moon in {n['moon_sign']}
Active dasha: {m['dasha']} (mahalord {m['maha_lord']})

TODAY ({t['date']}):
- Day lord: {t['day_lord']}
- Moon transiting: {t['moon_sign']} ({t['moon_nakshatra']})
- Sun: {t['sun_sign']} | Tithi: {t['tithi']} {t['paksha']}
- Retrograde: {', '.join(t['retrogrades']) or 'none'}

THIS WEEK ({w['range']}):
- Key transits: {transit_str or 'standard motion'}

THIS MONTH ({m['name']}, {m['days_left']} days left):
- Sun in {m['sun_sign']}
- Dasha: {m['dasha']}

Write THREE short readings, separated by exactly ---

1. TODAY (2-3 sentences): What today feels like for THIS person. Reference the day lord and Moon transit. One specific thing to lean into.
2. THIS WEEK (2-3 sentences): The arc of the week. What's building or releasing. One key shift.
3. THIS MONTH (2-3 sentences): The bigger picture. What this month is asking. How the dasha colors everything.

Rules:
- Mix astrology with plain language ("Moon in Gemini means your mind won't sit still" not "the lunar transit activates your third house")
- Reference their ascendant or Moon sign
- No headers, no labels
- Separate the 3 sections with exactly ---
- Under 150 words total"""


class _TimeRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/time-reading')
async def get_time_reading(request_body: _TimeRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_time_reading(engine)
        prompt = build_time_prompt(data, language)
        raw = await call_llm(prompt, settings,
                             user_message="Read today, this week, this month.",
                             max_tokens=900, temperature=0.85)
        segments = split_segments(raw)

        today_read = segments[0] if len(segments) > 0 else ''
        week_read = segments[1] if len(segments) > 1 else ''
        month_read = segments[2] if len(segments) > 2 else ''

        return {
            'today': {**data['today'], 'reading': today_read},
            'week': {**data['week'], 'reading': week_read},
            'month': {**data['month'], 'reading': month_read},
            'natal': data['natal'],
            'version': 1,
            'cache_ttl_seconds': 3600,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


time_reading_router = router
