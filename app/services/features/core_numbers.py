"""
CORE NUMBERS — All key numerology numbers in one reading.

Endpoint: POST /api/public/core-numbers
"""

from datetime import date, datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import extract_birth, call_llm


router = APIRouter(prefix="/public", tags=["Core Numbers"])


def build_core_numbers(birth_date: date, name: str = '') -> Dict:
    from app.services.numerology.core import NumerologyEngine

    ne = NumerologyEngine(name=name, birth_date=birth_date)

    mulank = ne.get_mulank() or {}
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank() or {}
    if not isinstance(bhagyank, dict): bhagyank = {}
    py = ne.get_personal_year() or {}
    if not isinstance(py, dict): py = {}
    pm = ne.get_personal_month() or {}
    if not isinstance(pm, dict): pm = {}
    pd = ne.get_personal_day() or {}
    if not isinstance(pd, dict): pd = {}
    lo_shu = ne.get_lo_shu_grid() or {}
    if not isinstance(lo_shu, dict): lo_shu = {}

    namank = {}
    if name:
        nm = ne.get_namank() or {}
        if isinstance(nm, dict):
            chal = nm.get('chaldean', {})
            if isinstance(chal, dict):
                namank = chal

    numbers = [
        {'key': 'mulank', 'label': 'Root Number',
         'number': mulank.get('number', 0), 'planet': mulank.get('planet', '')},
        {'key': 'bhagyank', 'label': 'Destiny Number',
         'number': bhagyank.get('number', 0), 'planet': bhagyank.get('planet', '')},
        {'key': 'personal_year', 'label': f'Personal Year {datetime.now().year}',
         'number': py.get('number', 0)},
        {'key': 'personal_month', 'label': 'Personal Month',
         'number': pm.get('number', 0)},
        {'key': 'personal_day', 'label': 'Today',
         'number': pd.get('number', 0)},
    ]

    if name and namank.get('root'):
        numbers.insert(2, {
            'key': 'namank', 'label': 'Name Number',
            'number': namank.get('root', 0), 'total': namank.get('total', 0),
        })

    return {
        'name': name,
        'birth_date': str(birth_date),
        'numbers': numbers,
        'missing_numbers': lo_shu.get('missing', []),
        'repeated_numbers': lo_shu.get('repeated', {}),
        'lo_shu_grid': lo_shu.get('grid', {}),
    }


def build_core_numbers_prompt(data: Dict, language: str = 'en') -> str:
    nums_text = '\n'.join([
        f"- {n['label']}: {n['number']}" + (f" ({n['planet']})" if n.get('planet') else '')
        for n in data['numbers']
    ])

    return f"""{voice_card(language)}

You are reading a person's complete numerology profile.

NUMBERS:
{nums_text}

Lo Shu missing numbers (gaps in their grid): {data['missing_numbers']}
Lo Shu repeated numbers (intensified): {data['repeated_numbers']}
Year: {datetime.now().year}

Write a FLOWING reading. 6-8 sentences. Cover:
- Root Number — what drives them daily
- Destiny Number — where life is pulling them
- How Root and Destiny work together or clash for THIS person
- Personal Year — what this year is really about
- Today — one line on the day's energy
- Lo Shu missing — what gaps to be aware of
- End with one surprising connection between their numbers

Under 130 words. Prose only — no headers, no bullets, no "1." labels.
Reference the actual numbers and their planets."""


class _CoreNumbersRequest(BaseModel):
    name: Optional[str] = ''
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/core-numbers')
async def get_core_numbers(request_body: _CoreNumbersRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        birth_date = date(birth_data['year'], birth_data['month'], birth_data['day'])
        language = request_body.language or 'en'
        name = (request_body.name or '').strip()

        data = build_core_numbers(birth_date, name)
        prompt = build_core_numbers_prompt(data, language)
        reading = await call_llm(prompt, settings,
                                 user_message="Read these numbers together.",
                                 max_tokens=800, temperature=0.8)

        return {**data, 'reading': reading, 'version': 1, 'cache_ttl_seconds': 86400}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


core_numbers_router = router
