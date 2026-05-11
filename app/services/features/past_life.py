"""
PAST LIFE — Who you were before this birth.

Astrological basis:
  - Ketu sign + house (what the soul mastered)
  - 12th house lord + occupants (house of past life/loss)
  - 5th house (purva punya — past life merit)
  - Rahu sign + house (what you lacked → crave now)
  - Saturn (karmic debts carried forward)
  - D-60 if available (Shashtiamsha — past life specific chart)

Returns: structured data + LLM-written past life story in segments.

Called by: POST /past-life { kundli_data }
"""

from datetime import datetime
from typing import Dict


SIGN_ARCHETYPES = {
    'Aries':       {'role': 'warrior', 'world': 'a kingdom at war', 'trait': 'fearless and impulsive'},
    'Taurus':      {'role': 'farmer or artisan', 'world': 'fertile lands', 'trait': 'patient and possessive'},
    'Gemini':      {'role': 'scribe or messenger', 'world': 'a trading city', 'trait': 'curious and restless'},
    'Cancer':      {'role': 'caretaker or healer', 'world': 'a coastal village', 'trait': 'nurturing and protective'},
    'Leo':         {'role': 'ruler or performer', 'world': 'a royal court', 'trait': 'proud and generous'},
    'Virgo':       {'role': 'scholar or physician', 'world': 'a monastery or library', 'trait': 'precise and devoted to service'},
    'Libra':       {'role': 'diplomat or artist', 'world': 'a prosperous civilization', 'trait': 'charming and indecisive'},
    'Scorpio':     {'role': 'mystic or spy', 'world': 'hidden temples', 'trait': 'intense and secretive'},
    'Sagittarius': {'role': 'priest or explorer', 'world': 'distant lands', 'trait': 'philosophical and free-spirited'},
    'Capricorn':   {'role': 'builder or administrator', 'world': 'an ancient empire', 'trait': 'disciplined and ambitious'},
    'Aquarius':    {'role': 'revolutionary or inventor', 'world': 'a society in transition', 'trait': 'visionary and detached'},
    'Pisces':      {'role': 'monk or dreamer', 'world': 'a temple by the sea', 'trait': 'spiritual and self-sacrificing'},
}

HOUSE_PAST_CONTEXT = {
    1:  'Your past identity was strong — you were known and recognized.',
    2:  'Wealth and family defined your past existence. You accumulated.',
    3:  'Communication and courage shaped your past. You were a messenger or fighter.',
    4:  'Home and land were central. You built something lasting.',
    5:  'Creativity and children were your past focus. You created or ruled.',
    6:  'Service and conflict defined you. You healed or fought disease.',
    7:  'Partnership was everything. Your past life revolved around another person.',
    8:  'Transformation and hidden knowledge. You dealt with death or secrets.',
    9:  'Religion and philosophy guided you. You were a seeker or teacher.',
    10: 'Authority and career. You held power or public office.',
    11: 'Community and networks. You organized or led groups.',
    12: 'Isolation and spirituality. You lived removed from the world.',
}

