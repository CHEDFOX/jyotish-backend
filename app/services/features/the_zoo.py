"""
THE ZOO — Your 4 BaZi animals (year/month/day/hour pillars).

Each animal has two pieces:
  - info: explainer card (what this animal is + what it governs)
  - reading: personal interpretation

Endpoint: POST /api/public/the-zoo
"""

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    extract_birth, get_engine, call_llm, split_segments,
)


router = APIRouter(prefix="/public", tags=["The Zoo"])


PILLAR_AGES = {'year': '0-16', 'month': '17-32', 'day': '33-48', 'hour': '49+'}


def build_the_zoo(engine) -> Dict:
    from app.services.chinese.bazi import BaZiChart

    bazi = BaZiChart(engine.birth_dt)
    pillars = bazi.get_four_pillars() or {}
    if not isinstance(pillars, dict): pillars = {}

    yd = bazi.get_animal_sign() or {}
    if not isinstance(yd, dict): yd = {}
    year_animal = yd.get('animal', '')

    animals = []
    for key in ('year', 'month', 'day', 'hour'):
        p = pillars.get(key, {}) or {}
        if not isinstance(p, dict): p = {}
        branch = p.get('branch', {}) or {}
        stem = p.get('stem', {}) or {}
        if not isinstance(branch, dict): branch = {}
        if not isinstance(stem, dict): stem = {}

        animals.append({
            'pillar': key,
            'ages': PILLAR_AGES[key],
            'animal': branch.get('animal', ''),
            'animal_chinese': branch.get('chinese', ''),
            'animal_element': branch.get('element', ''),
            'stem_element': stem.get('element', ''),
            'stem_name': stem.get('name', ''),
            'polarity': stem.get('polarity', ''),
        })

    return {'animals': animals, 'year_animal': year_animal}


def build_zoo_prompt(data: Dict, language: str = 'en') -> str:
    lines = []
    for a in data['animals']:
        lines.append(
            f"- {a['pillar'].upper()} pillar (ages {a['ages']}): "
            f"{a['polarity']} {a['stem_element']} {a['animal']} ({a['animal_chinese']}), animal element {a['animal_element']}"
        )
    pillars_text = '\n'.join(lines)

    return f"""{voice_card(language)}

You are reading this person's four BaZi animals — Chinese Four Pillars astrology.

Pillar layers:
- Year  = outer mask, social identity, ages 0-16
- Month = career and parents, how the world uses them, ages 17-32
- Day   = TRUE self, spouse, who they really are, ages 33-48
- Hour  = hidden self, children, legacy, old age, ages 49+

{pillars_text}

For EACH of the 4 pillars (in order: year, month, day, hour), write TWO short pieces:

1. INFO — 2-3 short lines. What this animal IS in BaZi (its archetypal nature combined with the stem element), and what it GOVERNS in THIS pillar position. Factual-mystical, like a museum label. NO "you" pronouns.

2. READING — 4-5 sentences. What this animal in THIS pillar reveals about THIS person. How the stem element shapes it. The strength AND the vulnerability. One surprising truth. Second person ("you").

Total 8 pieces. Separate each piece with exactly ---

Order:
[year info] --- [year reading] --- [month info] --- [month reading] --- [day info] --- [day reading] --- [hour info] --- [hour reading]

The DAY pillar reading must go deepest — that's who they really are beneath the year-animal mask.

Rules:
- INFO under 50 words, no "you", reads like an explainer card
- READING under 80 words, second person, specific to chart
- No headers, no "year info:" labels in the output
- Separate with exactly ---"""


class _ZooRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/the-zoo')
async def get_the_zoo(request_body: _ZooRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_the_zoo(engine)
        prompt = build_zoo_prompt(data, language)
        raw = await call_llm(prompt, settings,
                             user_message="Read all four animals.",
                             max_tokens=2200, temperature=0.85)
        segments = split_segments(raw)

        readings = []
        for i, a in enumerate(data['animals']):
            info_idx = i * 2
            reading_idx = i * 2 + 1
            info = segments[info_idx] if info_idx < len(segments) else ''
            reading = segments[reading_idx] if reading_idx < len(segments) else ''
            readings.append({**a, 'info': info, 'reading': reading})

        return {
            'year_animal': data['year_animal'],
            'animals': readings,
            'version': 2,
            'cache_ttl_seconds': 31536000,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


the_zoo_router = router
