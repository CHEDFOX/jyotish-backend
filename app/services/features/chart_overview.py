"""
CHART OVERVIEW — Birth chart snapshot across all 5 systems.

One call. One LLM call. Five compact, psychologically sharp overviews.
Cached at frontend for 7+ days (birth data doesn't change).

Usage in main.py:
    from app.services.features.chart_overview import chart_overview_router
    app.include_router(chart_overview_router, prefix="/api")
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, date
import httpx

router = APIRouter(prefix="/public", tags=["Chart Overview"])


def _safe(fn, default=None):
    try:
        r = fn()
        return r if r is not None else default
    except Exception:
        return default


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


# ═══════════════════════════════════════════════════════════════
# DATA BUILDERS
# ═══════════════════════════════════════════════════════════════

def _vedic(engine) -> str:
    lines = []
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}

    lines.append(f"Ascendant: {asc.get('rashi_name', '')} (lord: {asc.get('lord', '')})")

    moon = _pl(planets, 'Moon')
    lines.append(f"Moon: {moon.get('rashi_name', '')} · {moon.get('nakshatra_name', '')} · H{moon.get('house', '?')}")

    sun = _pl(planets, 'Sun')
    lines.append(f"Sun: {sun.get('rashi_name', '')} · H{sun.get('house', '?')}")

    # Planet positions compact
    for p in ['Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']:
        pd = _pl(planets, p)
        if pd.get('house'):
            status = []
            if pd.get('is_exalted'): status.append('exalted')
            if pd.get('is_debilitated'): status.append('debilitated')
            if pd.get('is_retrograde') or pd.get('retrograde'): status.append('retrograde')
            if pd.get('is_combust') or pd.get('combust'): status.append('combust')
            st = f" ({', '.join(status)})" if status else ''
            lines.append(f"{p}: {pd.get('rashi_name', '')} · H{pd['house']}{st}")

    # Yogas
    yogas = _safe(engine.get_yogas, {})
    if isinstance(yogas, dict):
        highlights = yogas.get('highlights', [])
        names = [y.get('name', '') for y in highlights[:4] if isinstance(y, dict) and y.get('name')]
        if names:
            lines.append(f"Yogas: {', '.join(names)}")

    # Dasha
    dasha = _safe(engine.get_vimshottari_dasha, {})
    if isinstance(dasha, dict) and dasha.get('dasha_string'):
        lines.append(f"Current dasha: {dasha['dasha_string']}")

    return '\n'.join(lines)


def _kp(engine) -> str:
    lines = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp = KPComplete(engine)

        cusps = kp.get_placidus_cusps()
        if isinstance(cusps, dict):
            for h in [1, 7, 10]:
                c = cusps.get(str(h), cusps.get(h, {}))
                if isinstance(c, dict):
                    lines.append(f"H{h} cusp: {c.get('sign', '')} {c.get('degree', '')}° · sub-lord: {c.get('sub_lord', '')}")

        rp = kp.get_ruling_planets()
        if isinstance(rp, dict):
            rp_list = rp.get('common_rp', rp.get('ruling_planets', []))
            if isinstance(rp_list, list) and rp_list:
                lines.append(f"Ruling planets: {', '.join(rp_list)}")

        for h in [1, 2, 7, 10, 11]:
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

        big3 = wc.get_big_three()
        if isinstance(big3, dict):
            lines.append(f"Sun: {big3.get('sun_sign', '')}")
            lines.append(f"Moon: {big3.get('moon_sign', '')}")
            lines.append(f"Rising: {big3.get('rising_sign', '')}")

        eb = wc.get_element_balance()
        if isinstance(eb, dict):
            dom = max(eb.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
            lines.append(f"Dominant element: {dom[0]} ({dom[1]})")
            lines.append(f"Fire:{eb.get('fire',0)} Earth:{eb.get('earth',0)} Air:{eb.get('air',0)} Water:{eb.get('water',0)}")

        aspects = wc.get_aspects()
        if isinstance(aspects, list):
            tight = [a for a in aspects if isinstance(a, dict) and abs(a.get('orb', 99)) < 2]
            for a in tight[:4]:
                lines.append(f"{a.get('person1_planet','')} {a.get('aspect','')} {a.get('person2_planet','')} (orb {a.get('orb',0):.1f}°)")

        configs = _safe(wc.get_configurations, [])
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

        dm = bazi.get_day_master()
        if isinstance(dm, dict):
            lines.append(f"Day Master: {dm.get('stem', '')} {dm.get('element', '')} ({dm.get('polarity', '')})")
            if dm.get('description'):
                lines.append(f"Nature: {dm['description'][:100]}")

        pillars = bazi.get_four_pillars()
        if isinstance(pillars, dict):
            for p in ['year', 'month', 'day', 'hour']:
                pil = pillars.get(p, {})
                if isinstance(pil, dict):
                    lines.append(f"{p.title()}: {pil.get('stem', '')} {pil.get('branch', '')} ({pil.get('animal', '')} · {pil.get('element', '')})")

        balance = bazi.get_element_balance()
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

        mulank = nc.get_mulank()
        if isinstance(mulank, dict):
            lines.append(f"Mulank (Root): {mulank.get('number', '')} — {mulank.get('planet', '')} ({mulank.get('meaning', '')[:60]})")

        bhagyank = nc.get_bhagyank()
        if isinstance(bhagyank, dict):
            lines.append(f"Bhagyank (Destiny): {bhagyank.get('number', '')} — {bhagyank.get('planet', '')} ({bhagyank.get('meaning', '')[:60]})")

        if name:
            namank = nc.get_namank()
            if isinstance(namank, dict):
                lines.append(f"Namank (Name): {namank.get('number', '')} — {namank.get('planet', '')} ({namank.get('meaning', '')[:60]})")

        py = nc.get_personal_year()
        if isinstance(py, dict):
            lines.append(f"Personal Year: {py.get('number', '')} — {py.get('theme', py.get('meaning', ''))[:60]}")

        try:
            grid = nc.get_lo_shu_grid()
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


# ═══════════════════════════════════════════════════════════════
# ASSEMBLER + PROMPT
# ═══════════════════════════════════════════════════════════════

def _assemble(engine, name: str = '') -> Dict:
    return {
        'vedic': _vedic(engine),
        'kp': _kp(engine),
        'western': _western(engine),
        'chinese': _chinese(engine),
        'numerology': _numerology(engine, name),
    }


def _prompt(data, language='en'):
    lang = ''
    if language and language.lower() not in ('english', 'en'):
        lang = ' Write in ' + language + '.'
    return '''You are the Oracle.''' + lang + '''
Make them feel seen, not informed.
Root the language in human behaviour, profound psychology, colour psychology, emotions and brain patterns — so they cannot stop coming back.

This is a BIRTH CHART OVERVIEW. One-time deep look at who this person is.

Data:
VEDIC: ''' + data.get('vedic','') + '''
KP: ''' + data.get('kp','') + '''
WESTERN: ''' + data.get('western','') + '''
CHINESE: ''' + data.get('chinese','') + '''
NUMEROLOGY: ''' + data.get('numerology','') + '''

Return ONLY valid JSON:
{
  "hook_title": "max 8 words. Persuasive. Identity-level.",
  "hook_body": "2 sentences. The pattern they live but never name.",
  "cta_dive": "4-6 words.",
  "vedic": {"headline":"3-5 words","glance":"1 line","snapshot":"3-5 data points with dots","reading":"3-5 sentences","deeper":"3-5 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "kp": {"headline":"3-5 words","glance":"1 line","snapshot":"3-5 data points","reading":"3-5 sentences","deeper":"3-5 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "western": {"headline":"3-5 words","glance":"1 line","snapshot":"3-5 data points","reading":"3-5 sentences","deeper":"3-5 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "chinese": {"headline":"3-5 words","glance":"1 line","snapshot":"3-5 data points","reading":"3-5 sentences","deeper":"3-5 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "numerology": {"headline":"3-5 words","glance":"1 line","snapshot":"3-5 data points","reading":"3-5 sentences","deeper":"3-5 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","closing":"1-2 sentences. All five unified."}
}

~600 words total. Headlines SHORT punchy. Do/dont only when genuinely needed.'''


class _ChartOverviewRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    name: Optional[str] = ''
    language: Optional[str] = 'en'


def _extract_birth(kundli_data):
    if not kundli_data:
        return None
    raw = kundli_data.get("raw", {})
    birth = raw.get("birth_details", {})
    if not birth:
        birth = kundli_data.get("birth_details", {})
    if not birth:
        return None
    try:
        return {
            'year': int(birth.get('year', 2000)), 'month': int(birth.get('month', 1)),
            'day': int(birth.get('day', 1)), 'hour': int(birth.get('hour', 12)),
            'minute': int(birth.get('minute', 0)),
            'lat': float(birth.get('latitude', 28.6139)),
            'lng': float(birth.get('longitude', 77.2090)),
        }
    except (TypeError, ValueError):
        return None


@router.post("/chart-overview")
async def get_chart_overview(request_body: _ChartOverviewRequest, request: Request):
    """Birth chart overview across all 5 systems."""
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        import json as json_parse

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _ = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])

        data = _assemble(engine, request_body.name or '')
        system_prompt = _prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Show me my birth chart across all five lenses."},
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.75,
                },
                timeout=90.0,
            )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="AI service unavailable")

        raw_text = response.json()["choices"][0]["message"]["content"].strip()
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            overview = json_parse.loads(cleaned)
        except json_parse.JSONDecodeError:
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start >= 0 and end > start:
                try:
                    overview = json_parse.loads(cleaned[start:end + 1])
                except json_parse.JSONDecodeError:
                    overview = {"error": "parse_failed", "raw": raw_text}
            else:
                overview = {"error": "no_json", "raw": raw_text}

        return {'overview': overview}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chart overview error: {str(e)[:200]}")


chart_overview_router = router
