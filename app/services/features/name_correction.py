"""
NAME CORRECTION — Numerological alignment + spelling corrections.

Endpoint: POST /api/public/name-correction
"""

from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import extract_birth, call_llm


router = APIRouter(prefix="/public", tags=["Name Correction"])


def build_name_correction(name: str, birth_date: date) -> Dict:
    from app.services.numerology.core import NumerologyEngine

    ne = NumerologyEngine(name=name, birth_date=birth_date)

    mulank = ne.get_mulank() or {}
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank() or {}
    if not isinstance(bhagyank, dict): bhagyank = {}
    namank = ne.get_namank() or {}
    if not isinstance(namank, dict): namank = {}

    chaldean = namank.get('chaldean', {}) or {}
    if not isinstance(chaldean, dict): chaldean = {}

    correction = ne.suggest_name_correction() or {}
    if not isinstance(correction, dict): correction = {}

    needs_fix = correction.get('needs_correction', False)
    suggestions = correction.get('suggestions', [])
    if not isinstance(suggestions, list): suggestions = []

    return {
        'name': name,
        'mulank': mulank.get('number', 0),
        'mulank_planet': mulank.get('planet', ''),
        'bhagyank': bhagyank.get('number', 0),
        'bhagyank_planet': bhagyank.get('planet', ''),
        'current_namank': chaldean.get('root', 0),
        'current_total': chaldean.get('total', 0),
        'needs_correction': needs_fix,
        'compatible_numbers': mulank.get('compatible_numbers', []),
        'suggestions': suggestions[:5],
    }


def build_name_prompt(data: Dict, language: str = 'en') -> str:
    suggestions_text = '\n'.join([
        f"  - \"{s.get('name', '')}\" → namank {s.get('namank', '?')} | {s.get('change', '')}"
        for s in data['suggestions'] if isinstance(s, dict)
    ]) or '  (none)'

    if data['needs_correction']:
        task = f"""Write 5-6 sentences:
1. Current name vibration ({data['current_namank']}) — why it clashes with Mulank {data['mulank']} / Bhagyank {data['bhagyank']}.
2. What this misalignment shows up as in daily life (energy, recognition, flow).
3. Recommend ONE specific alternative spelling. Say it clearly.
4. What the corrected number brings — how life shifts.
5. How to use it: signature, social media, email, introductions.

Under 110 words. Pick the best — don't list options."""
    else:
        task = """Write 4-5 sentences:
1. Current vibration and why it works with their birth numbers.
2. What this alignment gives them in practical terms.
3. One way to amplify the vibration.
4. One small insight about their name they may not know.

Under 90 words. Warm, affirming."""

    return f"""{voice_card(language)}

You are reading a person's name numerology.

INDICATORS:
- Name: "{data['name']}"
- Mulank (Root): {data['mulank']} ({data['mulank_planet']})
- Bhagyank (Destiny): {data['bhagyank']} ({data['bhagyank_planet']})
- Current name vibration (Chaldean): {data['current_total']} → root {data['current_namank']}
- Owner's compatible numbers: {data['compatible_numbers']}
- Needs correction: {data['needs_correction']}

Spelling alternatives:
{suggestions_text}

{task}"""


class _NameRequest(BaseModel):
    name: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/name-correction')
async def get_name_correction(request_body: _NameRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    if not request_body.name or not request_body.name.strip():
        raise HTTPException(status_code=400, detail='Name required')

    try:
        birth_date = date(birth_data['year'], birth_data['month'], birth_data['day'])
        language = request_body.language or 'en'

        data = build_name_correction(request_body.name.strip(), birth_date)
        prompt = build_name_prompt(data, language)
        reading = await call_llm(prompt, settings,
                                 user_message=f"Read this name.",
                                 max_tokens=700, temperature=0.75)

        return {**data, 'reading': reading, 'version': 1, 'cache_ttl_seconds': 31536000}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


name_correction_router = router
