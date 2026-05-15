"""
CORE CHART — Unified wheel across 5 systems.

One endpoint, 5 parallel LLM calls (one per system). Each system's wheel nodes
get titles, factual descriptions, and per-person interpretations.

Endpoint: POST /api/public/core-chart
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, parse_json_or_text,
)


router = APIRouter(prefix="/public", tags=["Core Chart"])


PLANET_GLYPHS = {
    'Sun': '\u2609', 'Moon': '\u263D', 'Mars': '\u2642',
    'Mercury': '\u263F', 'Jupiter': '\u2643', 'Venus': '\u2640',
    'Saturn': '\u2644', 'Uranus': '\u2645', 'Neptune': '\u2646', 'Pluto': '\u2647',
}


def _build_wheel_data(engine) -> Dict:
    """Per-system nodes as facts."""
    # Vedic — 9 grahas
    vedic_nodes = []
    for p in ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'):
        d = engine.planets.get(p, {}) if isinstance(engine.planets.get(p), dict) else {}
        vedic_nodes.append({
            'id': p, 'label': p,
            'sign': d.get('rashi_name', ''),
            'house': d.get('house', ''),
            'nakshatra': d.get('nakshatra_name', ''),
            'retrograde': bool(d.get('retrograde', False)),
            'degree': round(d.get('degree_in_rashi', 0), 1),
        })

    # KP — 12 cusps
    kp_nodes = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp = KPComplete(engine)
        cusps = kp.get_placidus_cusps() or {}
        for h in range(1, 13):
            cd = cusps.get(str(h), cusps.get(h, {}))
            cd = cd if isinstance(cd, dict) else {}
            kp_nodes.append({
                'id': f'H{h}', 'label': str(h),
                'sign': cd.get('rashi_name', ''),
                'nakshatra': cd.get('nakshatra', ''),
                'sub_lord': cd.get('sub_lord', cd.get('nakshatra_lord', '')),
            })
    except Exception:
        for h in range(1, 13):
            kp_nodes.append({'id': f'H{h}', 'label': str(h), 'sign': '', 'nakshatra': '', 'sub_lord': ''})

    # Western — 10 planets
    western_nodes = []
    for p in ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Uranus', 'Neptune', 'Pluto'):
        pd = engine.planets.get(p, {}) if isinstance(engine.planets.get(p), dict) else {}
        western_nodes.append({
            'id': p, 'label': PLANET_GLYPHS.get(p, p[0]),
            'sign': pd.get('rashi_name', ''),
            'house': pd.get('house', ''),
        })

    # Chinese — 5 elements
    chinese_nodes = []
    try:
        from app.services.chinese.bazi import BaZiChart
        bazi = BaZiChart(engine.birth_dt)
        bal = bazi.get_element_balance() or {}
        counts = bal.get('counts', {}) if isinstance(bal.get('counts'), dict) else {}
        dm = bazi.get_day_master() or {}
        dm_elem = dm.get('element', '') if isinstance(dm, dict) else ''
        for elem in ('Wood', 'Fire', 'Earth', 'Metal', 'Water'):
            chinese_nodes.append({
                'id': elem, 'label': elem,
                'count': counts.get(elem, 0),
                'is_day_master': elem == dm_elem,
                'strength': bal.get('day_master_strength', '') if elem == dm_elem else '',
            })
    except Exception:
        for elem in ('Wood', 'Fire', 'Earth', 'Metal', 'Water'):
            chinese_nodes.append({'id': elem, 'label': elem, 'count': 0, 'is_day_master': False, 'strength': ''})

    # Numerology — 1-9 Lo Shu
    num_nodes = []
    try:
        from app.services.numerology.core import NumerologyEngine
        nc = NumerologyEngine(name='', birth_date=engine.birth_dt.date())
        grid = nc.get_lo_shu_grid() or {}
        gc = grid.get('grid', {}) if isinstance(grid.get('grid'), dict) else {}
        m = nc.get_mulank() or {}
        b = nc.get_bhagyank() or {}
        mulank = m.get('number', 0) if isinstance(m, dict) else 0
        bhagyank = b.get('number', 0) if isinstance(b, dict) else 0
        present = grid.get('present_numbers', [])
        for n in range(1, 10):
            num_nodes.append({
                'id': str(n), 'label': str(n),
                'count': gc.get(n, gc.get(str(n), 0)),
                'present': n in present,
                'is_mulank': n == mulank,
                'is_bhagyank': n == bhagyank,
            })
    except Exception:
        for n in range(1, 10):
            num_nodes.append({'id': str(n), 'label': str(n), 'count': 0, 'present': False, 'is_mulank': False, 'is_bhagyank': False})

    return {
        'vedic': {'nodes': vedic_nodes, 'count': len(vedic_nodes)},
        'kp': {'nodes': kp_nodes, 'count': len(kp_nodes)},
        'western': {'nodes': western_nodes, 'count': len(western_nodes)},
        'chinese': {'nodes': chinese_nodes, 'count': len(chinese_nodes)},
        'numerology': {'nodes': num_nodes, 'count': len(num_nodes)},
    }


def _build_system_prompt(sys_name: str, nodes: list, engine, language: str = 'en') -> str:
    from app.services.jyotish_engine import JyotishEngine
    now = datetime.now()
    try:
        e_now = JyotishEngine(now, engine.latitude, engine.longitude)
        tp = e_now.planets
    except Exception:
        tp = {}

    dasha = safe(lambda: engine.get_vimshottari_dasha().get('dasha_string', ''), '')

    node_lines = []
    for n in nodes:
        parts = [n['id']]
        for k in ('sign', 'house', 'nakshatra', 'sub_lord', 'count', 'strength'):
            v = n.get(k)
            if v not in (None, 0, ''):
                parts.append(f'{k}={v}')
        if n.get('retrograde'): parts.append('retrograde')
        if n.get('is_day_master'): parts.append('Day Master')
        if n.get('is_mulank'): parts.append('Root Number')
        if n.get('is_bhagyank'): parts.append('Destiny Number')
        if 'present' in n and not n['present']: parts.append('MISSING')
        node_lines.append('  ' + ' | '.join(parts))

    transit_lines = []
    for pl in ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu'):
        td = tp.get(pl, {})
        if isinstance(td, dict) and td.get('rashi_name'):
            transit_lines.append(f'  {pl}: {td.get("rashi_name", "")} H{td.get("house", "")}')

    node_str = '\n'.join(node_lines)
    transit_str = '\n'.join(transit_lines)

    node_json = []
    for i, n in enumerate(nodes):
        comma = ',' if i < len(nodes) - 1 else ''
        node_json.append(
            f'    "{n["id"]}": {{"title":"3-5 words. Element with placement.",'
            f'"what":"2-3 sentences. What this element IS in {sys_name.upper()}. Universal definition. NO mention of this person.",'
            f'"significance":"3-4 sentences. What this element MEANS in {sys_name.upper()}. What it rules and governs. NO mention of this person.",'
            f'"effect":"3-4 sentences. How THIS specific placement affects THIS person now.",'
            f'"cta_significance":"4-6 words","cta_effect":"4-6 words"}}{comma}'
        )
    nodes_block = '\n'.join(node_json)

    return f"""{voice_card(language)}

