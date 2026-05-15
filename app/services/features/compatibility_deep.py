"""
COMPATIBILITY DEEP — General compatibility across all 5 systems.

Endpoints:
  POST /api/public/compatibility-deep  — full reading (per system: info + score + reading + deeper + do/dont)
  POST /api/public/compatibility-hook  — teaser/hook for the compatibility section
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, call_llm, parse_json_or_text,
)


router = APIRouter(prefix="/public", tags=["Compatibility"])


# Visual tokens (facts, not interpretation)
ELEMENT_COLORS = {
    'fire': '#E8A040', 'Fire': '#E8A040',
    'earth': '#8B7355', 'Earth': '#8B7355',
    'air': '#7EB8D0', 'Air': '#7EB8D0',
    'water': '#4A9E9E', 'Water': '#4A9E9E',
    'metal': '#A8B0B8', 'Metal': '#A8B0B8',
    'wood': '#4A8C5C', 'Wood': '#4A8C5C',
    'ether': '#B8A0D0', 'Ether': '#B8A0D0',
}

SIGN_ELEMENTS = {
    'Aries': 'fire', 'Leo': 'fire', 'Sagittarius': 'fire',
    'Taurus': 'earth', 'Virgo': 'earth', 'Capricorn': 'earth',
    'Gemini': 'air', 'Libra': 'air', 'Aquarius': 'air',
    'Cancer': 'water', 'Scorpio': 'water', 'Pisces': 'water',
}


def _dominant_element_vedic(engine) -> str:
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    counts = {'fire': 0, 'earth': 0, 'air': 0, 'water': 0}
    for p in ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'):
        pd = planets.get(p, {})
        if isinstance(pd, dict):
            elem = SIGN_ELEMENTS.get(pd.get('rashi_name', ''), '')
            if elem:
                counts[elem] = counts.get(elem, 0) + (2 if p in ('Sun', 'Moon') else 1)
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    asc_elem = SIGN_ELEMENTS.get(asc.get('rashi_name', ''), '')
    if asc_elem:
        counts[asc_elem] = counts.get(asc_elem, 0) + 2
    return max(counts, key=counts.get) if counts else 'fire'


def _dominant_element_chinese(engine) -> str:
    try:
        from app.services.chinese.bazi import BaZiChart
        bazi = BaZiChart(engine.birth_dt)
        balance = bazi.get_element_balance()
        if isinstance(balance, dict):
            elements = balance.get('elements', {})
            if isinstance(elements, dict) and elements:
                return max(elements, key=elements.get)
            return balance.get('day_master_element', 'wood')
    except Exception:
        return 'wood'


def _get_dominant_color(engine) -> str:
    chinese = _dominant_element_chinese(engine)
    vedic = _dominant_element_vedic(engine)
    return ELEMENT_COLORS.get(chinese) or ELEMENT_COLORS.get(vedic) or '#E8A040'


# ═══════════════════════════════════════════════════════════════
# DATA BUILDERS — facts only, no English interpretation prose
# ═══════════════════════════════════════════════════════════════

def _vedic_compat(e1, e2) -> str:
    lines = []
    try:
        from app.services.compatibility.synastry import analyze_synastry
        syn = safe(lambda: analyze_synastry(e1, e2), {}) or {}
        if isinstance(syn, dict):
            moon = syn.get('moon_compatibility', {}) or {}
            if isinstance(moon, dict) and moon.get('score') is not None:
                lines.append(f"Moon compatibility score: {moon.get('score', '?')}/10")
            overlays = syn.get('planet_overlays', []) or []
            if isinstance(overlays, list):
                for o in overlays[:5]:
                    if isinstance(o, dict):
                        h = o.get('falls_in_house', '')
                        p = o.get('planet', '')
                        if p and h:
                            lines.append(f"  {p} falls in partner's H{h}")
            dasha = syn.get('dasha_sync', {}) or {}
            if isinstance(dasha, dict):
                # Keep numeric/categorical only
                for k in ('score', 'level', 'in_sync'):
                    v = dasha.get(k)
                    if v is not None:
                        lines.append(f"Dasha {k}: {v}")
    except Exception as e:
        lines.append(f"(synastry partial: {str(e)[:40]})")

    try:
        from app.services.compatibility.manglik import ManglikAnalysis
        m1 = safe(lambda: ManglikAnalysis(e1, e1.ascendant_rashi).check_manglik(), {}) or {}
        m2 = safe(lambda: ManglikAnalysis(e2, e2.ascendant_rashi).check_manglik(), {}) or {}
        if isinstance(m1, dict) and isinstance(m2, dict):
            both = bool(m1.get('is_manglik')) and bool(m2.get('is_manglik'))
            lines.append(f"Manglik — P1: {'Yes' if m1.get('is_manglik') else 'No'}, P2: {'Yes' if m2.get('is_manglik') else 'No'}, mutual cancellation: {both}")
    except Exception:
        pass

    return '\n'.join(lines) if lines else 'Vedic synastry data limited.'


def _kp_compat(e1, e2) -> str:
    lines = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp1 = KPComplete(e1)
        kp2 = KPComplete(e2)
        rp1 = safe(kp1.get_ruling_planets, {}) or {}
        rp2 = safe(kp2.get_ruling_planets, {}) or {}
        if isinstance(rp1, dict) and isinstance(rp2, dict):
            list1 = set(rp1.get('common_rp', rp1.get('ruling_planets', [])) or [])
            list2 = set(rp2.get('common_rp', rp2.get('ruling_planets', [])) or [])
            common = list1 & list2
            lines.append(f"P1 ruling planets: {sorted(list1) or 'unknown'}")
            lines.append(f"P2 ruling planets: {sorted(list2) or 'unknown'}")
            lines.append(f"Common: {sorted(common) or 'none'} ({len(common)} of {max(len(list1), 1)})")
        for h in (7, 11):
            try:
                f1 = safe(lambda h=h: kp1.check_fruitfulness(house=h), {}) or {}
                f2 = safe(lambda h=h: kp2.check_fruitfulness(house=h), {}) or {}
                v1 = f1.get('verdict', '?') if isinstance(f1, dict) else '?'
                v2 = f2.get('verdict', '?') if isinstance(f2, dict) else '?'
                lines.append(f"House {h} fruitfulness — P1: {v1}, P2: {v2}")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"(KP partial: {str(e)[:40]})")
    return '\n'.join(lines) if lines else 'KP data limited.'


def _western_compat(e1, e2) -> str:
    lines = []
    try:
        from app.services.western.chart import WesternChart
        from app.services.western.compatibility import WesternCompatibility
        wc1 = WesternChart(e1.birth_dt, e1.latitude, e1.longitude)
        wc2 = WesternChart(e2.birth_dt, e2.latitude, e2.longitude)
        wcompat = WesternCompatibility(wc1, wc2)
        report = safe(wcompat.generate_synastry_report, {}) or {}
        if isinstance(report, dict):
            for label, key in (('P1', 'person1'), ('P2', 'person2')):
                p = report.get(key, {})
                if isinstance(p, dict):
                    lines.append(
                        f"{label}: Sun {p.get('sun_sign', '')}, Moon {p.get('moon_sign', '')}, "
                        f"Rising {p.get('rising_sign', '')}, Ruler {p.get('chart_ruler', '')} in H{p.get('chart_ruler_house', '')}, "
                        f"MC {p.get('midheaven_sign', '')}"
                    )
            for label, wc in (('P1', wc1), ('P2', wc2)):
                eb = safe(wc.get_element_balance, {}) or {}
                if isinstance(eb, dict):
                    elems = eb.get('elements', {}) or {}
                    if isinstance(elems, dict):
                        cs = ', '.join(f"{k}:{v}" for k, v in elems.items() if isinstance(v, (int, float)))
                        lines.append(f"{label} elements: {cs} | dominant {eb.get('dominant_element', '')} | weak {eb.get('weak_element', '')}")
            # Aspects: keep planet + aspect + nature + orb + strength. Drop English interpretation.
            aspects = report.get('aspects', []) or []
            if isinstance(aspects, list):
                lines.append(f"Total synastry aspects: {len(aspects)}")
                for a in aspects[:10]:
                    if isinstance(a, dict):
                        lines.append(
                            f"  {a.get('person1_planet', '')} {a.get('aspect', '')} {a.get('person2_planet', '')}"
                            f" — {a.get('nature', '')} (orb {a.get('orb', 0):.1f}, strength {a.get('strength', 0):.2f})"
                        )
        score = safe(wcompat.get_compatibility_score, {}) or {}
        if isinstance(score, dict):
            lines.append(f"Score: {score.get('score', '')}% — {score.get('verdict', '')}")
            lines.append(f"Harmonious aspects: {score.get('harmonious', 0)} | Challenging: {score.get('challenging', 0)}")
    except Exception as e:
        lines.append(f"(Western partial: {str(e)[:40]})")
    return '\n'.join(lines) if lines else 'Western data limited.'


def _chinese_compat(e1, e2) -> str:
    lines = []
    try:
        from app.services.chinese.bazi import BaZiChart
        b1 = BaZiChart(e1.birth_dt)
        b2 = BaZiChart(e2.birth_dt)

        dm1 = safe(b1.get_day_master, {}) or {}
        dm2 = safe(b2.get_day_master, {}) or {}
        if isinstance(dm1, dict):
            pol = dm1.get('polarity', '')
            lines.append(f"P1 Day Master: {dm1.get('element', '')}" + (f" ({pol})" if pol else ''))
        if isinstance(dm2, dict):
            pol = dm2.get('polarity', '')
            lines.append(f"P2 Day Master: {dm2.get('element', '')}" + (f" ({pol})" if pol else ''))

        a1 = safe(b1.get_animal_sign, {}) or {}
        a2 = safe(b2.get_animal_sign, {}) or {}
        if isinstance(a1, dict) and isinstance(a2, dict):
            an1 = a1.get('animal') or a1.get('branch', {}).get('animal', '')
            an2 = a2.get('animal') or a2.get('branch', {}).get('animal', '')
            lines.append(f"Animals — P1: {an1} | P2: {an2}")

        bal1 = safe(b1.get_element_balance, {}) or {}
        bal2 = safe(b2.get_element_balance, {}) or {}
        for label, bal in (('P1', bal1), ('P2', bal2)):
            if isinstance(bal, dict):
                c = bal.get('counts', {})
                if isinstance(c, dict):
                    cs = ', '.join(f"{k}:{v}" for k, v in c.items() if isinstance(v, (int, float)))
                    lines.append(f"{label} elements: {cs}")
    except Exception as e:
        lines.append(f"(Chinese partial: {str(e)[:40]})")

    # Engine-level Chinese compatibility — keep numeric/categorical, drop prose
    try:
        compat = safe(lambda: e1.get_chinese_compatibility(e2), {}) or {}
        if isinstance(compat, dict):
            for k, v in compat.items():
                if isinstance(v, (int, float, bool)):
                    lines.append(f"{k}: {v}")
    except Exception:
        pass

    return '\n'.join(lines) if lines else 'Chinese data limited.'


def _numerology_compat(e1, e2, name1='', name2='') -> str:
    lines = []
    try:
        from datetime import date
        from app.services.numerology.core import NumerologyEngine, check_number_compatibility
        bd1 = e1.birth_dt.date() if hasattr(e1.birth_dt, 'date') else date.today()
        bd2 = e2.birth_dt.date() if hasattr(e2.birth_dt, 'date') else date.today()
        nc1 = NumerologyEngine(name=name1, birth_date=bd1)
        nc2 = NumerologyEngine(name=name2, birth_date=bd2)

        for label, nc, nm in (('P1', nc1, name1), ('P2', nc2, name2)):
            m = safe(nc.get_mulank, {}) or {}
            b = safe(nc.get_bhagyank, {}) or {}
            if isinstance(m, dict):
                lines.append(f"{label} Root: {m.get('number', '')} ({m.get('planet', '')})")
            if isinstance(b, dict):
                lines.append(f"{label} Destiny: {b.get('number', '')} ({b.get('planet', '')})")
            if nm:
                n = safe(nc.get_namank, {}) or {}
                if isinstance(n, dict):
                    ch = n.get('chaldean', {}) or {}
                    if isinstance(ch, dict):
                        lines.append(f"{label} Name number: {ch.get('root', '')} [{nm}]")

        compat = safe(lambda: check_number_compatibility(bd1, bd2), {}) or {}
        if isinstance(compat, dict):
            lines.append(f"Compatibility score: {compat.get('score', '')}%")
            lines.append(f"Verdict: {compat.get('verdict', '')}")
            lines.append(f"Root match: {bool(compat.get('mulank_match'))}, Destiny match: {bool(compat.get('bhagyank_match'))}")

        for label, nc in (('P1', nc1), ('P2', nc2)):
            grid = safe(nc.get_lo_shu_grid, {}) or {}
            if isinstance(grid, dict):
                missing = grid.get('missing_numbers', [])
                arrows = grid.get('complete_arrows', [])
                if missing:
                    lines.append(f"{label} Lo Shu missing: {missing}")
                if arrows:
                    lines.append(f"{label} Lo Shu complete arrows: {arrows}")
    except Exception as e:
        lines.append(f"(Numerology partial: {str(e)[:40]})")
    return '\n'.join(lines) if lines else 'Numerology data limited.'


def _assemble(e1, e2, name1='', name2='') -> Dict:
    return {
        'vedic': _vedic_compat(e1, e2),
        'kp': _kp_compat(e1, e2),
        'western': _western_compat(e1, e2),
        'chinese': _chinese_compat(e1, e2),
        'numerology': _numerology_compat(e1, e2, name1, name2),
        'color1': _get_dominant_color(e1),
        'color2': _get_dominant_color(e2),
    }


# ═══════════════════════════════════════════════════════════════
# PROMPT
# ═══════════════════════════════════════════════════════════════

def _prompt(data: Dict, language: str = 'en') -> str:
    return f"""{voice_card(language)}

