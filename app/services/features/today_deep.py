"""
TODAY DEEP — Full-depth today reading across ALL astrological systems.

Generates 7 days in parallel (today + 6 forward), each with a 5-system reading.

Endpoint: POST /api/public/today-deep
"""

import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, parse_json_or_text,
)


router = APIRouter(prefix="/public", tags=["Today Deep"])


WEEKDAY_LORDS = {
    0: ('Moon', 'Monday'), 1: ('Mars', 'Tuesday'), 2: ('Mercury', 'Wednesday'),
    3: ('Jupiter', 'Thursday'), 4: ('Venus', 'Friday'), 5: ('Saturn', 'Saturday'),
    6: ('Sun', 'Sunday'),
}


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


# ═══════════════════════════════════════════════════════════════
# SYSTEM DATA BUILDERS — facts only
# ═══════════════════════════════════════════════════════════════

def _build_vedic_data(engine_natal, engine_now, now) -> str:
    lines = []
    planets = engine_natal.planets if isinstance(getattr(engine_natal, 'planets', None), dict) else {}
    asc = engine_natal.ascendant if isinstance(getattr(engine_natal, 'ascendant', None), dict) else {}
    lines.append(f"Ascendant: {asc.get('rashi_name', '')}")

    natal_moon = _pl(planets, 'Moon')
    lines.append(f"Natal Moon: {natal_moon.get('rashi_name', '')} ({natal_moon.get('nakshatra_name', '')})")

    dasha = safe(engine_natal.get_vimshottari_dasha, {}) or {}
    if isinstance(dasha, dict):
        lines.append(f"Active Dasha: {dasha.get('dasha_string', 'unknown')}")
        maha = dasha.get('mahadasha', {}) or {}
        if isinstance(maha, dict) and maha.get('lord'):
            maha_planet = _pl(planets, maha['lord'])
            lines.append(f"Mahadasha lord {maha['lord']} sits in H{maha_planet.get('house', '?')} ({maha_planet.get('rashi_name', '?')})")

    panchanga = safe(engine_now.get_panchanga, {}) or {}
    if isinstance(panchanga, dict):
        tithi = panchanga.get('tithi', {}) or {}
        if isinstance(tithi, dict):
            lines.append(f"Tithi: {tithi.get('name', tithi.get('tithi_name', ''))} ({tithi.get('paksha', '')})")
        yoga = panchanga.get('yoga', {}) or {}
        if isinstance(yoga, dict):
            lines.append(f"Yoga: {yoga.get('name', yoga.get('yoga_name', ''))}")
        karana = panchanga.get('karana', {}) or {}
        if isinstance(karana, dict):
            lines.append(f"Karana: {karana.get('name', karana.get('karana_name', ''))}")

    day_lord, day_name = WEEKDAY_LORDS.get(now.weekday(), ('', ''))
    natal_dl = _pl(planets, day_lord)
    lines.append(f"Day lord: {day_lord} ({day_name}), in chart at H{natal_dl.get('house', '?')}-{natal_dl.get('rashi_name', '?')}")

    transits = safe(engine_now.get_current_transits, {}) or {}
    if not isinstance(transits, dict):
        transits = {}
    if transits:
        t_moon = transits.get('Moon', {}) if isinstance(transits.get('Moon'), dict) else {}
        if t_moon:
            lines.append(f"Moon transiting: {t_moon.get('rashi_name', '')} ({t_moon.get('nakshatra_name', '')})")
        t_sun = transits.get('Sun', {}) if isinstance(transits.get('Sun'), dict) else {}
        if t_sun:
            lines.append(f"Sun transiting: {t_sun.get('rashi_name', '')}")
        retro = [p for p, d in transits.items() if isinstance(d, dict) and (d.get('retrograde') or d.get('is_retrograde'))]
        if retro:
            lines.append(f"Retrograde: {', '.join(retro)}")
        summary = []
        for p in ('Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'):
            td = transits.get(p, {})
            if isinstance(td, dict) and td.get('rashi_name'):
                summary.append(f"{p} in {td['rashi_name']}")
        if summary:
            lines.append(f"Transits: {', '.join(summary)}")

    natal_summary = []
    for p in ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'):
        pd = _pl(planets, p)
        if pd.get('house'):
            natal_summary.append(f"{p}:H{pd['house']}-{pd.get('rashi_name', '?')}")
    if natal_summary:
        lines.append(f"Natal: {', '.join(natal_summary)}")

    muhurta = safe(engine_now.get_muhurta, {}) or {}
    if isinstance(muhurta, dict):
        inaus = muhurta.get('inauspicious', {}) or {}
        if isinstance(inaus, dict) and inaus.get('rahu_kalam'):
            lines.append(f"Rahu Kalam: {inaus['rahu_kalam']}")

    yogas = safe(engine_natal.get_yogas, {}) or {}
    if isinstance(yogas, dict):
        highlights = yogas.get('highlights', [])
        top = [y.get('name', '') for y in highlights[:3] if isinstance(y, dict) and y.get('name')]
        if top:
            lines.append(f"Key yogas: {', '.join(top)}")

    return '\n'.join(lines)


