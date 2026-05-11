"""
WESTERN PLANETS — Single planet deep dive with all aspects.

10 planets: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto.
For each: sign, house, dignity, all aspects to other planets.
LLM writes significance + aspect-by-aspect short notes.

Called by: POST /western-planet { planet, kundli_data }
"""

from datetime import datetime
from typing import Dict, List


WESTERN_PLANETS = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']

PLANET_SIGNIFICANCE = {
    'Sun':     {'domain': 'Identity, ego, vitality, father, life purpose', 'archetype': 'The Self', 'rules': 'Leo'},
    'Moon':    {'domain': 'Emotions, instincts, mother, inner world, habits', 'archetype': 'The Soul', 'rules': 'Cancer'},
    'Mercury': {'domain': 'Communication, thinking, learning, wit, travel', 'archetype': 'The Messenger', 'rules': 'Gemini, Virgo'},
    'Venus':   {'domain': 'Love, beauty, values, money, pleasure, art', 'archetype': 'The Lover', 'rules': 'Taurus, Libra'},
    'Mars':    {'domain': 'Drive, aggression, sex, courage, conflict', 'archetype': 'The Warrior', 'rules': 'Aries, Scorpio'},
    'Jupiter': {'domain': 'Expansion, luck, wisdom, travel, beliefs', 'archetype': 'The Sage', 'rules': 'Sagittarius, Pisces'},
    'Saturn':  {'domain': 'Structure, discipline, limits, time, karma', 'archetype': 'The Teacher', 'rules': 'Capricorn, Aquarius'},
    'Uranus':  {'domain': 'Revolution, freedom, shock, genius, technology', 'archetype': 'The Rebel', 'rules': 'Aquarius'},
    'Neptune': {'domain': 'Illusion, dreams, spirituality, addiction, art', 'archetype': 'The Mystic', 'rules': 'Pisces'},
    'Pluto':   {'domain': 'Transformation, power, death, rebirth, obsession', 'archetype': 'The Alchemist', 'rules': 'Scorpio'},
}

ASPECT_NATURE = {
    'conjunction': {'symbol': '☌', 'nature': 'fusion', 'feel': 'intense merging'},
    'opposition':  {'symbol': '☍', 'nature': 'tension', 'feel': 'tug of war'},
    'trine':       {'symbol': '△', 'nature': 'harmony', 'feel': 'natural flow'},
    'square':      {'symbol': '□', 'nature': 'friction', 'feel': 'internal conflict'},
    'sextile':     {'symbol': '⚹', 'nature': 'opportunity', 'feel': 'gentle support'},
    'quincunx':    {'symbol': '⚻', 'nature': 'adjustment', 'feel': 'awkward tension'},
    'semi-square': {'symbol': '∠', 'nature': 'irritation', 'feel': 'minor friction'},
    'sesquiquadrate': {'symbol': '⚼', 'nature': 'agitation', 'feel': 'restless push'},
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_western_planet(engine, planet_name: str, language: str = 'en') -> Dict:
    """Build comprehensive Western planet data with all aspects."""

    if planet_name not in WESTERN_PLANETS:
        return {'error': f'Unknown planet: {planet_name}. Valid: {", ".join(WESTERN_PLANETS)}'}

    from app.services.western.chart import WesternChart
    chart = WesternChart(engine.birth_dt, engine.latitude, engine.longitude)

    # Get all aspects
    all_aspects = _safe(chart.get_aspects, [])
    if not isinstance(all_aspects, list): all_aspects = []

    # Planet data from chart
    planets_data = {}
    if hasattr(chart, '_planets') and isinstance(chart._planets, dict):
        chart._ensure_calculated()
        planets_data = chart._planets
    elif hasattr(chart, 'planets') and isinstance(chart.planets, dict):
        planets_data = chart.planets

    pl = planets_data.get(planet_name, {})
    if not isinstance(pl, dict): pl = {}

    sign = pl.get('sign', '')
    house = pl.get('house', 0)
    degree = round(pl.get('longitude', 0) % 30, 2) if pl.get('longitude') else 0
    full_degree = round(pl.get('longitude', 0), 2)
    is_retro = pl.get('retrograde', False) or pl.get('is_retrograde', False)
    dignity = pl.get('dignity', '')

    # Filter aspects involving this planet
    planet_aspects = []
    for a in all_aspects:
        if not isinstance(a, dict): continue
        p1 = a.get('planet1', '')
        p2 = a.get('planet2', '')
        if p1 == planet_name or p2 == planet_name:
            other = p2 if p1 == planet_name else p1
            other_data = planets_data.get(other, {})
            if not isinstance(other_data, dict): other_data = {}

            aspect_type = a.get('aspect', '')
            aspect_info = ASPECT_NATURE.get(aspect_type, {})
            orb = round(a.get('orb', 0), 1)
            applying = a.get('applying', None)

            planet_aspects.append({
                'other_planet': other,
                'other_sign': other_data.get('sign', ''),
                'other_house': other_data.get('house', 0),
                'aspect': aspect_type,
                'symbol': aspect_info.get('symbol', ''),
                'nature': aspect_info.get('nature', ''),
                'feel': aspect_info.get('feel', ''),
                'orb': orb,
                'applying': applying,
                'tight': orb < 2,
            })

    # Sort by tightness (tightest first)
    planet_aspects.sort(key=lambda a: a['orb'])

    # Significance data
    sig = PLANET_SIGNIFICANCE.get(planet_name, {})

    # Build briefing
    briefing_lines = [
        f"PLANET: {planet_name} ({sig.get('archetype', '')}) in {sign} H{house} at {degree}°",
        f"Dignity: {dignity or 'none'} | Retrograde: {'YES' if is_retro else 'no'}",
        f"Domain: {sig.get('domain', '')}",
        f"Rules: {sig.get('rules', '')}",
        "",
        f"ASPECTS ({len(planet_aspects)} total):",
    ]
    for a in planet_aspects:
        tight = "TIGHT" if a['tight'] else ""
        app = "applying" if a['applying'] else "separating" if a['applying'] is False else ""
        briefing_lines.append(
            f"  {planet_name} {a['aspect']} {a['other_planet']} (in {a['other_sign']} H{a['other_house']}) — orb {a['orb']}° {tight} {app} — {a['nature']}"
        )

    return {
        'planet': planet_name,
        'archetype': sig.get('archetype', ''),
        'domain': sig.get('domain', ''),
        'rules': sig.get('rules', ''),
        'sign': sign,
        'house': house,
        'degree': degree,
        'is_retrograde': is_retro,
        'dignity': dignity,
        'aspects': planet_aspects,
        'briefing': '\n'.join(briefing_lines),
    }


def build_western_planet_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for Western planet reading with aspects."""
    planet = data['planet']
    briefing = data['briefing']
    aspects = data['aspects']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    aspect_count = len(aspects)

    return f"""You are a Western astrologer — modern, insightful, direct.{lang_note}

{briefing}

Write two parts separated by ===

PART 1 — SIGNIFICANCE (3-4 sentences):
What {planet} as "{data['archetype']}" means in {data['sign']} in house {data['house']}.
How this placement shapes the person's {data['domain'].split(',')[0].lower()}.
If retrograde, what that changes.

PART 2 — ASPECTS ({aspect_count} aspects, write 1 line each):
For each aspect, write ONE short line (10-15 words) about how it plays out in the person's life.
Format each as: {planet} [aspect] [other planet] — [the one-line reading]

Be specific to the signs and houses. Not generic.
Total under 250 words. No bullets, no bold."""
