"""
TODAY DEEP — Full-depth today reading across ALL astrological systems.

One file. One import. Drop in and go.

Usage in main.py:
    from app.services.features.today_deep import today_deep_router
    app.include_router(today_deep_router, prefix="/api")

Systems: Vedic (BPHS) → KP → Western → Chinese → Numerology
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from typing import Dict
import httpx

router = APIRouter(prefix="/public", tags=["Today Deep"])


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

WEEKDAY_LORDS = {
    0: ('Moon', 'Monday'),
    1: ('Mars', 'Tuesday'),
    2: ('Mercury', 'Wednesday'),
    3: ('Jupiter', 'Thursday'),
    4: ('Venus', 'Friday'),
    5: ('Saturn', 'Saturday'),
    6: ('Sun', 'Sunday'),
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


# ═══════════════════════════════════════════════════════════════
# SYSTEM DATA BUILDERS
# ═══════════════════════════════════════════════════════════════

def _build_vedic_data(engine_natal, engine_now, now) -> str:
    lines = []
    planets = engine_natal.planets if isinstance(getattr(engine_natal, 'planets', None), dict) else {}

    asc = engine_natal.ascendant if isinstance(getattr(engine_natal, 'ascendant', None), dict) else {}
    lines.append(f"Ascendant: {asc.get('rashi_name', '')}")

    natal_moon = _pl(planets, 'Moon')
    lines.append(f"Natal Moon: {natal_moon.get('rashi_name', '')} ({natal_moon.get('nakshatra_name', '')})")

    dasha = _safe(engine_natal.get_vimshottari_dasha, {})
    if isinstance(dasha, dict):
        lines.append(f"Active Dasha: {dasha.get('dasha_string', 'unknown')}")
        maha = dasha.get('mahadasha', {})
        if isinstance(maha, dict) and maha.get('lord'):
            maha_planet = _pl(planets, maha['lord'])
            lines.append(f"Mahadasha lord {maha['lord']} sits in H{maha_planet.get('house', '?')} ({maha_planet.get('rashi_name', '?')})")

    panchanga = _safe(engine_now.get_panchanga, {})
    if isinstance(panchanga, dict):
        tithi = panchanga.get('tithi', {})
        if isinstance(tithi, dict):
            lines.append(f"Tithi: {tithi.get('name', tithi.get('tithi_name', ''))} ({tithi.get('paksha', '')})")
        yoga = panchanga.get('yoga', {})
        if isinstance(yoga, dict):
            lines.append(f"Yoga: {yoga.get('name', yoga.get('yoga_name', ''))}")
        karana = panchanga.get('karana', {})
        if isinstance(karana, dict):
            lines.append(f"Karana: {karana.get('name', karana.get('karana_name', ''))}")

    day_idx = now.weekday()
    day_lord, day_name = WEEKDAY_LORDS.get(day_idx, ('', ''))
    natal_dl = _pl(planets, day_lord)
    lines.append(f"Day lord: {day_lord} ({day_name}), in your chart at H{natal_dl.get('house', '?')}-{natal_dl.get('rashi_name', '?')}")

    transits = _safe(engine_now.get_current_transits, {})
    if not isinstance(transits, dict):
        transits = _safe(lambda: engine_now.ephemeris.get_current_transits() if hasattr(engine_now, 'ephemeris') else {}, {})
    if isinstance(transits, dict):
        t_moon = transits.get('Moon', {})
        if isinstance(t_moon, dict):
            lines.append(f"Moon transiting: {t_moon.get('rashi_name', '')} ({t_moon.get('nakshatra_name', '')})")
        t_sun = transits.get('Sun', {})
        if isinstance(t_sun, dict):
            lines.append(f"Sun transiting: {t_sun.get('rashi_name', '')}")
        retro = [p for p, d in transits.items() if isinstance(d, dict) and (d.get('retrograde') or d.get('is_retrograde'))]
        if retro:
            lines.append(f"Retrograde: {', '.join(retro)}")
        summary = []
        for p in ['Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']:
            td = transits.get(p, {})
            if isinstance(td, dict) and td.get('rashi_name'):
                summary.append(f"{p} in {td['rashi_name']}")
        if summary:
            lines.append(f"Transits: {', '.join(summary)}")

    natal_summary = []
    for p in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']:
        pd = _pl(planets, p)
        if pd.get('house'):
            natal_summary.append(f"{p}:H{pd['house']}-{pd.get('rashi_name', '?')}")
    if natal_summary:
        lines.append(f"Natal: {', '.join(natal_summary)}")

    muhurta = _safe(engine_now.get_muhurta, {})
    if isinstance(muhurta, dict):
        inaus = muhurta.get('inauspicious', {})
        if isinstance(inaus, dict):
            rk = inaus.get('rahu_kalam', '')
            if rk:
                lines.append(f"Rahu Kalam: {rk}")

    yogas = _safe(engine_natal.get_yogas, {})
    if isinstance(yogas, dict):
        highlights = yogas.get('highlights', [])
        top_yogas = [y.get('name', '') for y in highlights[:3] if isinstance(y, dict) and y.get('name')]
        if top_yogas:
            lines.append(f"Key yogas: {', '.join(top_yogas)}")

    return '\n'.join(lines)


def _build_kp_data(engine_natal, engine_now, now) -> str:
    lines = []
    try:
        from app.services.kp.kp_complete import KPComplete
        kp = KPComplete(engine_natal)

        rp = kp.get_ruling_planets(query_time=now)
        if isinstance(rp, dict):
            for key in ['day_lord', 'moon_sign_lord', 'moon_star_lord', 'moon_sub_lord', 'ascendant_sign_lord', 'ascendant_star_lord']:
                if rp.get(key):
                    lines.append(f"{key.replace('_', ' ').title()}: {rp[key]}")
            rp_common = rp.get('common_rp', rp.get('ruling_planets', []))
            if isinstance(rp_common, list) and rp_common:
                lines.append(f"Ruling planets: {', '.join(rp_common)}")

        for h in [1, 2, 7, 10, 11]:
            try:
                fruit = kp.check_fruitfulness(house=h)
                if isinstance(fruit, dict) and fruit.get('verdict'):
                    lines.append(f"H{h} ({fruit.get('cuspal_sub_lord', '')}): {fruit['verdict']}")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"KP data limited: {str(e)[:60]}")

    return '\n'.join(lines) if lines else 'KP system data unavailable for this chart.'


def _build_western_data(engine_natal, now) -> str:
    lines = []
    try:
        from app.services.western.chart import WesternChart
        wc = WesternChart(engine_natal.birth_dt, engine_natal.latitude, engine_natal.longitude)

        big3 = wc.get_big_three()
        if isinstance(big3, dict):
            lines.append(f"Sun: {big3.get('sun_sign', '')} | Moon: {big3.get('moon_sign', '')} | Rising: {big3.get('rising_sign', '')}")

        aspects = wc.get_aspects()
        if isinstance(aspects, list):
            tight = [a for a in aspects if isinstance(a, dict) and abs(a.get('orb', 99)) < 3]
            for a in tight[:6]:
                lines.append(f"{a.get('planet1', '')} {a.get('aspect_name', '')} {a.get('planet2', '')} (orb {a.get('orb', 0):.1f}°)")

        eb = wc.get_element_balance()
        if isinstance(eb, dict):
            lines.append(f"Elements — Fire:{eb.get('fire',0)} Earth:{eb.get('earth',0)} Air:{eb.get('air',0)} Water:{eb.get('water',0)}")
            dominant = max(eb.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
            lines.append(f"Dominant element: {dominant[0]}")

        try:
            ct = wc.get_current_transits()
            if isinstance(ct, list):
                for t in ct[:5]:
                    if isinstance(t, dict):
                        lines.append(f"Transit {t.get('transit_planet', '')} {t.get('aspect', '')} natal {t.get('natal_planet', '')} — {t.get('meaning', '')[:80]}")
        except Exception:
            pass
    except Exception as e:
        lines.append(f"Western data limited: {str(e)[:60]}")

    try:
        transits = _safe(lambda: engine_natal.get_current_transits() if hasattr(engine_natal, 'get_current_transits') else {}, {})
        if isinstance(transits, dict):
            sun_long = transits.get('Sun', {}).get('longitude', 0)
            moon_long = transits.get('Moon', {}).get('longitude', 0)
            diff = (moon_long - sun_long) % 360
            phases = [(22.5,'New Moon'),(67.5,'Waxing Crescent'),(112.5,'First Quarter'),(157.5,'Waxing Gibbous'),(202.5,'Full Moon'),(247.5,'Waning Gibbous'),(292.5,'Last Quarter'),(360,'Waning Crescent')]
            phase = next((p for d,p in phases if diff < d), 'Waning Crescent')
            lines.append(f"Moon phase: {phase}")
    except Exception:
        pass

    return '\n'.join(lines) if lines else 'Western data limited.'


def _build_chinese_data(engine_natal, now) -> str:
    lines = []
    try:
        from app.services.chinese.bazi import BaZiChart

        bazi_natal = BaZiChart(engine_natal.birth_dt)
        dm = bazi_natal.get_day_master()
        if isinstance(dm, dict):
            lines.append(f"Your Day Master: {dm.get('stem', '')} {dm.get('element', '')} ({dm.get('yin_yang', '')})")
            lines.append(f"Day Master nature: {dm.get('description', '')[:100]}")

        balance_natal = bazi_natal.get_element_balance()
        if isinstance(balance_natal, dict):
            lines.append(f"Your dominant element: {balance_natal.get('day_master_element', '')}")
            elements = balance_natal.get('elements', {})
            if isinstance(elements, dict):
                lines.append(f"Birth balance: {', '.join([f'{k}:{v}' for k, v in elements.items() if isinstance(v, (int, float))])}")

        bazi_today = BaZiChart(now)
        today_pillars = bazi_today.get_four_pillars()
        if isinstance(today_pillars, dict):
            day_p = today_pillars.get('day', {})
            if isinstance(day_p, dict):
                lines.append(f"Today's stem: {day_p.get('stem', '')} ({day_p.get('element', '')})")
                lines.append(f"Today's branch: {day_p.get('branch', '')} ({day_p.get('animal', '')})")

        today_dm = bazi_today.get_day_master()
        if isinstance(today_dm, dict) and isinstance(dm, dict):
            lines.append(f"Today's element ({today_dm.get('element', '')}) vs yours ({dm.get('element', '')})")

        animal = bazi_today.get_animal_sign()
        if isinstance(animal, dict):
            lines.append(f"Today's animal: {animal.get('animal', '')} ({animal.get('element', '')})")

        try:
            ten_gods = bazi_natal.get_ten_gods()
            if isinstance(ten_gods, dict):
                gods_list = ten_gods.get('gods', ten_gods.get('pillars', []))
                if isinstance(gods_list, list):
                    god_names = [g.get('god', g.get('name', '')) for g in gods_list if isinstance(g, dict)]
                    if god_names:
                        lines.append(f"Ten Gods: {', '.join(god_names[:4])}")
        except Exception:
            pass
    except Exception as e:
        lines.append(f"Chinese data limited: {str(e)[:60]}")

    return '\n'.join(lines) if lines else 'Chinese data limited.'


def _build_numerology_data(engine_natal, now) -> str:
    lines = []
    try:
        from app.services.numerology.core import NumerologyEngine

        birth_date = engine_natal.birth_dt.date() if hasattr(engine_natal.birth_dt, 'date') else date.today()
        nc = NumerologyEngine(name='', birth_date=birth_date)

        mulank = nc.get_mulank()
        if isinstance(mulank, dict):
            lines.append(f"Mulank (Root): {mulank.get('number', '')} — {mulank.get('planet', '')} ({mulank.get('meaning', '')[:60]})")

        bhagyank = nc.get_bhagyank()
        if isinstance(bhagyank, dict):
            lines.append(f"Bhagyank (Destiny): {bhagyank.get('number', '')} — {bhagyank.get('planet', '')} ({bhagyank.get('meaning', '')[:60]})")

        py = nc.get_personal_year()
        if isinstance(py, dict):
            lines.append(f"Personal Year: {py.get('number', '')} — {py.get('theme', py.get('meaning', ''))[:80]}")

        pm = nc.get_personal_month()
        if isinstance(pm, dict):
            lines.append(f"Personal Month: {pm.get('number', '')} — {pm.get('theme', pm.get('meaning', ''))[:80]}")

        pd = nc.get_personal_day(target_date=now.date() if hasattr(now, 'date') else now)
        if isinstance(pd, dict):
            lines.append(f"Personal Day: {pd.get('number', '')} — {pd.get('theme', pd.get('meaning', ''))[:80]}")

        today = now if isinstance(now, date) else now.date()
        u_day = sum(int(d) for d in str(today.year) + str(today.month).zfill(2) + str(today.day).zfill(2))
        while u_day > 9 and u_day not in (11, 22, 33):
            u_day = sum(int(d) for d in str(u_day))
        lines.append(f"Universal Day: {u_day}")
    except Exception as e:
        lines.append(f"Numerology data limited: {str(e)[:60]}")

    return '\n'.join(lines) if lines else 'Numerology data limited.'


# ═══════════════════════════════════════════════════════════════
# ASSEMBLER + PROMPT
# ═══════════════════════════════════════════════════════════════

def _assemble_day(engine_natal, birth_data, target_date):
    from app.services.jyotish_engine import JyotishEngine
    lat = birth_data.get('lat', birth_data.get('latitude', 25.35))
    lng = birth_data.get('lng', birth_data.get('longitude', 74.64))
    try:
        engine_day = JyotishEngine(target_date, lat, lng)
    except Exception:
        engine_day = engine_natal
    vedic = _build_vedic_data(engine_natal, engine_day, target_date)
    kp = _build_kp_data(engine_natal, engine_day, target_date)
    western = _build_western_data(engine_natal, target_date)
    chinese = _build_chinese_data(engine_natal, target_date)
    numr = _build_numerology_data(engine_natal, target_date)
    label = target_date.strftime('%A, %B %d, %Y')
    briefing = f'DATE: {label}\n\nVEDIC:\n{vedic}\n\nKP:\n{kp}\n\nWESTERN:\n{western}\n\nCHINESE:\n{chinese}\n\nNUMEROLOGY:\n{numr}'
    return {'briefing': briefing, 'date': label}


def _prompt_single_day(data, language='en'):
    briefing = data['briefing']
    lang = ''
    if language and language.lower() not in ('english', 'en'):
        lang = ' Write in ' + language + '.'
    return '''You are the Oracle.''' + lang + '''
Make them feel seen, not informed.
Root the language in human behaviour, profound psychology, colour psychology, emotions and brain patterns — so they cannot stop coming back.

This is a DAILY READING. The person opens this every day.

Data:
''' + briefing + '''

Return ONLY valid JSON:
{
  "hook_title": "max 8 words. Punch. Persuasive. Stop them mid-scroll.",
  "hook_body": "2 sentences. What they feel today but won't say.",
  "cta_dive": "4-6 words. Curiosity.",
  "vedic": {"headline":"3-5 words","reading":"3-4 sentences","deeper":"3-4 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words to next system"},
  "kp": {"headline":"3-5 words","reading":"3-4 sentences","deeper":"3-4 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "western": {"headline":"3-5 words","reading":"3-4 sentences","deeper":"3-4 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "chinese": {"headline":"3-5 words","reading":"3-4 sentences","deeper":"3-4 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","cta_next":"5-8 words"},
  "numerology": {"headline":"3-5 words","reading":"3-4 sentences","deeper":"3-4 sentences","do":["if needed"],"dont":["if needed"],"cta_deeper":"4-6 words","cta_verdict":"4-6 words","closing":"1 sentence. All five unified."}
}

~800 words total. Headlines SHORT and punchy. Do/dont only when genuinely needed — skip if not.'''


class _TodayDeepRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
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


async def _fetch_one_day(engine_natal, birth_data, target_date, language, settings):
    import json as json_parse
    data = _assemble_day(engine_natal, birth_data, target_date)
    prompt = _prompt_single_day(data, language)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': settings.OPENROUTER_MODEL, 'messages': [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': 'Read this day.'}], 'max_tokens': 2500, 'temperature': 0.8},
            timeout=120.0,
        )
    if response.status_code != 200:
        return None
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
    return None


@router.post('/today-deep')
async def get_today_deep(request_body: _TodayDeepRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit
    from datetime import timedelta
    import asyncio
    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))
    birth_data = _extract_birth(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    try:
        from app.services.oracle.engine_cache import get_cached_engine
        birth_dt = datetime(birth_data['year'], birth_data['month'], birth_data['day'], birth_data.get('hour', 12), birth_data.get('minute', 0))
        engine, _ = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        language = request_body.language or 'en'
        now = datetime.now()
        targets = [now + timedelta(days=i) for i in range(7)]
        tasks = [_fetch_one_day(engine, birth_data, t, language, settings) for t in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        days = {}
        for i, t in enumerate(targets):
            dk = t.strftime('%Y-%m-%d')
            r = results[i]
            if isinstance(r, dict):
                days[dk] = r
            else:
                days[dk] = {'error': str(r) if isinstance(r, Exception) else 'failed'}
        return {'date': now.strftime('%Y-%m-%d'), 'days': days}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

today_deep_router = router