This is a CORE CHART WHEEL. The person selects each node to learn what it means and how it affects them NOW.

{sys_name.upper()} nodes:
{node_str}
Dasha: {dasha}
Date: {now.strftime('%A, %B %d, %Y')}
Transits:
{transit_str}

Return ONLY valid JSON:
{{
  "headline": "3-5 words. Short. Punchy.",
  "hook_body": "2 sentences for this system — the pattern they live but won't name.",
  "cta_dive": "4-6 words. Curiosity.",
  "secret": "ONE precise cryptic line about this chart's pattern in this system. Specific number, house, ratio, or configuration. Max 12 words.",
{nodes_block}
}}

~500 words. Titles SHORT. The 'what' and 'significance' fields are factual museum labels — never mention 'you'.
The 'effect' field is personal and current."""


class _CoreChartRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/core-chart')
async def get_core_chart(request_body: _CoreChartRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'
        wheel_data = _build_wheel_data(engine)

        async def fetch_system(sys_name: str) -> dict:
            nodes = wheel_data[sys_name]['nodes']
            prompt = _build_system_prompt(sys_name, nodes, engine, language)
            try:
                raw = await call_llm(prompt, settings,
                                     user_message=f'Read my {sys_name} chart nodes.',
                                     max_tokens=2500, temperature=0.75)
                return parse_json_or_text(raw)
            except Exception:
                return {}

        systems = ('vedic', 'kp', 'western', 'chinese', 'numerology')
        results = await asyncio.gather(*[fetch_system(s) for s in systems], return_exceptions=True)

        readings = {}
        for i, s in enumerate(systems):
            r = results[i]
            readings[s] = r if isinstance(r, dict) and 'text' not in r else {}

        # Top-level hook drawn from Vedic (the primary system)
        vedic_r = readings.get('vedic', {}) if isinstance(readings.get('vedic'), dict) else {}

        return {
            'wheels': wheel_data,
            'readings': readings,
            'hook_title': vedic_r.get('headline', ''),
            'hook_body': vedic_r.get('hook_body', ''),
            'cta_dive': vedic_r.get('cta_dive', 'Open the wheel'),
            'secret': vedic_r.get('secret', ''),
            'version': 2,
            'cache_ttl_seconds': 86400,  # 1 day — transits/dasha shift
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


core_chart_router = router
