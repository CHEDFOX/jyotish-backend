"""
COMPATIBILITY DEEP — General compatibility across all 5 systems.

Takes two birth data sets. Runs every compatibility engine.
Returns structured data + LLM narrative + dominant color per person.

Separate from Ashtakoota (which will be built independently).

Usage in main.py:
    from app.services.features.compatibility_deep import compatibility_deep_router
    app.include_router(compatibility_deep_router, prefix="/api")
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, date
import httpx

router = APIRouter(prefix="/public", tags=["Compatibility"])

ELEMENT_COLORS = {
    'fire': '#E8A040', 'Fire': '#E8A040',
    'earth': '#8B7355', 'Earth': '#8B7355',
    'air': '#7EB8D0', 'Air': '#7EB8D0',
    'water': '#4A9E9E', 'Water': '#4A9E9E',
    'metal': '#A8B0B8', 'Metal': '#A8B0B8',
    'wood': '#4A8C5C', 'Wood': '#4A8C5C',
    'ether': '#B8A0D0', 'Ether': '#B8A0D0',
}

def _safe(fn, default=None):
    try:
        r = fn()
        return r if r is not None else default
    except Exception:
        return default


def _dominant_element_vedic(engine) -> str:
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    counts = {'fire': 0, 'earth': 0, 'air': 0, 'water': 0}
    SIGN_ELEMENTS = {
        'Aries': 'fire', 'Leo': 'fire', 'Sagittarius': 'fire',
        'Taurus': 'earth', 'Virgo': 'earth', 'Capricorn': 'earth',
        'Gemini': 'air', 'Libra': 'air', 'Aquarius': 'air',
        'Cancer': 'water', 'Scorpio': 'water', 'Pisces': 'water',
    }
    for p in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']:
        pd = planets.get(p, {})
        if isinstance(pd, dict):
            sign = pd.get('rashi_name', '')
            elem = SIGN_ELEMENTS.get(sign, '')
            if elem:
                weight = 2 if p in ('Sun', 'Moon') else 1
                counts[elem] = counts.get(elem, 0) + weight
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
    vedic_elem = _dominant_element_vedic(engine)
    chinese_elem = _dominant_element_chinese(engine)
    # Prefer Chinese element for color (more granular: 5 vs 4)
    return ELEMENT_COLORS.get(chinese_elem, ELEMENT_COLORS.get(vedic_elem, '#E8A040'))


# ═══════════════════════════════════════════════════════════════
# DATA BUILDERS
# ═══════════════════════════════════════════════════════════════

def _vedic_compat(engine1, engine2) -> str:
    lines = []
    try:
        from app.services.compatibility.synastry import analyze_synastry
        syn = analyze_synastry(engine1, engine2)
        if isinstance(syn, dict):
            moon = syn.get('moon_compatibility', {})
            if isinstance(moon, dict):
                lines.append(f"Moon compat: {moon.get('score', '?')}/10 — {moon.get('description', '')[:80]}")
            asc = syn.get('ascendant_compatibility', {})
            if isinstance(asc, dict):
                lines.append(f"Ascendant compat: {asc.get('compatibility', '')[:80]}")
            overlays = syn.get('planet_overlays', [])
            if isinstance(overlays, list):
                for o in overlays[:4]:
                    if isinstance(o, dict):
                        h = o.get('falls_in_house', ''); eff = o.get('impact', '')
                        if h and eff:
                            lines.append(f"{o.get('planet', '')} in H{h} — {eff[:60]}")
            dasha = syn.get('dasha_sync', {})
            if isinstance(dasha, dict) and dasha.get('assessment'):
                lines.append(f"Dasha sync: {dasha['assessment'][:80]}")
    except Exception as e:
        lines.append(f"Vedic compat limited: {str(e)[:50]}")

    # Manglik
    try:
        from app.services.compatibility.manglik import ManglikAnalysis
        m1 = ManglikAnalysis(engine1, engine1.ascendant_rashi)
        m2 = ManglikAnalysis(engine2, engine2.ascendant_rashi)
        r1 = m1.check_manglik()
        r2 = m2.check_manglik()
        if isinstance(r1, dict) and isinstance(r2, dict):
            lines.append(f"Person 1 Manglik: {'Yes' if r1.get('is_manglik') else 'No'} | Person 2: {'Yes' if r2.get('is_manglik') else 'No'}")
    except Exception:
        pass

    return '\n'.join(lines) if lines else 'Vedic compatibility data limited.'


def _kp_compat(engine1, engine2) -> str:
    lines = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp1 = KPComplete(engine1)
        kp2 = KPComplete(engine2)

        rp1 = kp1.get_ruling_planets()
        rp2 = kp2.get_ruling_planets()
        if isinstance(rp1, dict) and isinstance(rp2, dict):
            list1 = set(rp1.get('common_rp', rp1.get('ruling_planets', [])))
            list2 = set(rp2.get('common_rp', rp2.get('ruling_planets', [])))
            common = list1 & list2
            lines.append(f"Person 1 RP: {', '.join(list1) if list1 else 'unknown'}")
            lines.append(f"Person 2 RP: {', '.join(list2) if list2 else 'unknown'}")
            lines.append(f"Common RP: {', '.join(common) if common else 'None'} ({len(common)}/{max(len(list1),1)} overlap)")

        for h in [7, 11]:
            try:
                f1 = kp1.check_fruitfulness(house=h)
                f2 = kp2.check_fruitfulness(house=h)
                if isinstance(f1, dict) and isinstance(f2, dict):
                    lines.append(f"H{h} — P1: {f1.get('verdict', '?')} | P2: {f2.get('verdict', '?')}")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"KP compat limited: {str(e)[:50]}")
    return '\n'.join(lines) if lines else 'KP compatibility data limited.'


def _western_compat(engine1, engine2) -> str:
    lines = []
    try:
        from app.services.western.chart import WesternChart
        from app.services.western.compatibility import WesternCompatibility
        wc1 = WesternChart(engine1.birth_dt, engine1.latitude, engine1.longitude)
        wc2 = WesternChart(engine2.birth_dt, engine2.latitude, engine2.longitude)
        wcompat = WesternCompatibility(wc1, wc2)
        # Full synastry report — contains everything
        report = wcompat.generate_synastry_report()
        if isinstance(report, dict):
            # Profiles
            for label, key in [("P1","person1"),("P2","person2")]:
                p = report.get(key, {})
                if isinstance(p, dict):
                    lines.append(f"{label}: Sun {p.get('sun_sign','')}, Moon {p.get('moon_sign','')}, Rising {p.get('rising_sign','')}, Ruler {p.get('chart_ruler','')} in H{p.get('chart_ruler_house','')}, MC {p.get('midheaven_sign','')}")
            # Element balance
            for label, wc in [("P1",wc1),("P2",wc2)]:
                eb = wc.get_element_balance()
                if isinstance(eb, dict):
                    elems = eb.get('elements', {})
                    lines.append(f"{label} elements: {', '.join(f'{k}:{v}' for k,v in elems.items() if isinstance(v,(int,float)))} | dominant {eb.get('dominant_element','')} | weak {eb.get('weak_element','')}")
            # All synastry aspects — the actual relationship data
            aspects = report.get('aspects', [])
            if isinstance(aspects, list):
                lines.append(f"Total synastry aspects: {len(aspects)}")
                for a in aspects[:12]:
                    if isinstance(a, dict):
                        lines.append(f"  {a.get('person1_planet','')} {a.get('aspect','')} {a.get('person2_planet','')} — {a.get('nature','')} (orb {a.get('orb',0):.1f}, strength {a.get('strength',0):.2f}) — {a.get('interpretation','')}")
        # Compatibility score
        score = wcompat.get_compatibility_score()
        if isinstance(score, dict):
            lines.append(f"Compatibility: {score.get('score','')}% — {score.get('verdict','')}")
            lines.append(f"Harmonious: {score.get('harmonious',0)} | Challenging: {score.get('challenging',0)}")
            for ka in score.get('key_aspects', [])[:4]:
                if isinstance(ka, dict):
                    lines.append(f"  KEY: {ka.get('person1_planet','')} {ka.get('aspect','')} {ka.get('person2_planet','')} — {ka.get('interpretation','')}")
    except Exception as e:
        lines.append(f"Western error: {str(e)[:80]}")
    return '\n'.join(lines) if lines else 'Western data unavailable.'

def _chinese_compat(engine1, engine2) -> str:
    lines = []
    try:
        from app.services.chinese.bazi import BaZiChart
        b1 = BaZiChart(engine1.birth_dt)
        b2 = BaZiChart(engine2.birth_dt)

        dm1 = b1.get_day_master()
        dm2 = b2.get_day_master()
        if isinstance(dm1, dict) and isinstance(dm2, dict):
            yy1 = dm1.get('polarity', '') or ''; lines.append(f"P1 Day Master: {dm1.get('element', '')}{(' ('+yy1+')') if yy1 else ''}")
            yy2 = dm2.get('polarity', '') or ''; lines.append(f"P2 Day Master: {dm2.get('element', '')}{(' ('+yy2+')') if yy2 else ''}")

        a1 = b1.get_animal_sign()
        a2 = b2.get_animal_sign()
        if isinstance(a1, dict) and isinstance(a2, dict):
            lines.append(f"P1 Animal: {a1.get('animal', a1.get('branch',{}).get('animal',''))} | P2 Animal: {a2.get('animal', a2.get('branch',{}).get('animal',''))}")

        bal1 = b1.get_element_balance()
        bal2 = b2.get_element_balance()
        if isinstance(bal1, dict) and isinstance(bal2, dict):
            e1 = bal1.get('counts', {})
            e2 = bal2.get('counts', {})
            lines.append(f"P1 elements: {', '.join(f'{k}:{v}' for k,v in e1.items() if isinstance(v,(int,float)))}")
            lines.append(f"P2 elements: {', '.join(f'{k}:{v}' for k,v in e2.items() if isinstance(v,(int,float)))}")
    except Exception as e:
        lines.append(f"Chinese compat limited: {str(e)[:50]}")

    try:
        compat = engine1.get_chinese_compatibility(engine2)
        if isinstance(compat, dict):
            for k, v in compat.items():
                if isinstance(v, str):
                    lines.append(f"{k}: {v[:80]}")
                elif isinstance(v, (int, float)):
                    lines.append(f"{k}: {v}")
    except Exception:
        pass

    return '\n'.join(lines) if lines else 'Chinese compatibility data limited.'


def _numerology_compat(engine1, engine2, name1='', name2='') -> str:
    lines = []
    try:
        from app.services.numerology.core import NumerologyEngine, check_number_compatibility
        from datetime import date
        bd1 = engine1.birth_dt.date() if hasattr(engine1.birth_dt, 'date') else date.today()
        bd2 = engine2.birth_dt.date() if hasattr(engine2.birth_dt, 'date') else date.today()
        nc1 = NumerologyEngine(name=name1, birth_date=bd1)
        nc2 = NumerologyEngine(name=name2, birth_date=bd2)
        # Individual numbers with meanings
        for label, nc, nm in [("P1",nc1,name1),("P2",nc2,name2)]:
            m = nc.get_mulank()
            b = nc.get_bhagyank()
            if isinstance(m, dict):
                meaning = str(m.get('meaning','') or m.get('description','') or '')
                lines.append(f"{label} Root number: {m.get('number','')} ruled by {m.get('planet','')} — {meaning[:80]}")
            if isinstance(b, dict):
                meaning = str(b.get('meaning','') or b.get('description','') or '')
                lines.append(f"{label} Destiny number: {b.get('number','')} ruled by {b.get('planet','')} — {meaning[:80]}")
            if nm:
                n = nc.get_namank()
                if isinstance(n, dict):
                    ch = n.get('chaldean', {})
                    lines.append(f"{label} Name number: {ch.get('root','')} ({ch.get('compound_name','')}) — {str(ch.get('compound_meaning',''))[:80]} [{nm}]")
        # The actual relationship compatibility
        try:
            compat = check_number_compatibility(bd1, bd2)
            if isinstance(compat, dict):
                lines.append(f"Compatibility score: {compat.get('score','')}%")
                lines.append(f"Verdict: {compat.get('verdict','')}")
                lines.append(f"Root numbers match: {'Yes' if compat.get('mulank_match') else 'No'}")
                lines.append(f"Destiny numbers match: {'Yes' if compat.get('bhagyank_match') else 'No'}")
        except Exception:
            pass
        # Cross compatibility — how P1 relates to P2
        try:
            c12 = nc1.check_compatibility(bd2)
            if isinstance(c12, dict):
                for k, v in c12.items():
                    if k not in ('person1','person2') and v:
                        lines.append(f"Cross: {k} = {v}")
        except Exception:
            pass
        # Lo Shu comparison — what each person has and lacks
        for label, nc in [("P1",nc1),("P2",nc2)]:
            try:
                grid = nc.get_lo_shu_grid()
                if isinstance(grid, dict):
                    missing = grid.get('missing_numbers', [])
                    arrows = grid.get('complete_arrows', [])
                    if missing:
                        lines.append(f"{label} missing numbers: {missing}")
                    if arrows:
                        lines.append(f"{label} complete arrows: {arrows}")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"Numerology error: {str(e)[:80]}")
    return '\n'.join(lines) if lines else 'Numerology data unavailable.'

def _assemble(engine1, engine2, name1='', name2='') -> Dict:
    return {
        'vedic': _vedic_compat(engine1, engine2),
        'kp': _kp_compat(engine1, engine2),
        'western': _western_compat(engine1, engine2),
        'chinese': _chinese_compat(engine1, engine2),
        'numerology': _numerology_compat(engine1, engine2, name1, name2),
        'color1': _get_dominant_color(engine1),
        'color2': _get_dominant_color(engine2),
    }


def _prompt(data: Dict, language: str = 'en') -> str:
    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nIMPORTANT: Write everything in {language}.'

    return f"""You are the Oracle — warm, psychologically sharp, deeply personal.
