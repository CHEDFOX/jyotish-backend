"""
FIVE ELEMENTS — Your relationship with Wood, Fire, Earth, Metal, Water.

Endpoint: POST /api/public/five-elements
"""

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, split_segments,
)


router = APIRouter(prefix="/public", tags=["Five Elements"])


PRODUCTION_ORDER = ['Wood', 'Fire', 'Earth', 'Metal', 'Water']
GENERATES = {'Wood': 'Fire', 'Fire': 'Earth', 'Earth': 'Metal', 'Metal': 'Water', 'Water': 'Wood'}
CONTROLS  = {'Wood': 'Earth', 'Earth': 'Water', 'Water': 'Fire', 'Fire': 'Metal', 'Metal': 'Wood'}

ELEMENT_FACTS = {
    'Wood':  {'color': '#4A8C5C', 'season': 'Spring',      'direction': 'East',   'organ': 'Liver/Gallbladder',     'emotion': 'Anger', 'taste': 'Sour',    'virtue': 'Benevolence'},
    'Fire':  {'color': '#CC4444', 'season': 'Summer',      'direction': 'South',  'organ': 'Heart/Small Intestine', 'emotion': 'Joy',   'taste': 'Bitter',  'virtue': 'Propriety'},
    'Earth': {'color': '#B8860B', 'season': 'Late Summer', 'direction': 'Center', 'organ': 'Spleen/Stomach',        'emotion': 'Worry', 'taste': 'Sweet',   'virtue': 'Faithfulness'},
    'Metal': {'color': '#A0A0A0', 'season': 'Autumn',      'direction': 'West',   'organ': 'Lungs/Large Intestine', 'emotion': 'Grief', 'taste': 'Pungent', 'virtue': 'Righteousness'},
    'Water': {'color': '#3366AA', 'season': 'Winter',      'direction': 'North',  'organ': 'Kidneys/Bladder',       'emotion': 'Fear',  'taste': 'Salty',   'virtue': 'Wisdom'},
}


def build_five_elements(engine) -> Dict:
    from app.services.chinese.bazi import BaZiChart
    from app.services.chinese.advanced import calculate_yong_shen

    bazi = BaZiChart(engine.birth_dt)
    balance = bazi.get_element_balance() or {}
    if not isinstance(balance, dict): balance = {}
    counts = balance.get('counts', {}) or {}
    if not isinstance(counts, dict): counts = {}

    dm_element = balance.get('day_master_element', '')
    dm_strength = 'Strong' if balance.get('strong', False) else 'Weak'
    total = sum(counts.values()) or 1

    yong = safe(lambda: calculate_yong_shen(dm_element, counts, dm_strength), {}) or {}
    if not isinstance(yong, dict): yong = {}
    yong_element = yong.get('yong_shen', '')
    ji_element = yong.get('ji_shen', '')

    elements = []
    for elem in PRODUCTION_ORDER:
        count = counts.get(elem, 0)
        pct = round((count / total) * 100)

        if elem == dm_element:
            relation = 'self'
        elif GENERATES.get(elem) == dm_element:
            relation = 'resource'
        elif GENERATES.get(dm_element) == elem:
            relation = 'output'
        elif CONTROLS.get(elem) == dm_element:
            relation = 'power'
        elif CONTROLS.get(dm_element) == elem:
            relation = 'wealth'
        else:
            relation = 'neutral'

        is_yong = elem == yong_element
        is_ji = elem == ji_element
        if is_yong: need = 'need_more'
        elif is_ji: need = 'reduce'
        elif pct >= 30: need = 'abundant'
        elif pct <= 10: need = 'lacking'
        else: need = 'balanced'

        elements.append({
            'element': elem,
            'count': count,
            'percentage': pct,
            'relation': relation,
            'need': need,
            'is_yong_shen': is_yong,
            'is_ji_shen': is_ji,
            'generates': GENERATES[elem],
            'controls': CONTROLS[elem],
            **ELEMENT_FACTS[elem],
        })

    return {
        'elements': elements,
        'day_master': dm_element,
        'dm_strength': dm_strength,
        'yong_shen': yong_element,
        'ji_shen': ji_element,
    }


def build_elements_prompt(data: Dict, language: str = 'en') -> str:
    lines = [
        f"Day Master: {data['day_master']} ({data['dm_strength']})",
        f"Yong Shen (needed): {data['yong_shen']} | Ji Shen (harmful): {data['ji_shen']}\n",
    ]
    for e in data['elements']:
        flag = ' ★ YONG SHEN' if e['is_yong_shen'] else (' ✗ JI SHEN' if e['is_ji_shen'] else '')
        lines.append(
            f"{e['element']}: count {e['count']} ({e['percentage']}%) | relation {e['relation']} | need {e['need']}{flag}\n"
            f"  season {e['season']} | direction {e['direction']} | organ {e['organ']} | emotion {e['emotion']} | taste {e['taste']}"
        )
    chart_text = '\n'.join(lines)

    return f"""{voice_card(language)}

You are reading this person's relationship to the five elements (Chinese metaphysics).

DATA:
{chart_text}

Cycles:
- Generation: Wood → Fire → Earth → Metal → Water → Wood
- Control: Wood controls Earth, Earth controls Water, Water controls Fire, Fire controls Metal, Metal controls Wood

Write EXACTLY 5 readings, one per element in order: Wood, Fire, Earth, Metal, Water.
Separate each with exactly ---

For each (4-5 sentences):
- How much they carry of this element and what that does in daily life
- Their relationship to it (fuel / output / challenge / wealth / self)
- Whether they need more or less + ONE concrete TCM remedy (food, color, habit, environment)
- One line connecting it to their emotional/health pattern via the organ/emotion link

Rules:
- Each reading under 90 words
- No "Wood:" labels in the output
- Remedies must be specific and doable (drawn from TCM: color, taste, direction, organ)
- Separate the 5 readings with exactly ---"""


class _ElementsRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/five-elements')
async def get_five_elements(request_body: _ElementsRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_five_elements(engine)
        prompt = build_elements_prompt(data, language)
        raw = await call_llm(prompt, settings,
                             user_message="Read all five elements.",
                             max_tokens=2000, temperature=0.85)
        segments = split_segments(raw)

        readings = []
        for i, e in enumerate(data['elements']):
            seg = segments[i] if i < len(segments) else ''
            readings.append({**e, 'reading': seg})

        return {
            'day_master': data['day_master'],
            'dm_strength': data['dm_strength'],
            'yong_shen': data['yong_shen'],
            'ji_shen': data['ji_shen'],
            'elements': readings,
            'version': 1,
            'cache_ttl_seconds': 2592000,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


five_elements_router = router
