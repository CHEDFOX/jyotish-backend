"""
FOUR PILLARS — Kama (desire), Karma (action), Dharma (purpose), Moksha (liberation).

Each pillar carries an info explainer + the personal word/note interpretation.

Endpoint: POST /api/public/four-pillars
"""

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, parse_json_or_text,
)


router = APIRouter(prefix="/public", tags=["Four Pillars"])


PILLAR_STRUCTURE = {
    'kama':   {'title': 'Kama',   'meaning': 'Desire',     'houses': [3, 7, 11], 'karaka': 'Venus',   'primary_house': 7},
    'karma':  {'title': 'Karma',  'meaning': 'Action',     'houses': [2, 6, 10], 'karaka': 'Saturn',  'primary_house': 10},
    'dharma': {'title': 'Dharma', 'meaning': 'Purpose',    'houses': [1, 5, 9],  'karaka': 'Jupiter', 'primary_house': 9},
    'moksha': {'title': 'Moksha', 'meaning': 'Liberation', 'houses': [4, 8, 12], 'karaka': 'Ketu',    'primary_house': 12},
}


def build_four_pillars(engine) -> Dict:
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    def _pl(name):
        p = planets.get(name, {})
        return p if isinstance(p, dict) else {}

    dignity = safe(engine.get_planetary_dignity, {}) or {}
    if not isinstance(dignity, dict): dignity = {}
    house_lords = dignity.get('house_lords', {}) or {}
    if not isinstance(house_lords, dict): house_lords = {}

    yoga_data = safe(engine.get_yogas, {}) or {}
    if not isinstance(yoga_data, dict): yoga_data = {}
    all_yogas = yoga_data.get('yogas', []) or []
    if not isinstance(all_yogas, list): all_yogas = []

    sb_data = safe(engine.get_shadbala_complete, {}) or {}
    if not isinstance(sb_data, dict): sb_data = {}
    sb_planets = sb_data.get('planets', {}) or {}
    if not isinstance(sb_planets, dict): sb_planets = {}

    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    asc_sign = asc.get('rashi_name', '')

    pillars = {}
    for key, meta in PILLAR_STRUCTURE.items():
        karaka_name = meta['karaka']
        karaka = _pl(karaka_name)
        sb_k = sb_planets.get(karaka_name, {}) or {}
        if not isinstance(sb_k, dict): sb_k = {}

        house_planets = {
            h: [n for n, d in planets.items() if isinstance(d, dict) and d.get('house') == h]
            for h in meta['houses']
        }
        h_lords = {h: house_lords.get(str(h)) or house_lords.get(h) or '' for h in meta['houses']}

        pillar_planet_names = set()
        for h in meta['houses']:
            pillar_planet_names.update(house_planets.get(h, []))
        pillar_planet_names.add(karaka_name)
        pillar_yogas = []
        for y in all_yogas:
            if not isinstance(y, dict): continue
            yp = y.get('planets', [])
            if isinstance(yp, str): yp = [yp]
            if any(p in pillar_planet_names for p in yp):
                pillar_yogas.append(y.get('name', ''))

        primary_h = meta['primary_house']
        pillars[key] = {
            'key': key,
            'title': meta['title'],
            'meaning': meta['meaning'],
            'houses': meta['houses'],
            'karaka': {
                'planet': karaka_name,
                'sign': karaka.get('rashi_name', ''),
                'house': karaka.get('house', 0),
                'nakshatra': karaka.get('nakshatra_name', ''),
                'strength_pct': sb_k.get('percentage', 0),
                'grade': sb_k.get('grade', ''),
            },
            'primary_house': primary_h,
            'primary_lord': house_lords.get(str(primary_h)) or house_lords.get(primary_h) or '',
            'primary_planets': house_planets.get(primary_h, []),
            'house_lords': h_lords,
            'house_planets': house_planets,
            'yogas': pillar_yogas[:4],
        }

    return {'pillars': pillars, 'ascendant': asc_sign}


def build_pillars_prompt(data: Dict, language: str = 'en') -> str:
    lines = [f"Ascendant: {data['ascendant']}\n"]
    for key, p in data['pillars'].items():
        k = p['karaka']
        lines.append(
            f"=== {p['title'].upper()} ({p['meaning']}) ===\n"
            f"  Trikona houses: {p['houses']} (primary: {p['primary_house']})\n"
            f"  Karaka: {k['planet']} in {k['sign']} house {k['house']} ({k['nakshatra']}) — strength {k['strength_pct']}% ({k['grade']})\n"
            f"  Primary house {p['primary_house']}: lord {p['primary_lord']}, occupants {p['primary_planets'] or 'empty'}\n"
            f"  Trikona lords: {p['house_lords']}\n"
            f"  Yogas touching this pillar: {', '.join(p['yogas']) or 'none'}\n"
        )
    chart_text = '\n'.join(lines)

    return f"""{voice_card(language)}

You are reading this person's four life aims (purusharthas) — Kama (desire), Karma (action), Dharma (purpose), Moksha (liberation).

CHART DATA:
{chart_text}

Return ONLY valid JSON in this exact shape:
{{
  "kama":   {{"info": "<2-3 short lines>", "word": "<one word>", "note": "<2 sentences>"}},
  "karma":  {{"info": "<2-3 short lines>", "word": "<one word>", "note": "<2 sentences>"}},
  "dharma": {{"info": "<2-3 short lines>", "word": "<one word>", "note": "<2 sentences>"}},
  "moksha": {{"info": "<2-3 short lines>", "word": "<one word>", "note": "<2 sentences>"}},
  "closing": "<one memorable sentence tying all four together>"
}}

Field rules:
- "info" = museum-label explainer. What this aim IS in Vedic philosophy + which houses and karaka govern it. Factual-mystical, NO "you" pronouns. 2-3 short lines.
- "word" = ONE word, evocative, specific to THIS chart (not generic). Drawn from the actual placements.
- "note" = exactly 2 sentences, second person ("you"), referencing actual signs/houses/dignity from the chart data.
- "closing" = one sentence that ties all four pillars together for this person. Memorable. Screenshot-worthy.

Total under 300 words."""


class _PillarsRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/four-pillars')
async def get_four_pillars(request_body: _PillarsRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_four_pillars(engine)
        prompt = build_pillars_prompt(data, language)
        raw = await call_llm(prompt, settings,
                             user_message="Read these four pillars.",
                             max_tokens=1500, temperature=0.85)
        parsed = parse_json_or_text(raw)

        result_pillars = {}
        for key in ('kama', 'karma', 'dharma', 'moksha'):
            llm = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
            llm = llm or {}
            result_pillars[key] = {
                **data['pillars'][key],
                'info': llm.get('info', ''),
                'word': llm.get('word', ''),
                'note': llm.get('note', ''),
            }

        return {
            'ascendant': data['ascendant'],
            'pillars': result_pillars,
            'closing': parsed.get('closing', ''),
            'version': 2,
            'cache_ttl_seconds': 31536000,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


four_pillars_router = router
