"""
MOBILE NUMBER — Numerological vibration of your phone number.

Calculates total vibration, individual digit influence,
compatibility with owner's birth numbers.

Called by: POST /mobile-number { mobile, kundli_data }
"""

from datetime import date
from typing import Dict


NUMBER_VIBES = {
    1: {'vibe': 'Leadership', 'planet': 'Sun', 'effect': 'Attracts authority and independent opportunities'},
    2: {'vibe': 'Partnership', 'planet': 'Moon', 'effect': 'Brings emotional connections and cooperative energy'},
    3: {'vibe': 'Expression', 'planet': 'Jupiter', 'effect': 'Attracts creativity, communication, and social growth'},
    4: {'vibe': 'Stability', 'planet': 'Rahu', 'effect': 'Brings structure but can attract unexpected disruptions'},
    5: {'vibe': 'Freedom', 'planet': 'Mercury', 'effect': 'Attracts change, travel, and dynamic opportunities'},
    6: {'vibe': 'Harmony', 'planet': 'Venus', 'effect': 'Brings love, beauty, and domestic comfort'},
    7: {'vibe': 'Intuition', 'planet': 'Ketu', 'effect': 'Attracts spiritual seekers but can isolate socially'},
    8: {'vibe': 'Power', 'planet': 'Saturn', 'effect': 'Brings material success but demands discipline and patience'},
    9: {'vibe': 'Compassion', 'planet': 'Mars', 'effect': 'Attracts humanitarian connections and global reach'},
}


def _reduce(n):
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def build_mobile_number(mobile: str, birth_date: date, language: str = 'en') -> Dict:
    """Analyze mobile number vibration."""

    from app.services.numerology.core import NumerologyEngine

    ne = NumerologyEngine(birth_date=birth_date)
    mulank = ne.get_mulank()
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank()
    if not isinstance(bhagyank, dict): bhagyank = {}

    owner_mulank = mulank.get('number', 0)
    owner_bhagyank = bhagyank.get('number', 0)
    compatible = mulank.get('compatible_numbers', [])

    # Clean mobile number
    digits = ''.join(c for c in mobile if c.isdigit())
    if not digits:
        return {'error': 'No valid digits in mobile number'}

    # Total vibration
    total = sum(int(d) for d in digits)
    root = _reduce(total)
    vibe_info = NUMBER_VIBES.get(root, {})

    # Digit frequency
    freq = {}
    for d in digits:
        n = int(d)
        freq[n] = freq.get(n, 0) + 1

    # Most repeated digit
    dominant_digit = max(freq, key=freq.get) if freq else 0
    dominant_count = freq.get(dominant_digit, 0)
    dominant_info = NUMBER_VIBES.get(dominant_digit if dominant_digit > 0 else 1, {})

    # Missing digits
    missing = [i for i in range(0, 10) if i not in freq]

    # Last digit (most impactful in phone numerology)
    last_digit = int(digits[-1]) if digits else 0
    last_info = NUMBER_VIBES.get(last_digit if last_digit > 0 else 9, {})

    # Compatibility
    ideal = [owner_mulank, owner_bhagyank] + compatible
    is_aligned = root in ideal
    power_numbers = [1, 3, 5, 6, 9]
    is_power = root in power_numbers

    if is_aligned and is_power:
        verdict = 'excellent'
    elif is_aligned:
        verdict = 'good'
    elif is_power:
        verdict = 'decent'
    elif root == 4 or root == 8:
        verdict = 'caution'
    else:
        verdict = 'neutral'

    briefing = f"""MOBILE NUMBER ANALYSIS

Number: {mobile} (digits: {digits})
Total: {total} → Root: {root}
Vibration: {vibe_info.get('vibe', '')} ({vibe_info.get('planet', '')})

OWNER: Mulank {owner_mulank} | Bhagyank {owner_bhagyank} | Compatible: {compatible}
Alignment: {'YES' if is_aligned else 'NO'} | Verdict: {verdict.upper()}

DIGIT FREQUENCY: {freq}
Dominant digit: {dominant_digit} (appears {dominant_count}x) — {dominant_info.get('vibe', '')}
Last digit: {last_digit} — {last_info.get('vibe', '')}
Missing: {missing}"""

    return {
        'mobile': mobile,
        'digits': digits,
        'total': total,
        'root': root,
        'vibe': vibe_info.get('vibe', ''),
        'planet': vibe_info.get('planet', ''),
        'effect': vibe_info.get('effect', ''),
        'dominant_digit': dominant_digit,
        'dominant_count': dominant_count,
        'dominant_vibe': dominant_info.get('vibe', ''),
        'last_digit': last_digit,
        'last_vibe': last_info.get('vibe', ''),
        'digit_freq': freq,
        'missing_digits': missing,
        'owner_mulank': owner_mulank,
        'owner_bhagyank': owner_bhagyank,
        'is_aligned': is_aligned,
        'verdict': verdict,
        'briefing': briefing,
    }


def build_mobile_prompt(data: Dict, language: str = 'en') -> str:
    briefing = data['briefing']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a numerologist analyzing a phone number — practical, warm, specific.{lang_note}

{briefing}

Write 4-5 sentences about how this mobile number affects the person:

1. The overall vibration ({data['root']}) and what energy it brings to every call and message.
2. The dominant digit ({data['dominant_digit']}, appears {data['dominant_count']} times) — what it amplifies.
3. The last digit ({data['last_digit']}) — this is the "first impression" people get when they see your number.
4. Whether this number is aligned with the owner's energy or working against it.
5. One specific suggestion if the number is weak.

Under 80 words. No jargon. Practical — how does this number affect their daily life?"""
