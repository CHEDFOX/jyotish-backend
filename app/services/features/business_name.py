"""
BUSINESS NAME — Numerological vibration check for business names.

Checks name vibration, alignment with owner's birth numbers,
suggests corrections or alternatives.

Called by: POST /business-name { business_name, kundli_data }
"""

from datetime import date
from typing import Dict


BUSINESS_LUCKY_NUMBERS = {
    1: {'vibe': 'Leadership, independence, innovation', 'best_for': 'Tech startups, consulting, personal brands'},
    2: {'vibe': 'Partnership, diplomacy, service', 'best_for': 'Agencies, healthcare, hospitality'},
    3: {'vibe': 'Creativity, communication, growth', 'best_for': 'Media, entertainment, marketing, education'},
    4: {'vibe': 'Structure, stability, trust', 'best_for': 'Construction, finance, law, manufacturing'},
    5: {'vibe': 'Change, freedom, versatility', 'best_for': 'Travel, e-commerce, food, adventure'},
    6: {'vibe': 'Nurturing, beauty, responsibility', 'best_for': 'Fashion, beauty, real estate, home services'},
    7: {'vibe': 'Research, depth, spirituality', 'best_for': 'Technology, research, spiritual services, analytics'},
    8: {'vibe': 'Power, wealth, authority', 'best_for': 'Finance, real estate, luxury brands, corporations'},
    9: {'vibe': 'Compassion, global reach, completion', 'best_for': 'NGOs, international business, publishing, healing'},
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_business_name(business_name: str, birth_date: date, language: str = 'en') -> Dict:
    """Analyze a business name numerologically."""

    from app.services.numerology.core import NumerologyEngine, _reduce_to_root, CHALDEAN

    ne = NumerologyEngine(name=business_name, birth_date=birth_date)

    # Owner's numbers
    mulank = ne.get_mulank()
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank()
    if not isinstance(bhagyank, dict): bhagyank = {}

    owner_mulank = mulank.get('number', 0)
    owner_bhagyank = bhagyank.get('number', 0)
    compatible = mulank.get('compatible_numbers', [])

    # Business name vibration
    namank = ne.get_namank()
    if not isinstance(namank, dict): namank = {}
    chaldean = namank.get('chaldean', {})
    if not isinstance(chaldean, dict): chaldean = {}
    pyth = namank.get('pythagorean', {})
    if not isinstance(pyth, dict): pyth = {}

    biz_number = chaldean.get('root', 0)
    biz_total = chaldean.get('total', 0)

    # Check alignment
    ideal_numbers = [owner_mulank, owner_bhagyank] + compatible
    # Also add universally strong business numbers
    power_numbers = [1, 3, 5, 6, 9]

    is_aligned = biz_number in ideal_numbers
    is_power = biz_number in power_numbers
    biz_info = BUSINESS_LUCKY_NUMBERS.get(biz_number, {})

    if is_aligned and is_power:
        verdict = 'excellent'
        verdict_text = 'Perfectly aligned with your energy and commercially powerful.'
    elif is_aligned:
        verdict = 'good'
        verdict_text = 'Aligned with your birth numbers. Supports your personal energy.'
    elif is_power:
        verdict = 'decent'
        verdict_text = 'Commercially strong number but not personally aligned with you.'
    else:
        verdict = 'weak'
        verdict_text = 'Neither aligned with you nor a commercially strong vibration.'

    # Generate suggestions if not excellent
    suggestions = []
    if verdict != 'excellent':
        for target in [owner_mulank, owner_bhagyank, 1, 5, 9]:
            if target == biz_number: continue
            diff = (target - biz_number) % 9
            if diff == 0: diff = 9

            for letter, value in sorted(CHALDEAN.items(), key=lambda x: x[1]):
                if value == diff:
                    new_name = business_name + letter
                    new_total = sum(CHALDEAN.get(c.lower(), 0) for c in new_name if c.isalpha())
                    new_root = _reduce_to_root(new_total)
                    if new_root in ideal_numbers or new_root in power_numbers:
                        new_info = BUSINESS_LUCKY_NUMBERS.get(new_root, {})
                        suggestions.append({
                            'name': new_name,
                            'number': new_root,
                            'vibe': new_info.get('vibe', ''),
                            'change': f'Added "{letter.upper()}"',
                        })
                    break
            if len(suggestions) >= 3: break

    briefing = f"""BUSINESS NAME ANALYSIS

Business: "{business_name}"
Owner born: {birth_date}

OWNER: Mulank {owner_mulank} | Bhagyank {owner_bhagyank}
Compatible: {compatible}

BUSINESS VIBRATION:
  Chaldean: {biz_total} → {biz_number}
  Vibe: {biz_info.get('vibe', '')}
  Best for: {biz_info.get('best_for', '')}

VERDICT: {verdict.upper()} — {verdict_text}

SUGGESTIONS: {len(suggestions)}"""

    for s in suggestions:
        briefing += f"\n  \"{s['name']}\" → {s['number']} ({s['vibe']})"

    return {
        'business_name': business_name,
        'biz_number': biz_number,
        'biz_total': biz_total,
        'biz_vibe': biz_info.get('vibe', ''),
        'biz_best_for': biz_info.get('best_for', ''),
        'owner_mulank': owner_mulank,
        'owner_bhagyank': owner_bhagyank,
        'verdict': verdict,
        'verdict_text': verdict_text,
        'is_aligned': is_aligned,
        'is_power': is_power,
        'suggestions': suggestions[:3],
        'briefing': briefing,
    }


def build_business_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for business name reading."""
    briefing = data['briefing']
    verdict = data['verdict']
    name = data['business_name']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a numerology expert for business names — practical, clear, commercially aware.{lang_note}

{briefing}

Write 4-5 sentences about this business name:

1. What vibration number {data['biz_number']} brings to a business — the energy clients feel.
2. Whether this aligns with the owner's personal energy ({data['owner_mulank']}/{data['owner_bhagyank']}).
3. {"The best correction from the suggestions — recommend ONE specific new spelling." if verdict in ('weak', 'decent') else "Why this name works and how to amplify its energy."}
4. One practical tip for using this name (logo, spelling, domain, signage).

Under 80 words. No jargon. Business-practical and warm."""
