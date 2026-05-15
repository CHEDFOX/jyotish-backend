"""
BLUNT SEER — Astrology roast comedy.

Pulls WIDE data across Western + Vedic + Chinese + Numerology so each roast is
fingerprint-unique to the chart rather than generic to a Sun sign.

Endpoint: POST /api/public/blunt-seer
"""

import random
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import safe, extract_birth, get_engine, call_llm


router = APIRouter(prefix="/public", tags=["Blunt Seer"])


ROAST_ANGLES = [
    'their love life and dating patterns',
    'their work ethic and career habits',
    'how they handle money and spending',
    'their texting and communication style',
    'their emotional patterns and moods',
    'what they are like at parties and social events',
    'their morning routine and daily habits',
    'their ego and how they seek validation',
    'their hidden guilty pleasures',
    'how they handle arguments and conflict',
]


def build_blunt_seer(engine) -> Dict:
    from app.services.western.chart import WesternChart
    from app.services.western.extras import calculate_lilith
    from app.services.chinese.bazi import BaZiChart
    from app.services.numerology.core import NumerologyEngine

    # ── Western ───────────────────────────────────────────────
    chart = WesternChart(engine.birth_dt, engine.latitude, engine.longitude)
    big3 = safe(chart.get_big_three, {}) or {}
    if not isinstance(big3, dict): big3 = {}
    w_sun = big3.get('sun') if isinstance(big3.get('sun'), dict) else {}
    w_moon = big3.get('moon') if isinstance(big3.get('moon'), dict) else {}
    w_rising = big3.get('rising') if isinstance(big3.get('rising'), dict) else {}

    elements = safe(chart.get_element_balance, {}) or {}
    if not isinstance(elements, dict): elements = {}
    elem_counts = elements.get('counts', {}) if isinstance(elements.get('counts'), dict) else {}

    aspects = safe(chart.get_aspects, []) or []
    if not isinstance(aspects, list): aspects = []
    harsh = [
        f"{a.get('planet1','')} {a.get('aspect','')} {a.get('planet2','')}"
        for a in aspects
        if isinstance(a, dict) and a.get('aspect') in ('square', 'opposition')
    ][:5]

    retros = []
    if hasattr(chart, '_planets') and isinstance(chart._planets, dict):
        for pname, pdata in chart._planets.items():
            if isinstance(pdata, dict) and (pdata.get('retrograde') or pdata.get('is_retrograde')):
                retros.append(pname)

    lilith = safe(lambda: calculate_lilith(engine.birth_dt), {}) or {}
    if not isinstance(lilith, dict): lilith = {}

    # ── Vedic (deep personality + life moment) ────────────────
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    def _v(name):
        p = planets.get(name, {})
        return p if isinstance(p, dict) else {}

    v_sun, v_moon = _v('Sun'), _v('Moon')
    v_mars, v_mercury = _v('Mars'), _v('Mercury')
    v_venus, v_saturn = _v('Venus'), _v('Saturn')
    v_rahu, v_ketu = _v('Rahu'), _v('Ketu')

    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}

    dasha = safe(engine.get_vimshottari_dasha, {}) or {}
    if not isinstance(dasha, dict): dasha = {}

    dignity = safe(engine.get_planetary_dignity, {}) or {}
    if not isinstance(dignity, dict): dignity = {}
    house_lords = dignity.get('house_lords', {}) or {}
    if not isinstance(house_lords, dict): house_lords = {}
    def _h(h):
        return house_lords.get(str(h)) or house_lords.get(h) or ''

    debilitated, exalted, combust = [], [], []
    dp = dignity.get('planets', {}) or {}
    if isinstance(dp, dict):
        for pname, pdata in dp.items():
            if not isinstance(pdata, dict): continue
            dt = pdata.get('dignity_type', '')
            if dt == 'Debilitated': debilitated.append(pname)
            elif dt == 'Exalted': exalted.append(pname)
            if pdata.get('is_combust'): combust.append(pname)

    yoga_data = safe(engine.get_yogas, {}) or {}
    if not isinstance(yoga_data, dict): yoga_data = {}
    yogas = yoga_data.get('highlights', []) or []
    yoga_names = [y.get('name', '') for y in yogas[:5] if isinstance(y, dict) and y.get('name')]

    # ── Chinese ────────────────────────────────────────────────
    bazi_dm_elem, bazi_dominant, bazi_animal = '', '', ''
    try:
        bz = BaZiChart(engine.birth_dt)
        dm = bz.get_day_master() or {}
        if isinstance(dm, dict): bazi_dm_elem = dm.get('element', '')
        bal = bz.get_element_balance() or {}
        if isinstance(bal, dict):
            counts = bal.get('counts', {})
            if isinstance(counts, dict) and counts:
                bazi_dominant = max(counts, key=counts.get)
        ani = bz.get_animal_sign() or {}
        if isinstance(ani, dict): bazi_animal = ani.get('animal', '')
    except Exception:
        pass

    # ── Numerology ────────────────────────────────────────────
    nm_mulank, nm_bhagyank, nm_py = 0, 0, 0
    try:
        ne = NumerologyEngine(birth_date=engine.birth_dt.date())
        m = ne.get_mulank() or {}
        if isinstance(m, dict): nm_mulank = m.get('number', 0)
        b = ne.get_bhagyank() or {}
        if isinstance(b, dict): nm_bhagyank = b.get('number', 0)
        py = ne.get_personal_year() or {}
        if isinstance(py, dict): nm_py = py.get('number', 0)
    except Exception:
        pass

    age = datetime.now().year - engine.birth_dt.year

    return {
        'age': age,
        'western': {
            'sun': w_sun.get('sign', ''),
            'moon': w_moon.get('sign', ''),
            'rising': w_rising.get('sign', ''),
            'lilith': lilith.get('sign', ''),
            'dominant_element': elements.get('dominant', ''),
            'weakest_element': min(elem_counts, key=elem_counts.get) if elem_counts else '',
            'harsh_aspects': harsh,
            'natal_retrogrades': retros,
        },
        'vedic': {
            'ascendant': asc.get('rashi_name', ''),
            'sun': f"{v_sun.get('rashi_name','')} H{v_sun.get('house','?')}",
            'moon': f"{v_moon.get('rashi_name','')} {v_moon.get('nakshatra_name','')}",
            'mars': f"{v_mars.get('rashi_name','')} H{v_mars.get('house','?')}",
            'mercury': f"{v_mercury.get('rashi_name','')} H{v_mercury.get('house','?')}",
            'venus': f"{v_venus.get('rashi_name','')} H{v_venus.get('house','?')}",
            'saturn': f"{v_saturn.get('rashi_name','')} H{v_saturn.get('house','?')}",
            'rahu': f"{v_rahu.get('rashi_name','')} H{v_rahu.get('house','?')}",
            'ketu': f"{v_ketu.get('rashi_name','')} H{v_ketu.get('house','?')}",
            'second_lord': _h(2),
            'seventh_lord': _h(7),
            'tenth_lord': _h(10),
            'dasha': dasha.get('dasha_string', ''),
            'debilitated': debilitated,
            'exalted': exalted,
            'combust': combust,
            'yogas': yoga_names,
        },
        'chinese': {
            'day_master_element': bazi_dm_elem,
            'dominant_element': bazi_dominant,
            'animal': bazi_animal,
        },
        'numerology': {
            'mulank': nm_mulank,
            'bhagyank': nm_bhagyank,
            'personal_year': nm_py,
        },
    }


