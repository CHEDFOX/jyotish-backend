"""
CHART OVERVIEW — Birth chart snapshot across all 5 systems. One LLM call.

Endpoint: POST /api/public/chart-overview
"""

from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, parse_json_or_text,
)


router = APIRouter(prefix="/public", tags=["Chart Overview"])


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


def _vedic(engine) -> str:
    lines = []
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    lines.append(f"Ascendant: {asc.get('rashi_name', '')} (lord: {asc.get('lord', '')})")

    moon = _pl(planets, 'Moon')
    lines.append(f"Moon: {moon.get('rashi_name', '')} · {moon.get('nakshatra_name', '')} · H{moon.get('house', '?')}")
    sun = _pl(planets, 'Sun')
    lines.append(f"Sun: {sun.get('rashi_name', '')} · H{sun.get('house', '?')}")

    for p in ('Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'):
        pd = _pl(planets, p)
        if pd.get('house'):
            status = []
            if pd.get('is_exalted'): status.append('exalted')
            if pd.get('is_debilitated'): status.append('debilitated')
            if pd.get('is_retrograde') or pd.get('retrograde'): status.append('retrograde')
            if pd.get('is_combust') or pd.get('combust'): status.append('combust')
            st = f" ({', '.join(status)})" if status else ''
            lines.append(f"{p}: {pd.get('rashi_name', '')} · H{pd['house']}{st}")

    yogas = safe(engine.get_yogas, {}) or {}
    if isinstance(yogas, dict):
        highlights = yogas.get('highlights', [])
        names = [y.get('name', '') for y in highlights[:4] if isinstance(y, dict) and y.get('name')]
        if names:
            lines.append(f"Yogas: {', '.join(names)}")

    dasha = safe(engine.get_vimshottari_dasha, {}) or {}
    if isinstance(dasha, dict) and dasha.get('dasha_string'):
        lines.append(f"Current dasha: {dasha['dasha_string']}")

    return '\n'.join(lines)


def _kp(engine) -> str:
    lines = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp = KPComplete(engine)
        cusps = kp.get_placidus_cusps() or {}
        if isinstance(cusps, dict):
            for h in (1, 7, 10):
                c = cusps.get(str(h), cusps.get(h, {}))
                if isinstance(c, dict):
                    lines.append(f"H{h} cusp: {c.get('sign', '')} {c.get('degree', '')}° · sub-lord: {c.get('sub_lord', '')}")
        rp = kp.get_ruling_planets() or {}
        if isinstance(rp, dict):
            rp_list = rp.get('common_rp', rp.get('ruling_planets', []))
            if isinstance(rp_list, list) and rp_list:
                lines.append(f"Ruling planets: {', '.join(rp_list)}")
        for h in (1, 2, 7, 10, 11):
            try:
                f = kp.check_fruitfulness(house=h)
                if isinstance(f, dict) and f.get('verdict'):
                    lines.append(f"H{h}: {f['verdict']} ({f.get('cuspal_sub_lord', '')})")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"KP limited: {str(e)[:50]}")
    return '\n'.join(lines) if lines else 'KP data unavailable.'


