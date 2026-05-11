"""
KP HORARY — Number-based instant prediction.

User thinks of a number 1-249.
Backend: number → zodiac degree → horary chart → prediction.
LLM writes a short, jargon-free insight.

Called by: POST /kp-horary { number, question, kundli_data }
"""

from datetime import datetime
from typing import Dict, Optional


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_kp_horary(number: int, question: str = '', category: str = 'general',
                     latitude: float = 25.35, longitude: float = 74.64) -> Dict:
    """Run KP horary analysis for the given number."""

    from app.services.kp.kp_horary import KPHorary, get_sub_entry

    # Number to zodiac entry
    entry = get_sub_entry(number)

    # Run full horary analysis
    kp = KPHorary(
        number=number,
        question=question,
        category=category,
        latitude=latitude,
        longitude=longitude,
    )
    result = kp.analyze()
    if not isinstance(result, dict):
        result = {}

    # Ruling planets
    rp = result.get('ruling_planets', {})
    if not isinstance(rp, dict):
        rp = {}

    # Cusps summary
    cusps = result.get('cusps', {})
    if not isinstance(cusps, dict):
        cusps = {}

    # Find dominant house — the house most signified by ruling planets
    house_scores = {}
    for i in range(1, 13):
        house_scores[i] = 0
    # CSL house gets primary weight
    csl_house = result.get('csl_house', 0)
    if csl_house:
        house_scores[csl_house] = house_scores.get(csl_house, 0) + 3

    # Primary house gets weight
    primary = result.get('primary_house', 1)
    house_scores[primary] = house_scores.get(primary, 0) + 2

    dominant_house = max(house_scores, key=house_scores.get) if house_scores else 1

    # Ascendant from number
    asc = result.get('ascendant', {})
    if not isinstance(asc, dict):
        asc = {}

    # Build briefing
    verdict = result.get('verdict', 'Uncertain')
    confidence = result.get('confidence_pct', 50)
    reasoning = result.get('reasoning', '')
    csl = result.get('cusp_sub_lord', '')

    rp_summary = []
    for key in ['day_lord', 'moon_sign_lord', 'moon_star_lord', 'asc_sign_lord', 'asc_star_lord']:
        val = rp.get(key, '')
        if val:
            rp_summary.append(f"{key}: {val}")

    briefing = f"""KP HORARY — Number {number}
Question: {question or 'General reading'}
Category: {category}

ASCENDANT (from number): {asc.get('sign', '')} / {asc.get('star', '')} / {asc.get('sub', '')}
Primary house: H{primary}
Cuspal Sub-Lord (CSL): {csl} in H{csl_house}

VERDICT: {verdict} ({confidence}% confidence)
Reason: {reasoning}

Dominant house: H{dominant_house}
Ruling planets: {', '.join(rp_summary)}

Time of query: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"""

    return {
        'number': number,
        'question': question or '',
        'category': category,
        'ascendant': asc,
        'primary_house': primary,
        'csl': csl,
        'csl_house': csl_house,
        'verdict': verdict,
        'confidence': confidence,
        'reasoning': reasoning,
        'dominant_house': dominant_house,
        'ruling_planets': rp,
        'entry': {
            'sign': entry.get('sign', ''),
            'star': entry.get('star', ''),
            'sub_lord': entry.get('sub_lord', ''),
            'degree': round(entry.get('start_deg', 0), 2),
        },
        'briefing': briefing,
    }


def build_horary_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for horary reading — jargon-free."""
    briefing = data['briefing']
    verdict = data['verdict']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a wise, warm oracle. Someone just asked the universe a question by picking a number.{lang_note}

{briefing}

Write a SHORT, INTERESTING response. 3-4 sentences maximum.

Rules:
- NO astrological jargon. No "cuspal sub-lord", no "H7", no "significator".
  Write as if speaking to someone who knows nothing about astrology.
- The verdict is {verdict}. Deliver it with warmth, not clinical coldness.
- If YES: tell them what's coming and when to act.
- If NO: tell them why the timing isn't right and what to do instead.
- If uncertain: tell them what the universe is still deciding about.
- End with one surprising or memorable insight — something they'll remember.

Under 60 words. No headers, no bullets. Just speak."""
