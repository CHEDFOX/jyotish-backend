"""
NAME CORRECTION — Numerological name vibration analysis.

Checks name alignment with birth numbers (Mulank/Bhagyank).
Suggests corrections: added letters, removed letters, alternate spellings.
LLM writes about the changes and their effects.

Called by: POST /name-correction { name, kundli_data }
"""

from datetime import datetime, date
from typing import Dict


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_name_correction(name: str, birth_date: date, language: str = 'en') -> Dict:
    """Full name correction analysis."""

    from app.services.numerology.core import NumerologyEngine

    ne = NumerologyEngine(name=name, birth_date=birth_date)

    mulank = ne.get_mulank()
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank()
    if not isinstance(bhagyank, dict): bhagyank = {}
    namank = ne.get_namank()
    if not isinstance(namank, dict): namank = {}

    chaldean = namank.get('chaldean', {})
    if not isinstance(chaldean, dict): chaldean = {}
    pyth = namank.get('pythagorean', {})
    if not isinstance(pyth, dict): pyth = {}

    correction = ne.suggest_name_correction()
    if not isinstance(correction, dict): correction = {}

    needs_fix = correction.get('needs_correction', False)
    verdict = correction.get('verdict', '')
    suggestions = correction.get('suggestions', [])
    if not isinstance(suggestions, list): suggestions = []

    # Build briefing
    briefing = f"""NAME CORRECTION ANALYSIS

Name: {name}
Birth date: {birth_date}

MULANK (Root Number): {mulank.get('number', '?')} — {mulank.get('name', '')} (planet: {mulank.get('planet', '')})
BHAGYANK (Life Path): {bhagyank.get('number', '?')} — {bhagyank.get('name', '')} (planet: {bhagyank.get('planet', '')})

CURRENT NAME VIBRATION:
  Chaldean: {chaldean.get('total', '?')} → root {chaldean.get('root', '?')}
  Pythagorean: {pyth.get('total', '?')} → root {pyth.get('root', '?')}

VERDICT: {verdict}
NEEDS CORRECTION: {'YES' if needs_fix else 'NO'}

COMPATIBLE NUMBERS: {mulank.get('compatible_numbers', [])}

SUGGESTIONS ({len(suggestions)}):"""

    for i, s in enumerate(suggestions[:5]):
        if isinstance(s, dict):
            briefing += f"\n  {i+1}. \"{s.get('name', '')}\" → namank {s.get('namank', '?')} | change: {s.get('change', '')} | aligns with: {s.get('target', '')}"

    return {
        'name': name,
        'mulank': mulank.get('number', 0),
        'mulank_name': mulank.get('name', ''),
        'mulank_planet': mulank.get('planet', ''),
        'bhagyank': bhagyank.get('number', 0),
        'bhagyank_name': bhagyank.get('name', ''),
        'current_namank': chaldean.get('root', 0),
        'current_total': chaldean.get('total', 0),
        'needs_correction': needs_fix,
        'verdict': verdict,
        'suggestions': suggestions[:5],
        'compatible_numbers': mulank.get('compatible_numbers', []),
        'lucky_color': mulank.get('color', ''),
        'lucky_day': mulank.get('day', ''),
        'briefing': briefing,
    }


def build_name_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for name correction reading."""
    briefing = data['briefing']
    needs_fix = data['needs_correction']
    name = data['name']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    if needs_fix:
        return f"""You are a numerology expert — practical, clear, helpful.{lang_note}

{briefing}

The name "{name}" needs correction. Write a reading in 5-6 sentences:

1. Current name vibration number and why it's misaligned with birth numbers.
2. What this misalignment causes in daily life (be specific — energy, luck, opportunities).
3. The BEST suggested correction from the list — say the new spelling clearly.
4. What the corrected name number brings — how life shifts.
5. How to implement: start using it on signatures, social media, email, introductions.

Under 100 words. No jargon. Practical and warm. Don't list multiple options — pick the best one and recommend it clearly."""

    else:
        return f"""You are a numerology expert — practical, clear, reassuring.{lang_note}

{briefing}

The name "{name}" is already well-aligned! Write a reading in 4-5 sentences:

1. The current name vibration and why it works with their birth numbers.
2. What this alignment gives them — the energy it attracts.
3. One thing they can do to strengthen this vibration further.
4. A small insight about their name they might not know.

Under 80 words. Warm and affirming."""
