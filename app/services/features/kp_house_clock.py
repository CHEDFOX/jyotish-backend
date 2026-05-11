"""
KP HOUSE CLOCK — 12 houses analyzed via KP cuspal sub-lord theory.

For each house:
  - Life Area: what the house governs
  - Verdict: fruitful / barren / semi-fruitful (cuspal sub-lord analysis)
  - Chain: sign-lord → nakshatra-lord → sub-lord → sub-sub-lord

Called by: POST /kp-house-clock { kundli_data }
"""

from datetime import datetime
from typing import Dict


HOUSE_LIFE_AREAS = {
    1:  {'area': 'Self', 'governs': 'Body, health, personality, vitality, first impression'},
    2:  {'area': 'Wealth', 'governs': 'Money, family, speech, food, early education'},
    3:  {'area': 'Courage', 'governs': 'Siblings, short travel, communication, hands, effort'},
    4:  {'area': 'Home', 'governs': 'Mother, property, vehicles, peace of mind, education'},
    5:  {'area': 'Creation', 'governs': 'Children, romance, intelligence, speculation, past merit'},
    6:  {'area': 'Struggle', 'governs': 'Enemies, disease, debts, service, daily work, pets'},
    7:  {'area': 'Partnership', 'governs': 'Spouse, business partner, open enemies, foreign travel'},
    8:  {'area': 'Transformation', 'governs': 'Death, inheritance, hidden things, research, surgery'},
    9:  {'area': 'Fortune', 'governs': 'Father, guru, luck, long travel, higher learning, dharma'},
    10: {'area': 'Career', 'governs': 'Profession, status, authority, government, public life'},
    11: {'area': 'Gains', 'governs': 'Income, friends, elder siblings, wishes fulfilled, networks'},
    12: {'area': 'Liberation', 'governs': 'Loss, expense, foreign settlement, spirituality, moksha'},
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_kp_house_clock(engine, language: str = 'en') -> Dict:
    """Build the 12-house KP clock data."""

    from app.services.kp.kp_complete import KPComplete
    kp = KPComplete(engine)

    cusps = kp.get_placidus_cusps()
    if not isinstance(cusps, dict):
        cusps = {}

    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    houses = []
    briefing_lines = ["KP HOUSE CLOCK\n"]

    for h in range(1, 13):
        cusp = cusps.get(h, {})
        if not isinstance(cusp, dict):
            cusp = {}

        sign = cusp.get('rashi_name', '')
        degree = cusp.get('degree_in_sign', 0)
        nak = cusp.get('nakshatra', '')
        nak_lord = cusp.get('nakshatra_lord', '')
        sub_lord = cusp.get('sub_lord', '')
        sub_sub_lord = cusp.get('sub_sub_lord', '')
        longitude = cusp.get('longitude', 0)

        # Sign lord (ruler of the sign on the cusp)
        sign_lord = _get_sign_lord(sign)

        # Fruitfulness check
        fruit = kp.check_fruitfulness(h)
        if not isinstance(fruit, dict):
            fruit = {}
        verdict = fruit.get('fertility', 'Unknown')
        verdict_detail = fruit.get('strength', '')
        csl = fruit.get('cusp_sub_lord', sub_lord)
        csl_sign = fruit.get('csl_sign', '')

        # Planets in this house
        occupants = []
        for pname, pdata in planets.items():
            if not isinstance(pdata, dict):
                continue
            if pdata.get('house') == h:
                occupants.append(pname)

        # Sub-lord significator chain
        # What houses does the cuspal sub-lord signify?
        csl_sig = {}
        if csl:
            csl_sig = _safe(lambda: kp.get_planet_significators(csl), {})
            if not isinstance(csl_sig, dict):
                csl_sig = {}

        csl_signified = csl_sig.get('all_signified_houses', [])

        # Is the sub-lord favorable for this house?
        # KP rule: if CSL signifies houses 6, 8, 12 from this house = unfavorable
        unfav_from_house = [(h + 5) % 12 or 12, (h + 7) % 12 or 12, (h + 11) % 12 or 12]
        fav_from_house = [h]  # The house itself is always favorable
        # Add trikona and kendra from this house
        fav_from_house.extend([(h + 4) % 12 or 12, (h + 8) % 12 or 12])  # 5th and 9th from house

        unfav_count = len(set(csl_signified) & set(unfav_from_house))
        fav_count = len(set(csl_signified) & set(fav_from_house))

        if verdict == 'Fruitful' and fav_count > unfav_count:
            strength = 'strong'
        elif verdict == 'Barren' or unfav_count > fav_count:
            strength = 'weak'
        else:
            strength = 'moderate'

        life = HOUSE_LIFE_AREAS.get(h, {})

        house_data = {
            'house': h,
            'area': life.get('area', ''),
            'governs': life.get('governs', ''),
            'sign': sign,
            'degree': degree,
            'nakshatra': nak,
            'chain': {
                'sign_lord': sign_lord,
                'nakshatra_lord': nak_lord,
                'sub_lord': sub_lord,
                'sub_sub_lord': sub_sub_lord,
            },
            'verdict': verdict,
            'verdict_detail': verdict_detail,
            'strength': strength,
            'csl': csl,
            'csl_sign': csl_sign,
            'csl_signified_houses': csl_signified,
            'occupants': occupants,
        }
        houses.append(house_data)

        briefing_lines.append(
            f"H{h} ({life.get('area','')}) — {sign} {degree}° | CSL: {csl} | {verdict} ({strength}) | occupants: {', '.join(occupants) if occupants else 'none'}"
        )

    return {
        'houses': houses,
        'briefing': '\n'.join(briefing_lines),
    }


def build_house_prompt(house_data: Dict, all_houses: list, language: str = 'en') -> str:
    """Build LLM prompt for a single house reading."""
    h = house_data['house']
    area = house_data['area']
    chain = house_data['chain']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a KP astrology expert — precise, analytical, warm.{lang_note}

HOUSE {h}: {area}
Sign: {house_data['sign']} at {house_data['degree']}°
Nakshatra: {house_data['nakshatra']}
Chain: {chain['sign_lord']} → {chain['nakshatra_lord']} → {chain['sub_lord']} → {chain['sub_sub_lord']}
Cuspal Sub-Lord: {house_data['csl']} in {house_data['csl_sign']}
Verdict: {house_data['verdict']} ({house_data['strength']})
CSL signifies houses: {house_data['csl_signified_houses']}
Occupants: {', '.join(house_data['occupants']) if house_data['occupants'] else 'None'}
Governs: {house_data['governs']}

Write 3 short pieces:

1. LIFE AREA (1 sentence): What this house means for them — specific to the sign on the cusp.

2. VERDICT (1 sentence): Is this house delivering? Based on the CSL analysis — be honest. Fruitful, barren, or mixed.

3. INSIGHT (2 sentences): What the sub-lord chain reveals. Reference the chain specifically. One practical takeaway.

Separate with ---
No labels, no headers. Just the three pieces.
Total: under 80 words. Precise, not poetic."""


SIGN_LORDS = {
    'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury',
    'Cancer': 'Moon', 'Leo': 'Sun', 'Virgo': 'Mercury',
    'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter',
    'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter',
}

def _get_sign_lord(sign_name):
    return SIGN_LORDS.get(sign_name, '')
