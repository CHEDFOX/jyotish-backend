"""
MATCH — Vedic compatibility (Ashtakoota + Manglik + Navamsa + 7th-lord + Venus).

Endpoint: POST /api/public/match
Body: { kundli_data, partner: { year, month, day, hour, minute, lat, lng }, language }
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.features._base import safe, extract_birth


router = APIRouter(prefix="/public", tags=["Match"])


SIGN_ORDER = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
              'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

SIGN_RULERS = {
    'Aries': 'Mars',      'Taurus': 'Venus',     'Gemini': 'Mercury',
    'Cancer': 'Moon',     'Leo': 'Sun',          'Virgo': 'Mercury',
    'Libra': 'Venus',     'Scorpio': 'Mars',     'Sagittarius': 'Jupiter',
    'Capricorn': 'Saturn','Aquarius': 'Saturn',  'Pisces': 'Jupiter',
}

SIGN_ELEMENT = {
    'Aries': 'Fire', 'Leo': 'Fire', 'Sagittarius': 'Fire',
    'Taurus': 'Earth', 'Virgo': 'Earth', 'Capricorn': 'Earth',
    'Gemini': 'Air', 'Libra': 'Air', 'Aquarius': 'Air',
    'Cancer': 'Water', 'Scorpio': 'Water', 'Pisces': 'Water',
}

PLANET_FRIENDS = {
    'Sun':     {'friends': ['Moon', 'Mars', 'Jupiter'],   'enemies': ['Venus', 'Saturn'],     'neutrals': ['Mercury']},
    'Moon':    {'friends': ['Sun', 'Mercury'],            'enemies': [],                       'neutrals': ['Mars', 'Jupiter', 'Venus', 'Saturn']},
    'Mars':    {'friends': ['Sun', 'Moon', 'Jupiter'],    'enemies': ['Mercury'],              'neutrals': ['Venus', 'Saturn']},
    'Mercury': {'friends': ['Sun', 'Venus'],              'enemies': ['Moon'],                 'neutrals': ['Mars', 'Jupiter', 'Saturn']},
    'Jupiter': {'friends': ['Sun', 'Moon', 'Mars'],       'enemies': ['Mercury', 'Venus'],     'neutrals': ['Saturn']},
    'Venus':   {'friends': ['Mercury', 'Saturn'],         'enemies': ['Sun', 'Moon'],          'neutrals': ['Mars', 'Jupiter']},
    'Saturn':  {'friends': ['Mercury', 'Venus'],          'enemies': ['Sun', 'Moon', 'Mars'],  'neutrals': ['Jupiter']},
}


# ── Pure-math Navamsa (D9) from longitude ─────────────────────
def navamsa_sign(longitude: float) -> str:
    """D9 sign from sidereal longitude (0-360)."""
    if longitude is None:
        return ''
    L = float(longitude) % 360.0
    rashi = int(L // 30) % 12          # 0..11
    deg_in_sign = L - (rashi * 30)      # 0..29.999
    nav_index = int(deg_in_sign / (30.0 / 9.0))  # 0..8
    if nav_index > 8:
        nav_index = 8

    # Starting D9 rashi by sign quality:
    #   movable (0,3,6,9)  → same sign
    #   fixed   (1,4,7,10) → 9th from sign
    #   dual    (2,5,8,11) → 5th from sign
    if rashi in (0, 3, 6, 9):
        start = rashi
    elif rashi in (1, 4, 7, 10):
        start = (rashi + 8) % 12
    else:
        start = (rashi + 4) % 12

    return SIGN_ORDER[(start + nav_index) % 12]


def _build_engine(birth: dict):
    from app.services.jyotish_engine import JyotishEngine
    return JyotishEngine(
        datetime(
            int(birth.get('year', 2000)),
            int(birth.get('month', 1)),
            int(birth.get('day', 1)),
            int(birth.get('hour', 12)),
            int(birth.get('minute', 0)),
        ),
        float(birth.get('lat', birth.get('latitude', 28.6))),
        float(birth.get('lng', birth.get('longitude', 77.2))),
    )


def _planet(engine, name: str) -> dict:
    p = engine.planets.get(name, {}) if isinstance(getattr(engine, 'planets', None), dict) else {}
    return p if isinstance(p, dict) else {}


def _asc_sign(engine) -> str:
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    return asc.get('rashi_name', '')


def _asc_longitude(engine) -> float:
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    return asc.get('longitude', 0) or 0


# ── 1. Manglik Dosha ──────────────────────────────────────────
def _check_manglik_one(engine) -> Dict:
    mars = _planet(engine, 'Mars')
    house = mars.get('house', 0)
    is_manglik = house in (1, 2, 4, 7, 8, 12)
    if house in (7, 8):
        severity = 'high'
    elif house in (1, 4, 12):
        severity = 'medium'
    elif house == 2:
        severity = 'low'
    else:
        severity = 'none'
    return {
        'mars_house': house,
        'mars_sign': mars.get('rashi_name', ''),
        'is_manglik': is_manglik,
        'severity': severity,
    }


def check_manglik(e1, e2) -> Dict:
    m1 = _check_manglik_one(e1)
    m2 = _check_manglik_one(e2)
    both = m1['is_manglik'] and m2['is_manglik']
    if both:
        verdict = 'cancelled'
    elif m1['is_manglik'] or m2['is_manglik']:
        verdict = 'one_manglik'
    else:
        verdict = 'no_dosha'
    return {'person1': m1, 'person2': m2, 'mutual_cancellation': both, 'verdict': verdict}


# ── 2. Navamsa (D9) comparison — pure math ─────────────────────
def compare_navamsa(e1, e2) -> Dict:
    def _d9_pack(engine):
        moon = _planet(engine, 'Moon')
        venus = _planet(engine, 'Venus')
        asc_long = _asc_longitude(engine)
        d9_asc_sign = navamsa_sign(asc_long) if asc_long else ''
        return {
            'natal_asc': _asc_sign(engine),
            'natal_moon': moon.get('rashi_name', ''),
            'natal_venus': venus.get('rashi_name', ''),
            'd9_asc': d9_asc_sign,
            'd9_moon': navamsa_sign(moon.get('longitude', 0)),
            'd9_venus': navamsa_sign(venus.get('longitude', 0)),
            'd9_seventh_sign': SIGN_ORDER[(SIGN_ORDER.index(d9_asc_sign) + 6) % 12] if d9_asc_sign in SIGN_ORDER else '',
        }

    p1 = _d9_pack(e1)
    p2 = _d9_pack(e2)

    return {
        'available': True,
        'person1': p1,
        'person2': p2,
        'd9_moon_same_sign': p1['d9_moon'] and p1['d9_moon'] == p2['d9_moon'],
        'd9_venus_same_sign': p1['d9_venus'] and p1['d9_venus'] == p2['d9_venus'],
        'd9_asc_same_sign': p1['d9_asc'] and p1['d9_asc'] == p2['d9_asc'],
    }


# ── 3. 7th lord compatibility — derived from ascendant ─────────
def _seventh_lord_from_asc(engine) -> str:
    asc_sign = _asc_sign(engine)
    if asc_sign not in SIGN_ORDER:
        return ''
    seventh_sign = SIGN_ORDER[(SIGN_ORDER.index(asc_sign) + 6) % 12]
    return SIGN_RULERS.get(seventh_sign, '')


def compare_seventh_lords(e1, e2) -> Dict:
    l1 = _seventh_lord_from_asc(e1)
    l2 = _seventh_lord_from_asc(e2)
    if not l1 or not l2:
        return {'person1_lord': l1, 'person2_lord': l2, 'relation': 'unknown'}

    if l1 == l2:
        relation = 'identical'
    else:
        f = PLANET_FRIENDS.get(l1, {})
        if l2 in f.get('friends', []):
            relation = 'friends'
        elif l2 in f.get('enemies', []):
            relation = 'enemies'
        else:
            relation = 'neutral'
    return {'person1_lord': l1, 'person2_lord': l2, 'relation': relation}


# ── 4. Venus sign comparison ──────────────────────────────────
def compare_venus(e1, e2) -> Dict:
    v1 = _planet(e1, 'Venus').get('rashi_name', '')
    v2 = _planet(e2, 'Venus').get('rashi_name', '')
    e1_el = SIGN_ELEMENT.get(v1, '')
    e2_el = SIGN_ELEMENT.get(v2, '')

    if not e1_el or not e2_el:
        compat = 'unknown'
    elif e1_el == e2_el:
        compat = 'highly_compatible'
    elif {e1_el, e2_el} in ({'Fire', 'Air'}, {'Earth', 'Water'}):
        compat = 'compatible'
    elif {e1_el, e2_el} in ({'Fire', 'Water'}, {'Air', 'Earth'}):
        compat = 'challenging'
    else:
        compat = 'mixed'

    return {
        'person1_venus_sign': v1,
        'person1_venus_element': e1_el,
        'person2_venus_sign': v2,
        'person2_venus_element': e2_el,
        'compatibility': compat,
    }


# ── Composite score ────────────────────────────────────────────
def _composite_score(kootas_pct: float, manglik: Dict, lord: Dict, venus: Dict, navamsa: Dict) -> Dict:
    score = float(kootas_pct or 0)
    notes = []

    if manglik['verdict'] == 'one_manglik':
        score -= 10
        notes.append('one-sided Manglik reduces score')
    elif manglik['verdict'] == 'cancelled':
        notes.append('Manglik cancelled (both partners)')

    rel = lord.get('relation', 'unknown')
    if rel == 'friends':
        score += 5; notes.append('7th lords are friends')
    elif rel == 'identical':
        score += 3; notes.append('same 7th lord — shared style')
    elif rel == 'enemies':
        score -= 8; notes.append('7th lords are enemies')

    vc = venus.get('compatibility', '')
    if vc == 'highly_compatible':
        score += 5; notes.append('Venus elements match')
    elif vc == 'compatible':
        score += 3
    elif vc == 'challenging':
        score -= 5; notes.append('Venus elements clash')

    # Navamsa bonuses (D9 same-sign matches are auspicious for marriage)
    if navamsa.get('d9_moon_same_sign'):
        score += 4; notes.append('D9 Moons in same sign')
    if navamsa.get('d9_venus_same_sign'):
        score += 4; notes.append('D9 Venuses in same sign')
    if navamsa.get('d9_asc_same_sign'):
        score += 3; notes.append('D9 ascendants align')

    score = max(0, min(100, score))
    if score >= 75:
        grade = 'excellent'
    elif score >= 60:
        grade = 'good'
    elif score >= 45:
        grade = 'workable'
    else:
        grade = 'challenging'

    return {'composite_score': round(score, 1), 'grade': grade, 'notes': notes}


class _MatchRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    partner: dict
    language: Optional[str] = 'en'


@router.post('/match')
async def get_match(request_body: _MatchRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    p1_birth = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not p1_birth:
        raise HTTPException(status_code=400, detail='Person 1 birth data required')
    if not request_body.partner:
        raise HTTPException(status_code=400, detail='Partner birth data required')

    try:
        e1 = _build_engine(p1_birth)
        e2 = _build_engine(request_body.partner)

        moon2_long = e2.planets['Moon']['longitude']
        koota_result = e1.match_compatibility(moon2_long) or {}
        if not isinstance(koota_result, dict): koota_result = {}

        kootas_list = []
        for key in ('varna', 'vashya', 'tara', 'yoni', 'graha_maitri', 'gana', 'bhakoot', 'nadi'):
            k = (koota_result.get('kootas', {}) or {}).get(key, {})
            if not isinstance(k, dict): k = {}
            kootas_list.append({
                'name': k.get('koota', key),
                'score': k.get('points', 0),
                'max': k.get('max_points', 0),
                'description': k.get('description', ''),
            })

        manglik = check_manglik(e1, e2)
        navamsa = compare_navamsa(e1, e2)
        lord = compare_seventh_lords(e1, e2)
        venus = compare_venus(e1, e2)
        composite = _composite_score(koota_result.get('percentage', 0), manglik, lord, venus, navamsa)

        return {
            'ashtakoota': {
                'kootas': kootas_list,
                'total_score': koota_result.get('total_points', 0),
                'max_score': 36,
                'percentage': koota_result.get('percentage', 0),
                'compatibility_label': koota_result.get('compatibility', ''),
                'recommendation': koota_result.get('recommendation', ''),
                'doshas': koota_result.get('doshas', []),
                'has_major_dosha': koota_result.get('has_major_dosha', False),
            },
            'manglik': manglik,
            'navamsa': navamsa,
            'seventh_lord': lord,
            'venus': venus,
            'composite': composite,
            'boy': koota_result.get('boy', {}),
            'girl': koota_result.get('girl', {}),
            'version': 2,
            'cache_ttl_seconds': 31536000,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


match_router = router