You are reading the compatibility between two people across 5 astrological systems.

Here is all the calculated data:

═══ VEDIC ═══
{data['vedic']}

═══ KP ═══
{data['kp']}

═══ WESTERN ═══
{data['western']}

═══ CHINESE ═══
{data['chinese']}

═══ NUMEROLOGY ═══
{data['numerology']}

Return ONLY valid JSON in this exact shape:

{{
  "hook_title": "10-20 words — psychologically precise statement about these two together. Not generic romance.",
  "hook_body": "2-3 sentences — what draws them, what tests them. Specific to the charts.",
  "vedic":      {{ "info": "<museum-label, no 'you' — what Vedic synastry analyzes (Moon compatibility, ascendant overlay, manglik, dasha sync). 2-3 sentences.>", "score": 0-100, "one_line": "...", "reading": "3-4 sentences. The karma between them.", "deeper": "3-4 sentences. What will be hard.", "do": ["specific", "second", "third"], "dont": ["specific", "second", "third"] }},
  "kp":         {{ "info": "<museum-label about KP event-level compatibility — ruling planets, cuspal sub-lords, 7th/11th house fruitfulness. 2-3 sentences.>", "score": 0-100, "one_line": "...", "reading": "3-4 sentences. Event-level prediction.", "deeper": "3-4 sentences. Timing dimension.", "do": [...], "dont": [...] }},
  "western":    {{ "info": "<museum-label about Western synastry — aspects, element balance, planetary overlays. 2-3 sentences.>", "score": 0-100, "one_line": "...", "reading": "3-4 sentences. Psychological chemistry.", "deeper": "3-4 sentences. Shadow work — what each triggers.", "do": [...], "dont": [...] }},
  "chinese":    {{ "info": "<museum-label about BaZi compatibility — Day Master interaction, animals, element support/clash. 2-3 sentences.>", "score": 0-100, "one_line": "...", "reading": "3-4 sentences. Elemental dynamic.", "deeper": "3-4 sentences. Where Qi flows wrong.", "do": [...], "dont": [...] }},
  "numerology": {{ "info": "<museum-label about numerological compatibility — root/destiny chemistry, name vibration, Lo Shu grid. 2-3 sentences.>", "score": 0-100, "one_line": "...", "reading": "3-4 sentences. Vibrational match.", "deeper": "3-4 sentences. Where numbers clash.", "do": [...], "dont": [...] }},
  "closing": "1-2 sentences — the one thing all five lenses agree on about this pair."
}}