def _western(engine) -> str:
    lines = []
    try:
        from app.services.western.chart import WesternChart
        wc = WesternChart(engine.birth_dt, engine.latitude, engine.longitude)
        big3 = safe(wc.get_big_three, {}) or {}
        if isinstance(big3, dict):
            lines.append(f"Sun: {big3.get('sun_sign', '')}")
            lines.append(f"Moon: {big3.get('moon_sign', '')}")
            lines.append(f"Rising: {big3.get('rising_sign', '')}")
        eb = safe(wc.get_element_balance, {}) or {}
        if isinstance(eb, dict):
            dom = max(eb.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
            lines.append(f"Dominant element: {dom[0]} ({dom[1]})")
            lines.append(f"Fire:{eb.get('fire',0)} Earth:{eb.get('earth',0)} Air:{eb.get('air',0)} Water:{eb.get('water',0)}")
        aspects = safe(wc.get_aspects, []) or []
        if isinstance(aspects, list):
            tight = [a for a in aspects if isinstance(a, dict) and abs(a.get('orb', 99)) < 2]
            for a in tight[:4]:
                lines.append(f"{a.get('person1_planet','')} {a.get('aspect','')} {a.get('person2_planet','')} (orb {a.get('orb',0):.1f}°)")
        configs = safe(wc.get_configurations, []) or []
        if isinstance(configs, list) and configs:
            names = [c.get('name', '') for c in configs[:3] if isinstance(c, dict)]
            if names:
                lines.append(f"Patterns: {', '.join(names)}")
    except Exception as e:
        lines.append(f"Western limited: {str(e)[:50]}")
    return '\n'.join(lines) if lines else 'Western data unavailable.'


def _chinese(engine) -> str:
    lines = []
    try:
        from app.services.chinese.bazi import BaZiChart
        bazi = BaZiChart(engine.birth_dt)
        dm = bazi.get_day_master() or {}
        if isinstance(dm, dict):
            lines.append(f"Day Master: {dm.get('stem', '')} {dm.get('element', '')} ({dm.get('polarity', '')})")
        pillars = bazi.get_four_pillars() or {}
        if isinstance(pillars, dict):
            for p in ('year', 'month', 'day', 'hour'):
                pil = pillars.get(p, {})
                if isinstance(pil, dict):
                    lines.append(f"{p.title()}: {pil.get('stem', '')} {pil.get('branch', '')} ({pil.get('animal', '')} · {pil.get('element', '')})")
        balance = bazi.get_element_balance() or {}
        if isinstance(balance, dict):
            elements = balance.get('counts', {})
            if isinstance(elements, dict):
                lines.append(f"Elements: {', '.join(f'{k}:{v}' for k, v in elements.items() if isinstance(v, (int, float)))}")
            lines.append(f"Day Master element: {balance.get('day_master_element', '')}")
        try:
            tg = bazi.get_ten_gods()
            if isinstance(tg, dict):
                gods = tg.get('gods', tg.get('pillars', []))
                if isinstance(gods, list):
                    names = [g.get('god', g.get('name', '')) for g in gods if isinstance(g, dict)]
                    if names:
                        lines.append(f"Ten Gods: {', '.join(names[:4])}")
        except Exception:
            pass
    except Exception as e:
        lines.append(f"Chinese limited: {str(e)[:50]}")
    return '\n'.join(lines) if lines else 'Chinese data unavailable.'


def _numerology(engine, name: str = '') -> str:
    lines = []
    try:
        from app.services.numerology.core import NumerologyEngine
        bd = engine.birth_dt.date() if hasattr(engine.birth_dt, 'date') else date.today()
        nc = NumerologyEngine(name=name, birth_date=bd)

        m = nc.get_mulank() or {}
        if isinstance(m, dict):
            lines.append(f"Mulank (Root): {m.get('number', '')} ({m.get('planet', '')})")
        b = nc.get_bhagyank() or {}
        if isinstance(b, dict):
            lines.append(f"Bhagyank (Destiny): {b.get('number', '')} ({b.get('planet', '')})")
        if name:
            n = nc.get_namank() or {}
            if isinstance(n, dict):
                lines.append(f"Namank (Name): {n.get('number', '')} ({n.get('planet', '')})")
        py = nc.get_personal_year() or {}
        if isinstance(py, dict):
            lines.append(f"Personal Year: {py.get('number', '')}")
        try:
            grid = nc.get_lo_shu_grid() or {}
            if isinstance(grid, dict):
                present = grid.get('present_numbers', [])
                missing = grid.get('missing_numbers', [])
                if present:
                    lines.append(f"Lo Shu present: {', '.join(str(n) for n in present)}")
                if missing:
                    lines.append(f"Lo Shu missing: {', '.join(str(n) for n in missing)}")
        except Exception:
            pass
    except Exception as e:
        lines.append(f"Numerology limited: {str(e)[:50]}")
    return '\n'.join(lines) if lines else 'Numerology data unavailable.'


def _assemble(engine, name: str = '') -> Dict:
    return {
        'vedic': _vedic(engine),
        'kp': _kp(engine),
        'western': _western(engine),
        'chinese': _chinese(engine),
        'numerology': _numerology(engine, name),
    }


def _prompt(data: Dict, language: str = 'en') -> str:
    return f"""{voice_card(language)}

This is a BIRTH CHART OVERVIEW. One-time deep look at who this person is across 5 systems.

Data:
VEDIC:
{data['vedic']}

KP:
{data['kp']}

WESTERN:
{data['western']}

CHINESE:
{data['chinese']}

NUMEROLOGY:
{data['numerology']}

Return ONLY valid JSON:
{{
  "hook_title": "max 8 words. Persuasive. Identity-level.",
  "hook_body": "2 sentences. The pattern they live but never name.",
  "cta_dive": "4-6 words.",
  "secret": "ONE precise cryptic line about THIS chart. Specific factual truth: rare yoga, exact degree, vargottama planet, ratio, unusual configuration. Style: factual not poetic. Max 12 words.",
  "vedic":      {{ "headline": "3-5 words", "glance": "1 line", "snapshot": "3-5 data points with dots", "reading": "3-5 sentences", "deeper": "3-5 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "kp":         {{ "headline": "3-5 words", "glance": "1 line", "snapshot": "3-5 data points", "reading": "3-5 sentences", "deeper": "3-5 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "western":    {{ "headline": "3-5 words", "glance": "1 line", "snapshot": "3-5 data points", "reading": "3-5 sentences", "deeper": "3-5 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "chinese":    {{ "headline": "3-5 words", "glance": "1 line", "snapshot": "3-5 data points", "reading": "3-5 sentences", "deeper": "3-5 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "numerology": {{ "headline": "3-5 words", "glance": "1 line", "snapshot": "3-5 data points", "reading": "3-5 sentences", "deeper": "3-5 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "closing": "1-2 sentences. All five unified." }}
}}

~600 words total. Headlines SHORT and punchy. Do/dont only when genuinely needed."""


class _ChartOverviewRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    name: Optional[str] = ''
    language: Optional[str] = 'en'


@router.post('/chart-overview')
async def get_chart_overview(request_body: _ChartOverviewRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = _assemble(engine, request_body.name or '')
        prompt = _prompt(data, language)
        raw = await call_llm(prompt, settings,
                             user_message='Show me my birth chart across all five lenses.',
                             max_tokens=4000, temperature=0.75)
        overview = parse_json_or_text(raw)

        return {
            'overview': overview,
            'version': 2,
            'cache_ttl_seconds': 2592000,  # 30 days — depends on dasha shifts
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


chart_overview_router = router
