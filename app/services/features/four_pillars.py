"""
FOUR PILLARS — Kama · Karma · Dharma · Moksha

The four aims of the soul, read from the birth chart.

Kama (desire):  7th house, Venus, 3rd/7th/11th houses (kama trikona)
Karma (action):  10th house, Saturn, Mars, career indicators
Dharma (purpose): 9th house, Jupiter, 1st/5th/9th houses (dharma trikona)
Moksha (liberation): 12th house, Ketu, 4th/8th/12th houses (moksha trikona)

Called by: POST /four-pillars { kundli_data }
"""

from datetime import datetime
from typing import Dict


PILLAR_META = {
    'kama': {
        'title': 'Kama',
        'meaning': 'Desire',
        'houses': [3, 7, 11],
        'karaka': 'Venus',
        'question': 'What does your soul desire?',
    },
    'karma': {
        'title': 'Karma',
        'meaning': 'Action',
        'houses': [2, 6, 10],
        'karaka': 'Saturn',
        'question': 'What is your destined work?',
    },
    'dharma': {
        'title': 'Dharma',
        'meaning': 'Purpose',
        'houses': [1, 5, 9],
        'karaka': 'Jupiter',
        'question': 'Why are you here?',
    },
    'moksha': {
        'title': 'Moksha',
        'meaning': 'Liberation',
        'houses': [4, 8, 12],
        'karaka': 'Ketu',
        'question': 'How will you be free?',
    },
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


def build_four_pillars(engine, language: str = 'en') -> Dict:
    """Build the four life pillars from chart data."""

    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    # Dignity data
    dignity_data = _safe(engine.get_planetary_dignity, {})
    if not isinstance(dignity_data, dict): dignity_data = {}
    house_lords = dignity_data.get('house_lords', {})
    if not isinstance(house_lords, dict): house_lords = {}

    # Yoga data
    yoga_data = _safe(engine.get_yogas, {})
    if not isinstance(yoga_data, dict): yoga_data = {}
    all_yogas = yoga_data.get('yogas', [])
    if not isinstance(all_yogas, list): all_yogas = []

    # Shadbala
    sb_data = _safe(engine.get_shadbala_complete, {})
    if not isinstance(sb_data, dict): sb_data = {}
    sb_planets = sb_data.get('planets', {})
    if not isinstance(sb_planets, dict): sb_planets = {}

    # Ascendant
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    asc_sign = asc.get('rashi_name', '')

    pillars = {}
    briefing_lines = [f"FOUR PILLARS for {asc_sign} ascendant\n"]

    for key, meta in PILLAR_META.items():
        karaka_name = meta['karaka']
        karaka = _pl(planets, karaka_name)
        karaka_sign = karaka.get('rashi_name', '')
        karaka_house = karaka.get('house', 0)
        karaka_nak = karaka.get('nakshatra_name', '')

        # Karaka strength
        sb_k = sb_planets.get(karaka_name, {})
        if not isinstance(sb_k, dict): sb_k = {}
        karaka_strength = sb_k.get('percentage', 50)
        karaka_grade = sb_k.get('grade', 'Average')

        # Karaka dignity
        dg_k = dignity_data.get('planets', {})
        if not isinstance(dg_k, dict): dg_k = {}
        dg_planet = dg_k.get(karaka_name, {})
        if not isinstance(dg_planet, dict): dg_planet = {}
        karaka_dignity = dg_planet.get('dignity_type', '')

        # Planets in pillar houses
        house_planets = {}
        for h in meta['houses']:
            h_planets = []
            for pname, pdata in planets.items():
                if not isinstance(pdata, dict): continue
                if pdata.get('house') == h:
                    h_planets.append(pname)
            house_planets[h] = h_planets

        # House lords
        h_lords = {}
        for h in meta['houses']:
            lord = house_lords.get(str(h), house_lords.get(h, ''))
            h_lords[h] = lord

        # Relevant yogas
        pillar_yogas = []
        pillar_planet_names = set()
        for h in meta['houses']:
            pillar_planet_names.update(house_planets.get(h, []))
        pillar_planet_names.add(karaka_name)

        for y in all_yogas:
            if not isinstance(y, dict): continue
            yp = y.get('planets', [])
            if isinstance(yp, str): yp = [yp]
            if not isinstance(yp, list): continue
            if any(p in pillar_planet_names for p in yp):
                pillar_yogas.append(y.get('name', ''))

        # Key house (primary)
        primary_house = meta['houses'][-1]  # 11 for kama, 10 for karma, 9 for dharma, 12 for moksha
        if key == 'kama': primary_house = 7
        elif key == 'karma': primary_house = 10
        elif key == 'dharma': primary_house = 9
        elif key == 'moksha': primary_house = 12

        primary_lord = house_lords.get(str(primary_house), house_lords.get(primary_house, ''))
        primary_planets = house_planets.get(primary_house, [])

        pillar = {
            'key': key,
            'title': meta['title'],
            'meaning': meta['meaning'],
            'question': meta['question'],
            'karaka': {
                'planet': karaka_name,
                'sign': karaka_sign,
                'house': karaka_house,
                'nakshatra': karaka_nak,
                'strength': karaka_strength,
                'grade': karaka_grade,
                'dignity': karaka_dignity,
            },
            'primary_house': primary_house,
            'primary_lord': primary_lord,
            'primary_planets': primary_planets,
            'house_lords': h_lords,
            'house_planets': house_planets,
            'yogas': pillar_yogas[:4],
        }
        pillars[key] = pillar

        # Briefing
        briefing_lines.append(f"═══ {meta['title'].upper()} ({meta['meaning']}) ═══")
        briefing_lines.append(f"Karaka: {karaka_name} in {karaka_sign} H{karaka_house} ({karaka_nak}) — {karaka_strength}% {karaka_grade}")
        briefing_lines.append(f"Primary house: H{primary_house} lord={primary_lord} planets={', '.join(primary_planets) if primary_planets else 'empty'}")
        for h in meta['houses']:
            hp = house_planets.get(h, [])
            hl = h_lords.get(h, '')
            briefing_lines.append(f"  H{h}: lord={hl} occupants={', '.join(hp) if hp else 'none'}")
        if pillar_yogas:
            briefing_lines.append(f"Yogas: {', '.join(pillar_yogas[:3])}")
        briefing_lines.append('')

    return {
        'pillars': pillars,
        'ascendant': asc_sign,
        'briefing': '\n'.join(briefing_lines),
    }


def build_pillars_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for four pillars reading."""
    briefing = data['briefing']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are the voice of the stars — ancient, warm, mystical, true.{lang_note}

{briefing}

For each of the FOUR PILLARS, provide exactly this format:

KAMA
word: [ONE word that captures their desire nature]
note: [2 sentences — what they truly desire and how it manifests. Be specific to the chart data.]

KARMA
word: [ONE word that captures their action/work nature]
note: [2 sentences — what work they are destined for. Reference the 10th house and Saturn.]

DHARMA
word: [ONE word that captures their life purpose]
note: [2 sentences — why this soul is here. Reference the 9th house and Jupiter.]

MOKSHA
word: [ONE word that captures their path to freedom]
note: [2 sentences — how they will find liberation. Reference the 12th house and Ketu.]

CLOSING
[One powerful closing line — a single sentence that ties all four pillars together for this specific person. Make it land. Make it memorable.]

Rules:
- The "word" must be ONE word only — evocative, specific, not generic
- The "note" is exactly 2 sentences, warm but precise
- Reference actual chart placements (signs, houses)
- Total: under 250 words"""