Rules:
- "info" fields are factual museum labels — NO "you", NO interpretations of THIS pair, just what the system analyzes generally
- "reading"/"deeper" are personal to this specific chart pair
- Scores are honest — 45% is valid
- Each system offers a DIFFERENT angle, not repetition
- "deeper" is hard truth, don't soften
- do/dont specific to THIS pair, not generic
- ~700 words total"""


# ═══════════════════════════════════════════════════════════════
# REQUESTS + EXTRACTORS
# ═══════════════════════════════════════════════════════════════

def _extract_person(data):
    """Pull birth+name+gender from a person dict. Extension of base extract_birth."""
    if not isinstance(data, dict) or not data:
        return None
    try:
        return {
            'year': int(data.get('year', 2000)),
            'month': int(data.get('month', 1)),
            'day': int(data.get('day', 1)),
            'hour': int(data.get('hour', 12)),
            'minute': int(data.get('minute', 0)),
            'lat': float(data.get('lat', data.get('latitude', 28.6))),
            'lng': float(data.get('lng', data.get('longitude', 77.2))),
            'name': data.get('name', '') or '',
            'gender': data.get('gender', '') or '',
        }
    except (TypeError, ValueError):
        return None


def _engine_for(p):
    from app.services.oracle.engine_cache import get_cached_engine
    e, _ = get_cached_engine(
        datetime(p['year'], p['month'], p['day'], p.get('hour', 12), p.get('minute', 0)),
        p['lat'], p['lng'],
    )
    return e


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

class _CompatRequest(BaseModel):
    person1: dict
    person2: dict
    language: Optional[str] = 'en'


@router.post('/compatibility-deep')
async def get_compatibility_deep(request_body: _CompatRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    p1 = _extract_person(request_body.person1)
    p2 = _extract_person(request_body.person2)
    if not p1 or not p2:
        raise HTTPException(status_code=400, detail='Both person1 and person2 required')

    try:
        e1 = _engine_for(p1)
        e2 = _engine_for(p2)

        data = _assemble(e1, e2, p1.get('name', ''), p2.get('name', ''))
        prompt = _prompt(data, request_body.language or 'en')

        raw = await call_llm(prompt, settings,
                             user_message='Read our compatibility across all five lenses.',
                             max_tokens=2500, temperature=0.75)
        reading = parse_json_or_text(raw)

        return {
            'reading': reading,
            'person1_color': data['color1'],
            'person2_color': data['color2'],
            'version': 2,
            'cache_ttl_seconds': 31536000,  # birth-data based, never changes
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


class _CompatHookReq(BaseModel):
    kundli_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/compatibility-hook')
async def get_compatibility_hook(request_body: _CompatHookReq, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    # Pull birth from the kundli_data payload
    kd = request_body.kundli_data or {}
    raw = kd.get('raw', {}) if isinstance(kd, dict) else {}
    birth = raw.get('birth_details', {}) if isinstance(raw, dict) else {}
    if not birth:
        birth = kd.get('birth_details', {}) if isinstance(kd, dict) else {}
    if not birth:
        return {'hook_title': '', 'hook_body': '', 'cta_dive': '', 'secret': '',
                'version': 2, 'cache_ttl_seconds': 0}

    try:
        p = {
            'year': int(birth.get('year', 2000)),
            'month': int(birth.get('month', 1)),
            'day': int(birth.get('day', 1)),
            'hour': int(birth.get('hour', 12)),
            'minute': int(birth.get('minute', 0)),
            'lat': float(birth.get('latitude', 28.6)),
            'lng': float(birth.get('longitude', 77.2)),
        }
        engine = _engine_for(p)

        venus = engine.planets.get('Venus', {}) if isinstance(engine.planets.get('Venus'), dict) else {}
        moon = engine.planets.get('Moon', {}) if isinstance(engine.planets.get('Moon'), dict) else {}
        sun = engine.planets.get('Sun', {}) if isinstance(engine.planets.get('Sun'), dict) else {}

        chart_hint = (
            f"Venus in {venus.get('rashi_name', '')} H{venus.get('house', '')}, "
            f"Moon in {moon.get('rashi_name', '')} H{moon.get('house', '')}, "
            f"Sun in {sun.get('rashi_name', '')} H{sun.get('house', '')}"
        )

        prompt = f"""{voice_card(request_body.language or 'en')}

This person's love signature: {chart_hint}

Return ONLY valid JSON in this exact shape:
{{
  "hook_title": "max 8 words. Persuasive. About THEIR relationship pattern.",
  "hook_body": "2 sentences. What they secretly want in love but won't say.",
  "cta_dive": "4-6 words. Make them curious about compatibility.",
  "secret": "ONE precise cryptic line about THEIR love pattern. Specific number, ratio, planetary position, or rare configuration. Style: factual not poetic. Max 12 words."
}}"""
        raw_text = await call_llm(prompt, settings,
                                  user_message='My love pattern.',
                                  max_tokens=300, temperature=0.85)
        parsed = parse_json_or_text(raw_text)

        return {
            'hook_title': parsed.get('hook_title', ''),
            'hook_body': parsed.get('hook_body', ''),
            'cta_dive': parsed.get('cta_dive', ''),
            'secret': parsed.get('secret', ''),
            'version': 2,
            'cache_ttl_seconds': 86400,
        }
    except HTTPException:
        raise
    except Exception:
        return {'hook_title': '', 'hook_body': '', 'cta_dive': '', 'secret': '',
                'version': 2, 'cache_ttl_seconds': 0}


compatibility_deep_router = router
