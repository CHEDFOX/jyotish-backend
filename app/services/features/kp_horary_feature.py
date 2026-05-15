"""
KP HORARY — Number-based instant prediction (1-249 → zodiac entry).

Endpoint: POST /api/public/kp-horary
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import extract_birth, call_llm


router = APIRouter(prefix="/public", tags=["KP Horary"])


def build_kp_horary(number: int, question: str = '', category: str = 'general',
                    latitude: float = 25.35, longitude: float = 74.64) -> Dict:
    from app.services.kp.kp_horary import KPHorary, get_sub_entry

    entry = get_sub_entry(number)

    kp = KPHorary(
        number=number,
        question=question,
        category=category,
        latitude=latitude,
        longitude=longitude,
    )
    result = kp.analyze() or {}
    if not isinstance(result, dict): result = {}

    rp = result.get('ruling_planets', {}) or {}
    if not isinstance(rp, dict): rp = {}

    primary = result.get('primary_house', 1)
    csl_house = result.get('csl_house', 0)
    csl = result.get('cusp_sub_lord', '')

    house_scores = {i: 0 for i in range(1, 13)}
    if csl_house:
        house_scores[csl_house] = house_scores.get(csl_house, 0) + 3
    house_scores[primary] = house_scores.get(primary, 0) + 2
    dominant_house = max(house_scores, key=house_scores.get) if house_scores else 1

    asc = result.get('ascendant', {}) or {}
    if not isinstance(asc, dict): asc = {}

    return {
        'number': number,
        'question': question or '',
        'category': category,
        'ascendant': asc,
        'primary_house': primary,
        'csl': csl,
        'csl_house': csl_house,
        'verdict': result.get('verdict', 'Uncertain'),
        'confidence': result.get('confidence_pct', 50),
        'reasoning': result.get('reasoning', ''),
        'dominant_house': dominant_house,
        'ruling_planets': {k: rp.get(k, '') for k in
                           ('day_lord', 'moon_sign_lord', 'moon_star_lord', 'asc_sign_lord', 'asc_star_lord')},
        'entry': {
            'sign': entry.get('sign', ''),
            'star': entry.get('star', ''),
            'sub_lord': entry.get('sub_lord', ''),
            'degree': round(entry.get('start_deg', 0), 2),
        },
        'query_time': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
    }


def build_horary_prompt(data: Dict, language: str = 'en') -> str:
    rp_lines = [f"{k}: {v}" for k, v in data['ruling_planets'].items() if v]

    return f"""{voice_card(language)}

Someone just asked the universe a question by picking a number. Give them the answer.

NUMBER: {data['number']}
QUESTION: {data['question'] or '(no question — general reading)'}
CATEGORY: {data['category']}

KP analysis:
- Ascendant from number: {data['ascendant'].get('sign', '')} / {data['ascendant'].get('star', '')} / {data['ascendant'].get('sub', '')}
- Primary house: {data['primary_house']}
- Cuspal Sub-Lord: {data['csl']} in house {data['csl_house']}
- Dominant house: {data['dominant_house']}
- Ruling planets: {', '.join(rp_lines)}

VERDICT: {data['verdict']} ({data['confidence']}% confidence)
Reasoning: {data['reasoning']}

Time of question: {data['query_time']}

Write a SHORT reading. 3-4 sentences, under 70 words.

Rules:
- NO astrology jargon. No "cuspal sub-lord", no "house 7", no "significator".
  Speak as if to someone who knows nothing about astrology.
- Deliver the verdict with warmth.
  - YES → name what's coming and when to act.
  - NO → name why the timing isn't right and what to do instead.
  - UNCERTAIN → name what the universe is still deciding.
- End with one surprising or memorable insight."""


class _HoraryRequest(BaseModel):
    number: int
    question: Optional[str] = ''
    category: Optional[str] = 'general'
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/kp-horary')
async def get_kp_horary(request_body: _HoraryRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    if not (1 <= request_body.number <= 249):
        raise HTTPException(status_code=400, detail='Number must be between 1 and 249')

    # Lat/lng priority: explicit > birth_data
    lat = request_body.latitude
    lng = request_body.longitude
    if lat is None or lng is None:
        bd = extract_birth(request_body.kundli_data) or request_body.birth_data or {}
        if isinstance(bd, dict):
            if lat is None: lat = bd.get('lat') or bd.get('latitude')
            if lng is None: lng = bd.get('lng') or bd.get('longitude')
    if lat is None: lat = 25.35
    if lng is None: lng = 74.64

    try:
        language = request_body.language or 'en'

        data = build_kp_horary(
            number=request_body.number,
            question=request_body.question or '',
            category=request_body.category or 'general',
            latitude=float(lat),
            longitude=float(lng),
        )
        prompt = build_horary_prompt(data, language)
        reading = await call_llm(prompt, settings,
                                 user_message="What does this number say?",
                                 max_tokens=400, temperature=0.85)

        return {
            **data,
            'reading': reading,
            'version': 1,
            'cache_ttl_seconds': 0,  # horary is moment-of-question — always fresh
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


kp_horary_router = router