You are reading the compatibility between two people across 5 astrological systems.{lang_note}

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

Return ONLY valid JSON (no markdown, no backticks):

{{
  "hook_title": "10-20 word statement about these two people together. Psychologically precise. Not generic romance. The uncomfortable truth about why they work or don't.",
  "hook_body": "2-3 sentences. What draws them together and what will test them. Specific to the charts.",
  "vedic": {{
    "score": 0-100,
    "one_line": "One sentence — the Vedic verdict on this bond.",
    "reading": "3-4 sentences. Moon compatibility, synastry overlays, manglik, dasha sync. What the karma says.",
    "deeper": "3-4 sentences. The uncomfortable part. What will be hard. What requires conscious effort.",
    "do": ["specific action for this pair", "second", "third"],
    "dont": ["specific avoidance", "second", "third"]
  }},
  "kp": {{
    "score": 0-100,
    "one_line": "One sentence — KP's event-level prediction for this pair.",
    "reading": "3-4 sentences. Ruling planet overlap, 7th house promises. Will this partnership produce results?",
    "deeper": "3-4 sentences. The timing dimension. When this works best. When it gets rocky.",
    "do": ["action", "second", "third"],
    "dont": ["avoidance", "second", "third"]
  }},
  "western": {{
    "score": 0-100,
    "one_line": "One sentence — the psychological truth.",
    "reading": "3-4 sentences. Synastry aspects, element balance, emotional/intellectual/physical chemistry.",
    "deeper": "3-4 sentences. The shadow work. What each person triggers in the other.",
    "do": ["action", "second", "third"],
    "dont": ["avoidance", "second", "third"]
  }},
  "chinese": {{
    "score": 0-100,
    "one_line": "One sentence — the elemental dynamic.",
    "reading": "3-4 sentences. Day Master interaction, animal signs, element support/clash.",
    "deeper": "3-4 sentences. What happens when the Qi flows wrong between them.",
    "do": ["action", "second", "third"],
    "dont": ["avoidance", "second", "third"]
  }},
  "numerology": {{
    "score": 0-100,
    "one_line": "One sentence — the vibrational match.",
    "reading": "3-4 sentences. Root number chemistry, destiny alignment, name vibration.",
    "deeper": "3-4 sentences. Where the numbers clash. What frequency adjustment is needed.",
    "do": ["action", "second", "third"],
    "dont": ["avoidance", "second", "third"],
    "closing": "1-2 sentences tying all five systems together. The one thing all lenses agree on about this pair."
  }}
}}

