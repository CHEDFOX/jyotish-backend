"""
FIVE ELEMENTS WHEEL — Personal relationship with each element.

Production cycle: Wood → Fire → Earth → Metal → Water → Wood
For each: how much you carry, what it controls, need more/less, remedies.

Called by: POST /five-elements { kundli_data }
"""

from datetime import datetime
from typing import Dict

PRODUCTION_ORDER = ['Wood', 'Fire', 'Earth', 'Metal', 'Water']
GENERATES = {"Wood": "Fire", "Fire": "Earth", "Earth": "Metal", "Metal": "Water", "Water": "Wood"}
CONTROLS = {"Wood": "Earth", "Earth": "Water", "Water": "Fire", "Fire": "Metal", "Metal": "Wood"}
CONTROLLED_BY = {v: k for k, v in CONTROLS.items()}
GENERATED_BY = {v: k for k, v in GENERATES.items()}

ELEMENT_DATA = {
    'Wood': {
        'color': '#4A8C5C',
        'season': 'Spring',
        'direction': 'East',
        'organ': 'Liver, Gallbladder',
        'emotion': 'Anger',
        'virtue': 'Benevolence',
        'taste': 'Sour',
        'archetype': 'The Pioneer',
        'nature': 'Growth, flexibility, vision, planning',
        'remedies_excess': 'Reduce green in wardrobe, avoid sour foods, less planning more doing, spend time near Metal energy (white, west)',
        'remedies_deficit': 'Wear green, eat leafy greens, indoor plants, morning walks in nature, face east, wood furniture',
    },
    'Fire': {
        'color': '#CC4444',
        'season': 'Summer',
        'direction': 'South',
        'organ': 'Heart, Small Intestine',
        'emotion': 'Joy / Overexcitement',
        'virtue': 'Propriety',
        'taste': 'Bitter',
        'archetype': 'The Illuminator',
        'nature': 'Passion, charisma, warmth, expression',
        'remedies_excess': 'Cool colors (blue, black), reduce spicy food, less social media, water activities, meditation',
        'remedies_deficit': 'Wear red, candles, sunlight, warm lighting, south-facing spaces, social gatherings, cardio exercise',
    },
    'Earth': {
        'color': '#B8860B',
        'season': 'Late Summer',
        'direction': 'Center',
        'organ': 'Spleen, Stomach',
        'emotion': 'Worry',
        'virtue': 'Faithfulness',
        'taste': 'Sweet',
        'archetype': 'The Stabilizer',
        'nature': 'Stability, nurturing, grounding, reliability',
        'remedies_excess': 'Reduce sweet foods, less overthinking, movement over stillness, add Wood energy (green, growth)',
        'remedies_deficit': 'Wear yellow/brown, ceramics, gardening, root vegetables, square shapes, center your home',
    },
    'Metal': {
        'color': '#A0A0A0',
        'season': 'Autumn',
        'direction': 'West',
        'organ': 'Lungs, Large Intestine',
        'emotion': 'Grief',
        'virtue': 'Righteousness',
        'taste': 'Pungent',
        'archetype': 'The Refiner',
        'nature': 'Precision, discipline, letting go, clarity',
        'remedies_excess': 'Reduce white/metallic, less rigidity, add Fire energy (red, warmth), creative expression',
        'remedies_deficit': 'Wear white/silver, metal jewelry, declutter, breathwork, west-facing spaces, clear boundaries',
    },
    'Water': {
        'color': '#3366AA',
        'season': 'Winter',
        'direction': 'North',
        'organ': 'Kidneys, Bladder',
        'emotion': 'Fear',
        'virtue': 'Wisdom',
        'taste': 'Salty',
        'archetype': 'The Philosopher',
        'nature': 'Depth, wisdom, adaptability, introspection',
        'remedies_excess': 'Reduce black/blue, less isolation, add Earth energy (yellow, stability), structure and routine',
        'remedies_deficit': 'Wear black/blue, water features, swimming, north-facing spaces, rest, journal, reduce noise',
    },
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_five_elements(engine, language: str = 'en') -> Dict:
    """Build personal relationship with all 5 elements."""

    from app.services.chinese.bazi import BaZiChart
    from app.services.chinese.advanced import calculate_yong_shen

    bazi = BaZiChart(engine.birth_dt)

    # Element balance
    balance = bazi.get_element_balance()
    if not isinstance(balance, dict): balance = {}
    counts = balance.get('counts', {})
    if not isinstance(counts, dict): counts = {}
    dm_element = balance.get('day_master_element', '')
    dm_strength = 'Strong' if balance.get('strong', False) else 'Weak'
    total = sum(counts.values()) or 1

    # Yong Shen
    yong = _safe(lambda: calculate_yong_shen(dm_element, counts, dm_strength), {})
    if not isinstance(yong, dict): yong = {}
    yong_element = yong.get('yong_shen', '')
    ji_element = yong.get('ji_shen', '')

    # Day master
    dm = bazi.get_day_master()
    if not isinstance(dm, dict): dm = {}

    elements = []
    briefing_lines = [
        f"FIVE ELEMENTS for Day Master: {dm_element} ({dm_strength})",
        f"Yong Shen (needed): {yong_element} | Ji Shen (harmful): {ji_element}",
        f"Counts: {counts}\n",
    ]

    for elem in PRODUCTION_ORDER:
        count = counts.get(elem, 0)
        pct = round((count / total) * 100)
        data = ELEMENT_DATA[elem]

        # Relationship to day master
        if elem == dm_element:
            relation = 'self'
        elif GENERATES.get(elem) == dm_element:
            relation = 'resource'  # generates you
        elif GENERATES.get(dm_element) == elem:
            relation = 'output'  # you generate it
        elif CONTROLS.get(elem) == dm_element:
            relation = 'power'  # controls you
        elif CONTROLS.get(dm_element) == elem:
            relation = 'wealth'  # you control it
        else:
            relation = 'neutral'

        # Need assessment
        is_yong = elem == yong_element
        is_ji = elem == ji_element
        if is_yong:
            need = 'need more'
            remedy_type = 'deficit'
        elif is_ji:
            need = 'reduce'
            remedy_type = 'excess'
        elif pct >= 30:
            need = 'abundant'
            remedy_type = 'excess'
        elif pct <= 10:
            need = 'lacking'
            remedy_type = 'deficit'
        else:
            need = 'balanced'
            remedy_type = None

        remedy = ''
        if remedy_type == 'excess':
            remedy = data['remedies_excess']
        elif remedy_type == 'deficit':
            remedy = data['remedies_deficit']

        el = {
            'element': elem,
            'count': count,
            'percentage': pct,
            'color': data['color'],
            'season': data['season'],
            'direction': data['direction'],
            'organ': data['organ'],
            'emotion': data['emotion'],
            'virtue': data['virtue'],
            'archetype': data['archetype'],
            'nature': data['nature'],
            'relation': relation,
            'need': need,
            'is_yong_shen': is_yong,
            'is_ji_shen': is_ji,
            'remedy': remedy,
            'generates': GENERATES[elem],
            'controls': CONTROLS[elem],
            'generated_by': GENERATED_BY[elem],
            'controlled_by': CONTROLLED_BY[elem],
        }
        elements.append(el)

        briefing_lines.append(
            f"{elem} ({data['archetype']}): {count} ({pct}%) | relation: {relation} | need: {need} | {'★ YONG SHEN' if is_yong else '✗ JI SHEN' if is_ji else ''}"
        )

    return {
        'elements': elements,
        'day_master': dm_element,
        'dm_strength': dm_strength,
        'yong_shen': yong_element,
        'ji_shen': ji_element,
        'briefing': '\n'.join(briefing_lines),
    }


def build_element_prompt(element_data: Dict, all_data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for single element reading."""
    elem = element_data['element']
    briefing = all_data['briefing']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a Chinese metaphysics practitioner — warm, practical, wise.{lang_note}

{briefing}

ELEMENT: {elem} ({element_data['archetype']})
Count: {element_data['count']} ({element_data['percentage']}%)
Relation to Day Master: {element_data['relation']}
Assessment: {element_data['need']}
{'★ This is the YONG SHEN — the most needed element!' if element_data['is_yong_shen'] else ''}
{'✗ This is the JI SHEN — the harmful element.' if element_data['is_ji_shen'] else ''}
Nature: {element_data['nature']}
Organ: {element_data['organ']} | Emotion: {element_data['emotion']}
Generates: {element_data['generates']} | Controls: {element_data['controls']}

Write a short, practical reading (4-5 sentences):
1. How much of this element they carry and what that means practically.
2. The relationship — is this their fuel, their output, their challenge?
3. Whether they need more or less, and ONE specific daily remedy.
4. End with how this element connects to their emotional/health pattern.

Under 80 words. No jargon. Practical and warm."""