def _build_kp_data(engine_natal, engine_now, now) -> str:
    lines = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp = KPComplete(engine_natal)
        rp = kp.get_ruling_planets(query_time=now)
        if isinstance(rp, dict):
            for key in ('day_lord', 'moon_sign_lord', 'moon_star_lord', 'moon_sub_lord', 'ascendant_sign_lord', 'ascendant_star_lord'):
                if rp.get(key):
                    lines.append(f"{key.replace('_', ' ').title()}: {rp[key]}")
            rp_list = rp.get('common_rp', rp.get('ruling_planets', []))
            if isinstance(rp_list, list) and rp_list:
                lines.append(f"Ruling planets: {', '.join(rp_list)}")
        for h in (1, 2, 7, 10, 11):
            try:
                fruit = kp.check_fruitfulness(house=h)
                if isinstance(fruit, dict) and fruit.get('verdict'):
                    lines.append(f"H{h} ({fruit.get('cuspal_sub_lord', '')}): {fruit['verdict']}")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"KP data limited: {str(e)[:60]}")
    return '\n'.join(lines) if lines else 'KP data unavailable.'


def _build_western_data(engine_natal, now) -> str:
    lines = []
    try:
        from app.services.western.chart import WesternChart
        wc = WesternChart(engine_natal.birth_dt, engine_natal.latitude, engine_natal.longitude)
        big3 = safe(wc.get_big_three, {}) or {}
        if isinstance(big3, dict):
            lines.append(f"Sun: {big3.get('sun_sign', '')} | Moon: {big3.get('moon_sign', '')} | Rising: {big3.get('rising_sign', '')}")
        aspects = safe(wc.get_aspects, []) or []
        if isinstance(aspects, list):
            tight = [a for a in aspects if isinstance(a, dict) and abs(a.get('orb', 99)) < 3]
            for a in tight[:6]:
                lines.append(f"{a.get('planet1', '')} {a.get('aspect_name', '')} {a.get('planet2', '')} (orb {a.get('orb', 0):.1f}°)")
        eb = safe(wc.get_element_balance, {}) or {}
        if isinstance(eb, dict):
            lines.append(f"Elements — Fire:{eb.get('fire',0)} Earth:{eb.get('earth',0)} Air:{eb.get('air',0)} Water:{eb.get('water',0)}")
            dom = max(eb.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
            lines.append(f"Dominant element: {dom[0]}")
        ct = safe(wc.get_current_transits, []) or []
        if isinstance(ct, list):
            for t in ct[:5]:
                if isinstance(t, dict):
                    lines.append(f"Transit {t.get('transit_planet', '')} {t.get('aspect', '')} natal {t.get('natal_planet', '')}")
    except Exception as e:
        lines.append(f"Western data limited: {str(e)[:60]}")

    # Moon phase
    try:
        transits = safe(lambda: engine_natal.get_current_transits() if hasattr(engine_natal, 'get_current_transits') else {}, {}) or {}
        if isinstance(transits, dict):
            sun_long = transits.get('Sun', {}).get('longitude', 0)
            moon_long = transits.get('Moon', {}).get('longitude', 0)
            diff = (moon_long - sun_long) % 360
            phases = [(22.5, 'New Moon'), (67.5, 'Waxing Crescent'), (112.5, 'First Quarter'),
                      (157.5, 'Waxing Gibbous'), (202.5, 'Full Moon'), (247.5, 'Waning Gibbous'),
                      (292.5, 'Last Quarter'), (360, 'Waning Crescent')]
            phase = next((p for d, p in phases if diff < d), 'Waning Crescent')
            lines.append(f"Moon phase: {phase}")
    except Exception:
        pass

    return '\n'.join(lines) if lines else 'Western data limited.'


def _build_chinese_data(engine_natal, now) -> str:
    lines = []
    try:
        from app.services.chinese.bazi import BaZiChart
        b_natal = BaZiChart(engine_natal.birth_dt)
        dm = b_natal.get_day_master() or {}
        if isinstance(dm, dict):
            lines.append(f"Day Master: {dm.get('stem', '')} {dm.get('element', '')} ({dm.get('yin_yang', '')})")

        bal_natal = b_natal.get_element_balance() or {}
        if isinstance(bal_natal, dict):
            lines.append(f"Dominant element: {bal_natal.get('day_master_element', '')}")
            elements = bal_natal.get('elements', {})
            if isinstance(elements, dict):
                lines.append(f"Birth balance: {', '.join(f'{k}:{v}' for k, v in elements.items() if isinstance(v, (int, float)))}")

        b_today = BaZiChart(now)
        pillars = b_today.get_four_pillars() or {}
        if isinstance(pillars, dict):
            day_p = pillars.get('day', {})
            if isinstance(day_p, dict):
                lines.append(f"Today's stem: {day_p.get('stem', '')} ({day_p.get('element', '')})")
                lines.append(f"Today's branch: {day_p.get('branch', '')} ({day_p.get('animal', '')})")
        today_dm = b_today.get_day_master() or {}
        if isinstance(today_dm, dict) and isinstance(dm, dict):
            lines.append(f"Today's element ({today_dm.get('element', '')}) vs yours ({dm.get('element', '')})")
        animal = b_today.get_animal_sign() or {}
        if isinstance(animal, dict):
            lines.append(f"Today's animal: {animal.get('animal', '')} ({animal.get('element', '')})")
    except Exception as e:
        lines.append(f"Chinese data limited: {str(e)[:60]}")
    return '\n'.join(lines) if lines else 'Chinese data limited.'


def _build_numerology_data(engine_natal, now) -> str:
    lines = []
    try:
        from app.services.numerology.core import NumerologyEngine
        bd = engine_natal.birth_dt.date() if hasattr(engine_natal.birth_dt, 'date') else date.today()
        nc = NumerologyEngine(name='', birth_date=bd)

        m = nc.get_mulank() or {}
        if isinstance(m, dict):
            lines.append(f"Mulank (Root): {m.get('number', '')} ({m.get('planet', '')})")
        b = nc.get_bhagyank() or {}
        if isinstance(b, dict):
            lines.append(f"Bhagyank (Destiny): {b.get('number', '')} ({b.get('planet', '')})")
        py = nc.get_personal_year() or {}
        if isinstance(py, dict):
            lines.append(f"Personal Year: {py.get('number', '')}")
        pm = nc.get_personal_month() or {}
        if isinstance(pm, dict):
            lines.append(f"Personal Month: {pm.get('number', '')}")
        pd = nc.get_personal_day(target_date=now.date() if hasattr(now, 'date') else now) or {}
        if isinstance(pd, dict):
            lines.append(f"Personal Day: {pd.get('number', '')}")

        today = now if isinstance(now, date) else now.date()
        u_day = sum(int(d) for d in str(today.year) + str(today.month).zfill(2) + str(today.day).zfill(2))
        while u_day > 9 and u_day not in (11, 22, 33):
            u_day = sum(int(d) for d in str(u_day))
        lines.append(f"Universal Day: {u_day}")
    except Exception as e:
        lines.append(f"Numerology data limited: {str(e)[:60]}")
    return '\n'.join(lines) if lines else 'Numerology data limited.'


def _assemble_day(engine_natal, birth_data, target_date) -> Dict:
    lat = birth_data.get('lat', birth_data.get('latitude', 25.35))
    lng = birth_data.get('lng', birth_data.get('longitude', 74.64))
    try:
        from app.services.jyotish_engine import JyotishEngine
        engine_day = JyotishEngine(target_date, lat, lng)
    except Exception:
        engine_day = engine_natal
    return {
        'briefing': f"""DATE: {target_date.strftime('%A, %B %d, %Y')}

VEDIC:
{_build_vedic_data(engine_natal, engine_day, target_date)}

KP:
{_build_kp_data(engine_natal, engine_day, target_date)}

WESTERN:
{_build_western_data(engine_natal, target_date)}

CHINESE:
{_build_chinese_data(engine_natal, target_date)}

NUMEROLOGY:
{_build_numerology_data(engine_natal, target_date)}""",
        'date': target_date.strftime('%A, %B %d, %Y'),
    }


def _prompt_single_day(data: Dict, language: str = 'en') -> str:
    return f"""{voice_card(language)}

This is a DAILY READING. The person opens this every day.

Data:
{data['briefing']}

Return ONLY valid JSON:
{{
  "hook_title": "max 8 words. Punch. Persuasive. Stop them mid-scroll.",
  "hook_body": "2 sentences. What they feel today but won't say.",
  "cta_dive": "4-6 words. Curiosity.",
  "secret": "ONE precise cryptic line about THIS person for TODAY. Use a specific number, date count, planet placement, dasha day, or rare configuration. Style: factual not poetic. Max 10 words.",
  "daily_word": {{
    "devanagari": "single Sanskrit word in Devanagari script that captures the energy of THIS day for THIS person",
    "romanized": "the same word in roman letters, lowercase",
    "meaning": "1-3 word English translation"
  }},
  "vedic":      {{ "headline": "3-5 words", "reading": "3-4 sentences", "deeper": "3-4 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words to next system" }},
  "kp":         {{ "headline": "3-5 words", "reading": "3-4 sentences", "deeper": "3-4 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "western":    {{ "headline": "3-5 words", "reading": "3-4 sentences", "deeper": "3-4 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "chinese":    {{ "headline": "3-5 words", "reading": "3-4 sentences", "deeper": "3-4 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "cta_next": "5-8 words" }},
  "numerology": {{ "headline": "3-5 words", "reading": "3-4 sentences", "deeper": "3-4 sentences", "do": ["if needed"], "dont": ["if needed"], "cta_deeper": "4-6 words", "cta_verdict": "4-6 words", "closing": "1 sentence. All five unified." }}
}}

~800 words total. Headlines SHORT and punchy. Do/dont only when genuinely needed."""


class _TodayDeepRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


async def _fetch_one_day(engine_natal, birth_data, target_date, language, settings) -> Optional[dict]:
    data = _assemble_day(engine_natal, birth_data, target_date)
    prompt = _prompt_single_day(data, language)
    try:
        raw = await call_llm(prompt, settings,
                             user_message='Read this day.',
                             max_tokens=2500, temperature=0.8)
        return parse_json_or_text(raw)
    except Exception:
        return None


@router.post('/today-deep')
async def get_today_deep(request_body: _TodayDeepRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'
        now = datetime.now()
        targets = [now + timedelta(days=i) for i in range(7)]

        tasks = [_fetch_one_day(engine, birth_data, t, language, settings) for t in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        days = {}
        for i, t in enumerate(targets):
            dk = t.strftime('%Y-%m-%d')
            r = results[i]
            if isinstance(r, dict) and 'text' not in r:
                days[dk] = r
            else:
                days[dk] = {'error': str(r)[:120] if isinstance(r, Exception) else 'parse_failed'}

        return {
            'date': now.strftime('%Y-%m-%d'),
            'days': days,
            'version': 2,
            'cache_ttl_seconds': 21600,  # 6 hours — moon transits shift
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


today_deep_router = router
