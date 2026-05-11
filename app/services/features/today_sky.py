"""
TODAY'S SKY — What the day holds for you.

Calculates: current transits, tithi, nakshatra, yoga, karana,
active dasha, transit aspects to natal chart, moon sign transit.

Returns: structured day data + LLM guiding note.

Called by: POST /today { kundli_data }
"""

from datetime import datetime
from typing import Dict


WEEKDAY_LORDS = {
    0: ('Moon', 'Monday'),
    1: ('Mars', 'Tuesday'),
    2: ('Mercury', 'Wednesday'),
    3: ('Jupiter', 'Thursday'),
    4: ('Venus', 'Friday'),
    5: ('Saturn', 'Saturday'),
    6: ('Sun', 'Sunday'),
}

TITHI_NAMES = [
    'Pratipada', 'Dwitiya', 'Tritiya', 'Chaturthi', 'Panchami',
    'Shashthi', 'Saptami', 'Ashtami', 'Navami', 'Dashami',
    'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi', 'Purnima',
    'Pratipada', 'Dwitiya', 'Tritiya', 'Chaturthi', 'Panchami',
    'Shashthi', 'Saptami', 'Ashtami', 'Navami', 'Dashami',
    'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi', 'Amavasya',
]


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def _pl(planets, name):
    p = planets.get(name, {})
    return p if isinstance(p, dict) else {}


def build_today(engine, language: str = 'en') -> Dict:
    """Build today's astrological snapshot for this person."""

    now = datetime.now()
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    # Current transits
    transits = _safe(engine.get_current_transits, {})
    if not isinstance(transits, dict): transits = {}

    # Today's weekday lord
    day_idx = now.weekday()
    day_lord, day_name = WEEKDAY_LORDS.get(day_idx, ('', ''))

    # Moon transit (most important daily indicator)
    t_moon = transits.get('Moon', {})
    if not isinstance(t_moon, dict): t_moon = {}
    moon_transit_sign = t_moon.get('rashi_name', '')
    moon_transit_nak = t_moon.get('nakshatra_name', '')
    moon_transit_house = t_moon.get('house_from_natal', t_moon.get('house', 0))

    # Sun transit
    t_sun = transits.get('Sun', {})
    if not isinstance(t_sun, dict): t_sun = {}
    sun_transit_sign = t_sun.get('rashi_name', '')

    # Natal moon sign (for transit comparison)
    natal_moon = _pl(planets, 'Moon')
    natal_moon_sign = natal_moon.get('rashi_name', '')
    natal_moon_nak = natal_moon.get('nakshatra_name', '')

    # Active dasha
    dasha = _safe(engine.get_vimshottari_dasha, {})
    if not isinstance(dasha, dict): dasha = {}
    maha = dasha.get('mahadasha', {})
    if not isinstance(maha, dict): maha = {}
    antar = dasha.get('antardasha', {})
    if not isinstance(antar, dict): antar = {}
    dasha_string = dasha.get('dasha_string', '')
    maha_lord = maha.get('lord', '')

    # Panchanga-like data
    panchanga = _safe(engine.get_panchanga, {})
    if not isinstance(panchanga, dict): panchanga = {}
    tithi = panchanga.get('tithi', {})
    if not isinstance(tithi, dict): tithi = {}
    tithi_name = tithi.get('name', '')
    tithi_num = tithi.get('number', 0)
    paksha = tithi.get('paksha', '')

    yoga_panch = panchanga.get('yoga', {})
    if not isinstance(yoga_panch, dict): yoga_panch = {}
    yoga_name = yoga_panch.get('name', '')

    karana = panchanga.get('karana', {})
    if not isinstance(karana, dict): karana = {}
    karana_name = karana.get('name', '')

    # Retrograde planets in transit
    retro_planets = []
    for pname, pdata in transits.items():
        if not isinstance(pdata, dict): continue
        if pdata.get('retrograde', False) or pdata.get('is_retrograde', False):
            retro_planets.append(pname)

    # Day lord relationship to chart
    natal_day_lord = _pl(planets, day_lord)
    day_lord_house = natal_day_lord.get('house', 0)
    day_lord_sign = natal_day_lord.get('rashi_name', '')

    # Ascendant
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    asc_sign = asc.get('rashi_name', '')

    # Briefing for LLM
    briefing = f"""TODAY: {now.strftime('%A, %B %d, %Y')}

PERSON: {asc_sign} ascendant, natal Moon in {natal_moon_sign} ({natal_moon_nak})
Active dasha: {dasha_string}
Mahadasha lord: {maha_lord}

DAY ENERGY:
  Day lord: {day_lord} ({day_name}) — in your chart at H{day_lord_house} in {day_lord_sign}
  Moon transiting: {moon_transit_sign} ({moon_transit_nak})
  Sun transiting: {sun_transit_sign}

PANCHANGA:
  Tithi: {tithi_name} ({paksha})
  Yoga: {yoga_name}
  Karana: {karana_name}

RETROGRADE PLANETS: {', '.join(retro_planets) if retro_planets else 'None'}"""

    return {
        'date': now.strftime('%A, %B %d, %Y'),
        'day_lord': day_lord,
        'day_name': day_name,
        'day_lord_house': day_lord_house,
        'day_lord_sign': day_lord_sign,
        'moon_transit': moon_transit_sign,
        'moon_nakshatra': moon_transit_nak,
        'sun_transit': sun_transit_sign,
        'natal_moon': natal_moon_sign,
        'tithi': tithi_name,
        'paksha': paksha,
        'yoga': yoga_name,
        'karana': karana_name,
        'dasha': dasha_string,
        'retro_planets': retro_planets,
        'ascendant': asc_sign,
        'briefing': briefing,
    }


def build_today_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for today's reading."""
    briefing = data['briefing']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are the voice of the stars — ancient, warm, mystical, true.
You are telling this person about their day.{lang_note}

{briefing}

Write a short, warm reading about TODAY for this person.

3-5 sentences only. No headers, no bullets, no bold, no labels.
Just flowing text — like a wise friend telling you what to expect today.

Be specific: mention the day lord, the moon's transit, and how it touches their chart.
If a planet is retrograde, mention it briefly.
End with one gentle suggestion or affirmation.

Maximum 80 words. Warm, precise, personal."""