def build_roast_prompt(data: Dict, language: str = 'en') -> str:
    angle = random.choice(ROAST_ANGLES)
    w, v, c, n = data['western'], data['vedic'], data['chinese'], data['numerology']

    return f"""{voice_card(language)}

But for THIS reading, DROP the oracle voice. You are a stand-up comedian who knows astrology cold — funny, specific, lovable, NEVER cruel.

ROAST TARGET (age {data['age']}):

WESTERN VIBE:
- Sun {w['sun']} | Moon {w['moon']} | Rising {w['rising']} | Lilith {w['lilith']}
- Dominant element: {w['dominant_element']} | Weakest: {w['weakest_element']}
- Harsh aspects: {', '.join(w['harsh_aspects']) or 'none'}
- Retrogrades at birth: {', '.join(w['natal_retrogrades']) or 'none'}

VEDIC LAYER (the inner truth):
- Ascendant: {v['ascendant']}
- Sun: {v['sun']} | Moon: {v['moon']} | Mars: {v['mars']}
- Mercury: {v['mercury']} | Venus: {v['venus']} | Saturn: {v['saturn']}
- Rahu: {v['rahu']} | Ketu: {v['ketu']}
- Love (7th lord): {v['seventh_lord']} | Career (10th lord): {v['tenth_lord']} | Money (2nd lord): {v['second_lord']}
- Current dasha: {v['dasha']}
- Debilitated: {', '.join(v['debilitated']) or 'none'} | Exalted: {', '.join(v['exalted']) or 'none'} | Combust: {', '.join(v['combust']) or 'none'}
- Active yogas: {', '.join(v['yogas']) or 'none'}

CHINESE: Day Master {c['day_master_element']}, dominant {c['dominant_element']}, year animal {c['animal']}
NUMEROLOGY: Mulank {n['mulank']} | Bhagyank {n['bhagyank']} | Personal Year {n['personal_year']}

ANGLE: Roast {angle}.

Write a FUNNY roast in 4-5 sentences:
- Pull from MULTIPLE systems above so the humor is unique to THIS chart, not generic to a Sun sign
- Reference at least 2 specific placements by name (e.g. "your Mercury in {v['mercury']}", "Personal Year {n['personal_year']}")
- Connect chart facts to real-life behavior — dating apps, Netflix, texting, cooking, Sunday plans, group chats
- Start with something unexpected — NOT "Oh you're a [sun sign]..."
- End with ONE line so specific they'll screenshot it
- Under 90 words. Flowing. No bullets. No astrology jargon explanation.
- COMEDY not cruelty. Playful, not painful."""


class _RoastRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/blunt-seer')
async def get_blunt_seer(request_body: _RoastRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_blunt_seer(engine)
        prompt = build_roast_prompt(data, language)
        roast = await call_llm(prompt, settings,
                               user_message="Roast me.",
                               max_tokens=500, temperature=0.95)

        return {
            **data,
            'roast': roast,
            'version': 1,
            'cache_ttl_seconds': 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


blunt_seer_router = router
