"""
MOBILE NUMBER — Numerological vibration of a phone number.

Endpoint: POST /api/public/mobile-number
"""

from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import extract_birth, call_llm


router = APIRouter(prefix="/public", tags=["Mobile Number"])


def _reduce(n):
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def build_mobile_number(mobile: str, birth_date: date) -> Dict:
    from app.services.numerology.core import NumerologyEngine

    ne = NumerologyEngine(birth_date=birth_date)
    mulank = ne.get_mulank() or {}
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank() or {}
    if not isinstance(bhagyank, dict): bhagyank = {}

    owner_mulank = mulank.get('number', 0)
    owner_bhagyank = bhagyank.get('number', 0)
    compatible = mulank.get('compatible_numbers', [])

    digits = ''.join(c for c in mobile if c.isdigit())
    if not digits:
        return {'error': 'No valid digits'}

    total = sum(int(d) for d in digits)
    root = _reduce(total)

    freq = {}
    for d in digits:
        n = int(d)
        freq[n] = freq.get(n, 0) + 1

    dominant_digit = max(freq, key=freq.get) if freq else 0
    dominant_count = freq.get(dominant_digit, 0)
    missing = [i for i in range(10) if i not in freq]
    last_digit = int(digits[-1])

    ideal = [owner_mulank, owner_bhagyank] + (compatible if isinstance(compatible, list) else [])
    power_numbers = [1, 3, 5, 6, 9]
    is_aligned = root in ideal
    is_power = root in power_numbers

    if is_aligned and is_power:
        verdict = 'excellent'
    elif is_aligned:
        verdict = 'good'
    elif is_power:
        verdict = 'decent'
    elif root in (4, 8):
        verdict = 'caution'
    else:
        verdict = 'neutral'

    return {
        'mobile': mobile,
        'digits': digits,
        'total': total,
        'root': root,
        'dominant_digit': dominant_digit,
        'dominant_count': dominant_count,
        'last_digit': last_digit,
        'digit_freq': freq,
        'missing_digits': missing,
        'owner_mulank': owner_mulank,
        'owner_bhagyank': owner_bhagyank,
        'compatible_numbers': compatible,
        'is_aligned': is_aligned,
        'is_power': is_power,
        'verdict': verdict,
    }


def build_mobile_prompt(data: Dict, language: str = 'en') -> str:
    closing = ('Give one concrete fix if the number is misaligned.'
               if data['verdict'] in ('weak', 'caution', 'neutral')
               else 'Suggest one way to use this number to its full potential.')

    return f"""{voice_card(language)}

You are reading a mobile phone number's numerology.

INDICATORS:
- Mobile: {data['mobile']}
- All digits summed: {data['total']} → root {data['root']}
- Dominant digit (most repeated): {data['dominant_digit']}, appears {data['dominant_count']} times
- Last digit (the impression people feel when they see this number): {data['last_digit']}
- Missing digits in the number: {data['missing_digits']}
- Owner Mulank: {data['owner_mulank']} | Bhagyank: {data['owner_bhagyank']}
- Aligned with owner: {data['is_aligned']}
- Verdict: {data['verdict']}

Write 4-5 sentences:
1. Energy the root number ({data['root']}) brings to every call, message, connection.
2. The dominant digit ({data['dominant_digit']}) — what it amplifies in their daily phone use.
3. The last digit ({data['last_digit']}) — first impression a person gets when they see this number.
4. Whether the number is working with the owner or against them. Be specific.
5. {closing}

Under 90 words. Practical — how does this number affect their actual daily life?"""


class _MobileRequest(BaseModel):
    mobile: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/mobile-number')
async def get_mobile_number(request_body: _MobileRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    if not request_body.mobile or not request_body.mobile.strip():
        raise HTTPException(status_code=400, detail='Mobile number required')

    try:
        birth_date = date(birth_data['year'], birth_data['month'], birth_data['day'])
        language = request_body.language or 'en'

        data = build_mobile_number(request_body.mobile.strip(), birth_date)
        if 'error' in data:
            raise HTTPException(status_code=400, detail=data['error'])

        prompt = build_mobile_prompt(data, language)
        reading = await call_llm(prompt, settings,
                                 user_message="Read this mobile number.",
                                 max_tokens=600, temperature=0.75)

        return {**data, 'reading': reading, 'version': 1, 'cache_ttl_seconds': 2592000}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


mobile_number_router = router
