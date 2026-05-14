"""
CORE CHART — Unified wheel across 5 systems.
One endpoint returns everything. Nodes + readings. Cached 7 days.
"""
from typing import Dict, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/public", tags=["Core Chart"])


def _build_wheel_data(engine) -> Dict:
    """Build wheel nodes for all 5 systems from computed data."""
    # Vedic: 9 planets
    vedic_nodes = []
    for p in ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu']:
        d = engine.planets.get(p, {})
        vedic_nodes.append({
            'id': p, 'label': p,
            'sign': d.get('rashi_name', ''),
            'house': d.get('house', ''),
            'nakshatra': d.get('nakshatra_name', ''),
            'retrograde': bool(d.get('retrograde', False)),
            'degree': round(d.get('degree_in_rashi', 0), 1),
        })

    # KP: 12 houses
    kp_nodes = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp = KPComplete(engine)
        cusps = kp.get_placidus_cusps()
        if isinstance(cusps, dict):
            for h in range(1, 13):
                hk = str(h) if str(h) in cusps else h
                cd = cusps.get(hk, cusps.get(str(h), {}))
                if isinstance(cd, dict):
                    kp_nodes.append({
                        'id': f'H{h}', 'label': str(h),
                        'sign': cd.get('rashi_name', ''),
                        'nakshatra': cd.get('nakshatra', ''),
                        'sub_lord': cd.get('sub_lord', cd.get('nakshatra_lord', '')),
                    })
    except Exception:
        for h in range(1, 13):
            kp_nodes.append({'id': f'H{h}', 'label': str(h), 'sign': '', 'nakshatra': '', 'sub_lord': ''})

    # Western: planets
    western_nodes = []
    try:
        from app.services.western.chart import WesternChart
        wc = WesternChart(engine.birth_dt, engine.latitude, engine.longitude)
        b3 = wc.get_big_three()
        eb = wc.get_element_balance()
        glyphs = {'Sun':'\u2609','Moon':'\u263D','Mars':'\u2642','Mercury':'\u263F','Jupiter':'\u2643','Venus':'\u2640','Saturn':'\u2644','Uranus':'\u2645','Neptune':'\u2646','Pluto':'\u2647'}
        for p in ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Uranus','Neptune','Pluto']:
            pd = engine.planets.get(p, {})
            western_nodes.append({
                'id': p, 'label': glyphs.get(p, p[0]),
                'sign': pd.get('rashi_name', ''),
                'house': pd.get('house', ''),
            })
    except Exception:
        pass

    # Chinese: 5 elements
    chinese_nodes = []
    try:
        from app.services.chinese.bazi import BaZiChart
        bazi = BaZiChart(engine.birth_dt)
        bal = bazi.get_element_balance()
        counts = bal.get('counts', {})
        dm = bazi.get_day_master()
        pillars = bazi.get_four_pillars()
        for elem in ['Wood','Fire','Earth','Metal','Water']:
            chinese_nodes.append({
                'id': elem, 'label': elem,
                'count': counts.get(elem, 0),
                'is_day_master': elem == dm.get('element', ''),
                'strength': bal.get('day_master_strength', '') if elem == dm.get('element', '') else '',
            })
    except Exception:
        for elem in ['Wood','Fire','Earth','Metal','Water']:
            chinese_nodes.append({'id': elem, 'label': elem, 'count': 0, 'is_day_master': False, 'strength': ''})

    # Numerology: 9 numbers
    num_nodes = []
    try:
        from app.services.numerology.core import NumerologyEngine
        nc = NumerologyEngine(name='', birth_date=engine.birth_dt.date())
        grid = nc.get_lo_shu_grid()
        grid_counts = grid.get('grid', {})
        mulank = nc.get_mulank().get('number', 0)
        bhagyank = nc.get_bhagyank().get('number', 0)
        for n in range(1, 10):
            num_nodes.append({
                'id': str(n), 'label': str(n),
                'count': grid_counts.get(n, grid_counts.get(str(n), 0)),
                'present': n in grid.get('present_numbers', []),
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


def _build_system_prompt(sys_name, nodes, engine):
    from app.services.jyotish_engine import JyotishEngine
    from datetime import datetime
    now = datetime.now()
    try:
        e_now = JyotishEngine(now, engine.latitude, engine.longitude)
        tp = e_now.planets
    except Exception:
        tp = {}
    try:
        dasha = engine.get_vimshottari_dasha().get('dasha_string', '')
    except Exception:
        dasha = ''
    node_lines = []
    for n in nodes:
        parts = [n['id']]
        for k in ['sign','house','nakshatra','sub_lord','count','strength']:
            v = n.get(k)
            if v and v != 0 and v != '': parts.append(f'{k}={v}')
        if n.get('retrograde'): parts.append('retrograde')
        if n.get('is_day_master'): parts.append('Day Master')
        if n.get('is_mulank'): parts.append('Root Number')
        if n.get('is_bhagyank'): parts.append('Destiny')
        if not n.get('present', True): parts.append('MISSING')
        node_lines.append('  ' + ' | '.join(parts))
    transit_lines = []
    for pl in ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu']:
        td = tp.get(pl, {})
        if isinstance(td, dict) and td.get('rashi_name'):
            transit_lines.append(f'  {pl}: {td.get("rashi_name","")} H{td.get("house","")}')
    node_str = '\n'.join(node_lines)
    transit_str = '\n'.join(transit_lines)
    node_json = []
    for i, n in enumerate(nodes):
        comma = ',' if i < len(nodes) - 1 else ''
        node_json.append(f'    "{n["id"]}": {{"title":"3-5 words","what":"1-2 sentences","significance":"2-3 sentences","effect":"2-3 sentences current impact","cta_significance":"4-6 words","cta_effect":"4-6 words"}}{comma}')
    nodes_block = '\n'.join(node_json)
    return f'''You are the Oracle.
Make them feel seen, not informed.
Root the language in human behaviour, profound psychology, colour psychology, emotions and brain patterns — so they cannot stop coming back.

This is a CORE CHART WHEEL. The person selects each node to learn what it means and how it affects them NOW.

{sys_name.upper()} nodes:
{node_str}
Dasha: {dasha}
Date: {now.strftime("%A, %B %d, %Y")}
Transits:
{transit_str}

Return ONLY valid JSON:
{{
  "headline": "3-5 words. Short. Punchy.",
{nodes_block}
}}

~500 words. Titles SHORT. Do/dont only if genuinely needed.'''


class _CoreChartRequest(BaseModel):
    kundli_data: Optional[dict] = None
    language: Optional[str] = 'en'


def _extract_birth(kundli_data):
    if not kundli_data:
        return None
    raw = kundli_data.get('raw', {})
    birth = raw.get('birth_details', {})
    if not birth:
        birth = kundli_data.get('birth_details', {})
    if not birth:
        return None
    try:
        return {
            'year': int(birth.get('year', 2000)),
            'month': int(birth.get('month', 1)),
            'day': int(birth.get('day', 1)),
            'hour': int(birth.get('hour', 12)),
            'minute': int(birth.get('minute', 0)),
            'lat': float(birth.get('latitude', 28.6)),
            'lng': float(birth.get('longitude', 77.2)),
        }
    except (TypeError, ValueError):
        return None


@router.post('/core-chart')
async def get_core_chart(request_body: _CoreChartRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit
    import json as json_parse
    import asyncio
    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))
    birth_data = _extract_birth(request_body.kundli_data)
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    try:
        from app.services.oracle.engine_cache import get_cached_engine
        birth_dt = datetime(birth_data['year'], birth_data['month'], birth_data['day'], birth_data.get('hour', 12), birth_data.get('minute', 0))
        engine, _ = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        wheel_data = _build_wheel_data(engine)

        # 5 parallel LLM calls — one per system
        async def fetch_system(sys_name):
            nodes = wheel_data[sys_name]['nodes']
            prompt = _build_system_prompt(sys_name, nodes, engine)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}', 'Content-Type': 'application/json'},
                    json={'model': settings.OPENROUTER_MODEL, 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': f'Read my {sys_name} chart nodes.'}], 'max_tokens': 2500, 'temperature': 0.75},
                    timeout=90.0,
                )
            if response.status_code != 200:
                return {}
            raw = response.json()['choices'][0]['message']['content'].strip()
            cleaned = raw.replace('```json', '').replace('```', '').strip()
            try:
                return json_parse.loads(cleaned)
            except json_parse.JSONDecodeError:
                s, e = cleaned.find('{'), cleaned.rfind('}')
                if s >= 0 and e > s:
                    try:
                        return json_parse.loads(cleaned[s:e+1])
                    except json_parse.JSONDecodeError:
                        pass
            return {}

        systems = ['vedic', 'kp', 'western', 'chinese', 'numerology']
        results = await asyncio.gather(*[fetch_system(s) for s in systems], return_exceptions=True)
        readings = {}
        for i, s in enumerate(systems):
            r = results[i]
            readings[s] = r if isinstance(r, dict) else {}

        return {'wheels': wheel_data, 'readings': readings}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


core_chart_router = router
