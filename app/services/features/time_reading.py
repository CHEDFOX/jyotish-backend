"""
TIME — Today · This Week · This Month

Calculates current transits, upcoming aspects, Moon phases,
sign ingresses for day/week/month windows.
LLM writes short notes for each period.

Called by: POST /time-reading { kundli_data }
"""

from datetime import datetime, timedelta
from typing import Dict


WEEKDAY_LORDS = {
    0: 'Moon', 1: 'Mars', 2: 'Mercury', 3: 'Jupiter',
    4: 'Venus', 5: 'Saturn', 6: 'Sun',
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


def build_time_reading(engine, language: str = 'en') -> Dict:
    """Build today + week + month astrological snapshot."""

    now = datetime.now()
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    # Current transits
    transits = _safe(engine.get_current_transits, {})
    if not isinstance(transits, dict): transits = {}

    # Natal data
    natal_moon = _pl(planets, 'Moon')
    natal_moon_sign = natal_moon.get('rashi_name', '')
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    asc_sign = asc.get('rashi_name', '')

    # Active dasha
    dasha = _safe(engine.get_vimshottari_dasha, {})
    if not isinstance(dasha, dict): dasha = {}
    dasha_string = dasha.get('dasha_string', '')
    maha = dasha.get('mahadasha', {})
    if not isinstance(maha, dict): maha = {}
    maha_lord = maha.get('lord', '')

    # Day lord
    day_lord = WEEKDAY_LORDS.get(now.weekday(), '')

    # Transit Moon
    t_moon = transits.get('Moon', {})
    if not isinstance(t_moon, dict): t_moon = {}
    moon_transit_sign = t_moon.get('rashi_name', '')
    moon_transit_nak = t_moon.get('nakshatra_name', '')

    # Transit Sun
    t_sun = transits.get('Sun', {})
    if not isinstance(t_sun, dict): t_sun = {}
    sun_transit_sign = t_sun.get('rashi_name', '')

    # Retrograde planets
    retros = []
    for pname, pdata in transits.items():
        if not isinstance(pdata, dict): continue
        if pdata.get('retrograde', False) or pdata.get('is_retrograde', False):
            retros.append(pname)

    # Panchanga
    panchanga = _safe(engine.get_panchanga, {})
    if not isinstance(panchanga, dict): panchanga = {}
    tithi = panchanga.get('tithi', {})
    if not isinstance(tithi, dict): tithi = {}
    tithi_name = tithi.get('name', '')
    paksha = tithi.get('paksha', '')

    # Transit positions for key planets
    transit_positions = {}
    for pname in ['Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu']:
        tp = transits.get(pname, {})
        if isinstance(tp, dict):
            transit_positions[pname] = {
                'sign': tp.get('rashi_name', ''),
                'retro': tp.get('retrograde', False) or tp.get('is_retrograde', False),
            }

    # Week info
    week_end = now + timedelta(days=7)
    week_day_lords = [WEEKDAY_LORDS.get((now + timedelta(days=i)).weekday(), '') for i in range(7)]
    dominant_week_lord = max(set(week_day_lords), key=week_day_lords.count) if week_day_lords else ''

    # Month info
    month_name = now.strftime('%B %Y')
    days_left = (datetime(now.year, now.month + 1 if now.month < 12 else 1, 1, tzinfo=None) - now).days if now.month < 12 else (datetime(now.year + 1, 1, 1) - now).days

    # Build briefing
    briefing = f"""TIME READING for {asc_sign} ascendant, Moon in {natal_moon_sign}
Dasha: {dasha_string} | Maha lord: {maha_lord}
Date: {now.strftime('%A, %B %d, %Y')}

TODAY:
  Day lord: {day_lord} ({now.strftime('%A')})
  Moon: {moon_transit_sign} ({moon_transit_nak})
  Sun: {sun_transit_sign}
  Tithi: {tithi_name} ({paksha})
  Retrogrades: {', '.join(retros) if retros else 'None'}

THIS WEEK ({now.strftime('%b %d')} – {week_end.strftime('%b %d')}):
  Key transits: {', '.join(f'{k} in {v["sign"]}{"(R)" if v["retro"] else ""}' for k, v in transit_positions.items())}
  Moon moves through ~3 signs this week

THIS MONTH ({month_name}, {days_left} days left):
  Sun in {sun_transit_sign}
  Major transits: {', '.join(f'{k} in {v["sign"]}' for k, v in transit_positions.items())}
  Dasha period: {dasha_string}"""

    return {
        'today': {
            'date': now.strftime('%A, %B %d'),
            'day_lord': day_lord,
            'moon_sign': moon_transit_sign,
            'moon_nakshatra': moon_transit_nak,
            'sun_sign': sun_transit_sign,
            'tithi': tithi_name,
            'paksha': paksha,
            'retrogrades': retros,
        },
        'week': {
            'range': f"{now.strftime('%b %d')} – {week_end.strftime('%b %d')}",
            'transit_positions': transit_positions,
        },
        'month': {
            'name': month_name,
            'days_left': days_left,
            'sun_sign': sun_transit_sign,
            'dasha': dasha_string,
        },
        'natal': {
            'ascendant': asc_sign,
            'moon_sign': natal_moon_sign,
        },
        'briefing': briefing,
    }


def build_time_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for 3-segment time reading."""
    briefing = data['briefing']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a warm, modern astrologer giving quick time-based readings.{lang_note}

{briefing}

Write THREE short readings separated by ---

TODAY (2-3 sentences):
What today feels like. Mention the day lord and Moon transit.
One specific thing to watch for or lean into.

THIS WEEK (2-3 sentences):
The week's energy arc. What's building or releasing.
One key day or shift to be aware of.

THIS MONTH (2-3 sentences):
The bigger picture. What this month is asking of them.
How the dasha period colors everything.

Rules:
- Each section: 2-3 sentences only
- Mix a little astrology with plain language — "Moon in Gemini means your mind won't sit still" not "the lunar transit activates your third house"
- Be specific to their chart — reference their ascendant or Moon sign
- Separate sections with exactly ---
- No headers, no labels. Just the readings.
- Under 150 words total."""