Rules:
- Scores must be honest, not flattering. 45% is a valid score.
- Each system offers a DIFFERENT ANGLE — not repetition.
- "deeper" sections are the hard truths. Don't soften them.
- Do/dont must be specific to THIS pair, not generic relationship advice.
- ~600 words total."""


# ═══════════════════════════════════════════════════════════════
# ENDPOINT
# ═══════════════════════════════════════════════════════════════

class _CompatRequest(BaseModel):
    person1: dict
    person2: dict
    language: Optional[str] = 'en'


def _extract_person(data):
    if not data:
        return None
    try:
        return {
            'year': int(data.get('year', 2000)), 'month': int(data.get('month', 1)),
            'day': int(data.get('day', 1)), 'hour': int(data.get('hour', 12)),
            'minute': int(data.get('minute', 0)),
            'lat': float(data.get('lat', data.get('latitude', 28.6))),
            'lng': float(data.get('lng', data.get('longitude', 77.2))),
            'name': data.get('name', ''),
            'gender': data.get('gender', ''),
        }
    except (TypeError, ValueError):
        return None


@router.post("/compatibility-deep")
async def get_compatibility_deep(request_body: _CompatRequest, request: Request):
    """General compatibility across all 5 systems."""
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    p1 = _extract_person(request_body.person1)
    p2 = _extract_person(request_body.person2)
    if not p1 or not p2:
        raise HTTPException(status_code=400, detail="Both person1 and person2 required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        import json as json_parse

        e1, _ = get_cached_engine(
            datetime(p1['year'], p1['month'], p1['day'], p1.get('hour', 12), p1.get('minute', 0)),
            p1['lat'], p1['lng']
        )
        e2, _ = get_cached_engine(
            datetime(p2['year'], p2['month'], p2['day'], p2.get('hour', 12), p2.get('minute', 0)),
            p2['lat'], p2['lng']
        )

        data = _assemble(e1, e2, p1.get('name', ''), p2.get('name', ''))
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
                        {"role": "user", "content": "Read our compatibility across all five lenses."},
                    ],
                    "max_tokens": 2200,
                    "temperature": 0.75,
                },
                timeout=90.0,
            )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="AI service unavailable")

        raw_text = response.json()["choices"][0]["message"]["content"].strip()
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            reading = json_parse.loads(cleaned)
        except json_parse.JSONDecodeError:
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start >= 0 and end > start:
                try:
                    reading = json_parse.loads(cleaned[start:end + 1])
                except json_parse.JSONDecodeError:
                    reading = {"error": "parse_failed", "raw": raw_text}
            else:
                reading = {"error": "no_json", "raw": raw_text}

        return {
            'reading': reading,
            'person1_color': data['color1'],
            'person2_color': data['color2'],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Compatibility error: {str(e)[:200]}")


compatibility_deep_router = router
