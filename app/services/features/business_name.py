"""
BUSINESS NAME — Numerological vibration check.

Endpoint: POST /api/public/business-name
"""

from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import extract_birth, call_llm


router = APIRouter(prefix="/public", tags=["Business Name"])


def build_business_name(business_name: str, birth_date: date) -> Dict:
    from app.services.numerology.core import NumerologyEngine, _reduce_to_root, CHALDEAN

    ne = NumerologyEngine(name=business_name, birth_date=birth_date)

    mulank = ne.get_mulank() or {}
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank() or {}
    if not isinstance(bhagyank, dict): bhagyank = {}

    owner_mulank = mulank.get('number', 0)
    owner_bhagyank = bhagyank.get('number', 0)
    compatible = mulank.get('compatible_numbers', [])

    namank = ne.get_namank() or {}
    if not isinstance(namank, dict): namank = {}
    chaldean = namank.get('chaldean', {}) or {}
    if not isinstance(chaldean, dict): chaldean = {}

    biz_number = chaldean.get('root', 0)
    biz_total = chaldean.get('total', 0)

    ideal = [owner_mulank, owner_bhagyank] + (compatible if isinstance(compatible, list) else [])
    power_numbers = [1, 3, 5, 6, 9]
    is_aligned = biz_number in ideal
    is_power = biz_number in power_numbers

    if is_aligned and is_power:
        verdict = 'excellent'
    elif is_aligned:
        verdict = 'good'
    elif is_power:
        verdict = 'decent'
    else:
        verdict = 'weak'

    suggestions = []
    if verdict != 'excellent':
        for target in [owner_mulank, owner_bhagyank, 1, 5, 9]:
            if target == biz_number:
                continue
            diff = (target - biz_number) % 9
            if diff == 0:
                diff = 9
            for letter, value in sorted(CHALDEAN.items(), key=lambda x: x[1]):
                if value == diff:
                    new_name = business_name + letter
                    new_total = sum(CHALDEAN.get(c.lower(), 0) for c in new_name if c.isalpha())
                    new_root = _reduce_to_root(new_total)
                    if new_root in ideal or new_root in power_numbers:
                        suggestions.append({
                            'name': new_name,
                            'number': new_root,
                            'change': f'Added "{letter.upper()}"',
                        })
                    break
            if len(suggestions) >= 3:
                break

    return {
        'business_name': business_name,
        'biz_number': biz_number,
        'biz_total': biz_total,
        'owner_mulank': owner_mulank,
        'owner_bhagyank': owner_bhagyank,
        'compatible_numbers': compatible,
        'is_aligned': is_aligned,
        'is_power': is_power,
        'verdict': verdict,
        'suggestions': suggestions[:3],
    }


def build_business_prompt(data: Dict, language: str = 'en') -> str:
    suggestions_text = '\n'.join([
        f"  - \"{s['name']}\" → number {s['number']} ({s['change']})"
        for s in data['suggestions']
    ]) or '  (none — current name is aligned)'

    closing = ('Recommend ONE specific alternative spelling and what changes if they switch to it.'
               if data['verdict'] in ('weak', 'decent')
               else 'Explain why this name works and one way to amplify it.')

    return f"""{voice_card(language)}

You are reading a business name's numerology.

INDICATORS:
- Business name: "{data['business_name']}"
- Business number (Chaldean): {data['biz_total']} → {data['biz_number']}
- Owner Mulank (Root): {data['owner_mulank']}
- Owner Bhagyank (Destiny): {data['owner_bhagyank']}
- Compatible numbers for owner: {data['compatible_numbers']}
- Aligned with owner: {data['is_aligned']}
- Commercially power number: {data['is_power']}
- Verdict: {data['verdict']}

Spelling alternatives that would shift the number:
{suggestions_text}

Write 4-5 sentences:
1. What energy number {data['biz_number']} brings to a business — what clients/customers feel.
2. Whether this aligns with the owner ({data['owner_mulank']}/{data['owner_bhagyank']}) — what that means in practice.
3. {closing}
4. One practical step: logo, domain, signage, or signature.

Under 90 words. Commercial-practical. Warm. No jargon."""


class _BusinessNameRequest(BaseModel):
    business_name: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/business-name')
async def get_business_name(request_body: _BusinessNameRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    if not request_body.business_name or not request_body.business_name.strip():
        raise HTTPException(status_code=400, detail='Business name required')

    try:
        birth_date = date(birth_data['year'], birth_data['month'], birth_data['day'])
        language = request_body.language or 'en'

        data = build_business_name(request_body.business_name.strip(), birth_date)
        prompt = build_business_prompt(data, language)
        reading = await call_llm(prompt, settings,
                                 user_message=f"Read this business name.",
                                 max_tokens=600, temperature=0.75)

        return {**data, 'reading': reading, 'version': 1, 'cache_ttl_seconds': 31536000}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


business_name_router = router