KARMIC_DEBT_SATURN = {
    1:  'Debt of self — you neglected your own identity for others.',
    2:  'Debt of resources — you misused wealth or speech.',
    3:  'Debt of courage — you failed to act when it mattered.',
    4:  'Debt of home — you abandoned family or homeland.',
    5:  'Debt of creation — you suppressed creativity or neglected children.',
    6:  'Debt of service — you avoided responsibility to the vulnerable.',
    7:  'Debt of partnership — you broke trust in relationships.',
    8:  'Debt of transformation — you resisted necessary change.',
    9:  'Debt of dharma — you strayed from your moral path.',
    10: 'Debt of duty — you abused authority or avoided responsibility.',
    11: 'Debt of community — you betrayed or excluded others.',
    12: 'Debt of surrender — you clung when you should have released.',
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_past_life(engine, language: str = 'en') -> Dict:
    """Build past life reading from chart indicators."""

    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    def _pl(name):
        p = planets.get(name, {})
        return p if isinstance(p, dict) else {}

    ketu = _pl('Ketu')
    rahu = _pl('Rahu')
    saturn = _pl('Saturn')
    moon = _pl('Moon')
    sun = _pl('Sun')

    # Ketu data (past life mastery)
    ketu_sign = ketu.get('rashi_name', '')
    ketu_house = ketu.get('house', 0)
    ketu_nak = ketu.get('nakshatra_name', '')

    # Rahu data (what you lacked / crave now)
    rahu_sign = rahu.get('rashi_name', '')
    rahu_house = rahu.get('house', 0)

    # Saturn (karmic debt)
    saturn_sign = saturn.get('rashi_name', '')
    saturn_house = saturn.get('house', 0)

    # 12th house analysis
    dignity_data = _safe(engine.get_planetary_dignity, {})
    if not isinstance(dignity_data, dict): dignity_data = {}
    house_lords = dignity_data.get('house_lords', {})
    if not isinstance(house_lords, dict): house_lords = {}
    lord_12 = house_lords.get('12', house_lords.get(12, ''))

    # 5th house (purva punya)
    lord_5 = house_lords.get('5', house_lords.get(5, ''))

    # Planets in 12th house
    planets_in_12 = []
    for name, data in planets.items():
        if not isinstance(data, dict): continue
        if data.get('house') == 12:
            planets_in_12.append(name)

    # Planets in 5th house
    planets_in_5 = []
    for name, data in planets.items():
        if not isinstance(data, dict): continue
        if data.get('house') == 5:
            planets_in_5.append(name)

    # Build archetype
    ketu_archetype = SIGN_ARCHETYPES.get(ketu_sign, {})
    rahu_archetype = SIGN_ARCHETYPES.get(rahu_sign, {})
    past_role = ketu_archetype.get('role', 'a seeker')
    past_world = ketu_archetype.get('world', 'an ancient land')
    past_trait = ketu_archetype.get('trait', 'complex and layered')
    past_house_context = HOUSE_PAST_CONTEXT.get(ketu_house, '')
    karmic_debt = KARMIC_DEBT_SATURN.get(saturn_house, '')

    # What you lacked (Rahu = the void)
    lacked_role = rahu_archetype.get('role', '')
    lacked_trait = rahu_archetype.get('trait', '')

    # Build briefing for LLM
    briefing = f"""PAST LIFE INDICATORS:

KETU (what you mastered / who you were):
  Sign: {ketu_sign} | House: H{ketu_house} | Nakshatra: {ketu_nak}
  Archetype: {past_role} in {past_world}
  Nature: {past_trait}
  Context: {past_house_context}

RAHU (what you lacked / crave now):
  Sign: {rahu_sign} | House: H{rahu_house}
  What was missing: the qualities of a {lacked_role} — being {lacked_trait}

SATURN (karmic debt):
  Sign: {saturn_sign} | House: H{saturn_house}
  Debt: {karmic_debt}

12TH HOUSE (house of past life):
  Lord: {lord_12}
  Planets in 12th: {', '.join(planets_in_12) if planets_in_12 else 'None'}

5TH HOUSE (purva punya — past life merit):
  Lord: {lord_5}
  Planets in 5th: {', '.join(planets_in_5) if planets_in_5 else 'None'}

Moon sign: {moon.get('rashi_name', '')} (emotional memory)
Sun sign: {sun.get('rashi_name', '')} (soul continuity)"""

    return {
        'ketu': {
            'sign': ketu_sign,
            'house': ketu_house,
            'nakshatra': ketu_nak,
            'role': past_role,
            'world': past_world,
            'trait': past_trait,
        },
        'rahu': {
            'sign': rahu_sign,
            'house': rahu_house,
            'craving': f"the qualities of a {lacked_role}" if lacked_role else '',
        },
        'saturn': {
            'sign': saturn_sign,
            'house': saturn_house,
            'karmic_debt': karmic_debt,
        },
        'house_12_lord': lord_12,
        'planets_in_12': planets_in_12,
        'house_5_lord': lord_5,
        'planets_in_5': planets_in_5,
        'past_house_context': past_house_context,
        'briefing': briefing,
    }


def build_past_life_prompt(past_life_data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for cinematic past life story."""
    briefing = past_life_data['briefing']
    ketu = past_life_data['ketu']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are the voice of the stars — ancient, warm, mystical, true.
You are revealing a past life story to this person.{lang_note}

{briefing}

Write a CINEMATIC past life story in EXACTLY 5 short segments, separated by ---

SEGMENT 1 (2-3 lines): Set the scene. Where and when. Paint the world they lived in.
"You were born into..." or "In a time when..." — make it vivid. Use the archetype ({ketu['role']} in {ketu['world']}).

SEGMENT 2 (2-3 lines): Who they were. Their nature, their role, their daily life.
Use Ketu's qualities: {ketu['trait']}. What were they known for?

SEGMENT 3 (2-3 lines): The peak — what they achieved or experienced. Their greatest moment.
This is the IMAGE BREAK segment. Make it visual. A scene worth painting.

SEGMENT 4 (2-3 lines): The fall or the departure. What went wrong, what was left unfinished.
Use Saturn's karmic debt and what Rahu says was missing.

SEGMENT 5 (2-3 lines): The thread to now. Why this soul chose THIS life.
What lesson carries forward. End with something that lands.

Rules:
- Each segment is 2-3 SHORT lines only. Not paragraphs — lines.
- Separate segments with exactly ---
- No headers, no labels, no "Segment 1:" text
- Write in second person ("You were...")
- Be specific, not generic. Use the astrological data.
- Total: under 200 words."""
