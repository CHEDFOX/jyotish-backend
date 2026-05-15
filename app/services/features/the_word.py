"""
THE WORD — Quick KP yes/no on universal life topics.

Maps each topic to a KP house, runs cuspal sub-lord analysis,
returns yes/no/maybe + one-line LLM supporting text.

Endpoints:
  POST /api/public/the-word        run a reading
  GET  /api/public/the-word/topics list available topics
"""

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm,
)


router = APIRouter(prefix="/public", tags=["The Word"])


# Topic → KP house mapping. Category drives the supporting/negating house set
# from kp_horary's HORARY_EVENTS table.
TOPICS = {
    'love':         {'house': 7,  'category': 'love'},
    'money':        {'house': 2,  'category': 'wealth'},
    'travel':       {'house': 9,  'category': 'travel'},
    'health':       {'house': 1,  'category': 'health'},
    'career':       {'house': 10, 'category': 'career'},
    'marriage':     {'house': 7,  'category': 'marriage'},
    'children':     {'house': 5,  'category': 'children'},
    'fame':         {'house': 10, 'category': 'career'},
    'enemies':      {'house': 6,  'category': 'litigation'},
    'property':     {'house': 4,  'category': 'property'},
    'education':    {'house': 4,  'category': 'education'},
    'luck':         {'house': 9,  'category': 'general'},
    'friendship':   {'house': 11, 'category': 'general'},
    'spirituality': {'house': 12, 'category': 'general'},
    'secrets':      {'house': 8,  'category': 'general'},
    'inheritance':  {'house': 8,  'category': 'wealth'},
    'promotion':    {'house': 10, 'category': 'job_change'},
    'court_case':   {'house': 7,  'category': 'litigation'},
    'debt':         {'house': 6,  'category': 'wealth'},
    'foreign':      {'house': 12, 'category': 'travel'},
    'vehicle':      {'house': 4,  'category': 'property'},
    'surgery':      {'house': 8,  'category': 'health'},
    'business':     {'house': 7,  'category': 'business'},
    'passion':      {'house': 5,  'category': 'love'},
    'freedom':      {'house': 12, 'category': 'general'},
}


def build_the_word(engine, topic: str) -> Dict:
    topic_data = TOPICS.get(topic.lower())
    if not topic_data:
        return {'error': f'Unknown topic: {topic}', 'valid_topics': list(TOPICS.keys())}

    from app.services.kp.kp_complete import KPComplete
    from app.services.kp.kp_horary import HORARY_EVENTS

    kp = KPComplete(engine)
    house = topic_data['house']
    category = topic_data['category']

    fruit = kp.check_fruitfulness(house) or {}
    if not isinstance(fruit, dict): fruit = {}

    verdict_raw = fruit.get('fertility', 'Unknown')
    csl = fruit.get('cusp_sub_lord', '')
    csl_sign = fruit.get('csl_sign', '')

    cusps = kp.get_placidus_cusps() or {}
    if not isinstance(cusps, dict): cusps = {}
    cusp = cusps.get(house, {}) or {}
    if not isinstance(cusp, dict): cusp = {}

    sign = cusp.get('rashi_name', '')
    nak = cusp.get('nakshatra', '')

    csl_sig = safe(lambda: kp.get_planet_significators(csl), {}) or {} if csl else {}
    if not isinstance(csl_sig, dict): csl_sig = {}
    csl_houses = csl_sig.get('all_signified_houses', [])

    event_cfg = HORARY_EVENTS.get(category, HORARY_EVENTS.get('general', {}))
    supporting = set([house] + event_cfg.get('supporting', []))
    negating = set(event_cfg.get('negating', []))

    fav = set(csl_houses) & supporting
    unfav = set(csl_houses) & negating

    if verdict_raw == 'Fruitful' and len(fav) > len(unfav):
        answer = 'yes'
        confidence = min(80 + len(fav) * 5, 95)
    elif verdict_raw == 'Barren' or len(unfav) > len(fav):
        answer = 'no'
        confidence = min(70 + len(unfav) * 5, 90)
    elif len(fav) == len(unfav) and len(fav) > 0:
        answer = 'maybe'
        confidence = 50
    else:
        answer = 'maybe'
        confidence = 45

    return {
        'topic': topic,
        'category': category,
        'house': house,
        'sign': sign,
        'nakshatra': nak,
        'csl': csl,
        'csl_sign': csl_sign,
        'csl_signifies': sorted(csl_houses) if isinstance(csl_houses, (list, set)) else [],
        'favorable_houses': sorted(fav),
        'unfavorable_houses': sorted(unfav),
        'verdict_raw': verdict_raw,
        'answer': answer,
        'confidence': confidence,
    }


def build_word_prompt(data: Dict, language: str = 'en') -> str:
    return f"""{voice_card(language)}

You are giving a ONE-LINE oracle answer about a life topic.

TOPIC: {data['topic']}
KP analysis says: {data['answer'].upper()} ({data['confidence']}% confidence)
House {data['house']} ({data['sign']}), CSL: {data['csl']} in {data['csl_sign']}
CSL signifies houses: {data['csl_signifies']}
Favorable: {data['favorable_houses']} | Unfavorable: {data['unfavorable_houses']}

Write EXACTLY ONE sentence — 8 to 18 words — in the same voice as the rest of the app.
No house numbers. No planet names. No astrology jargon.
If yes: name what's coming and the energy around it.
If no: name the gentle redirect, what to do instead.
If maybe: name what's still shifting, what hasn't decided yet."""


class _WordRequest(BaseModel):
    topic: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.get('/the-word/topics')
async def list_topics():
    # Topic catalog — frontend uses keys to look up localized labels from /strings
    topics = [{'key': k, 'category': v['category'], 'house': v['house']} for k, v in TOPICS.items()]
    return {'topics': topics, 'count': len(topics), 'version': 1}


@router.post('/the-word')
async def get_the_word(request_body: _WordRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    if not request_body.topic or not request_body.topic.strip():
        raise HTTPException(status_code=400, detail='Topic required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        data = build_the_word(engine, request_body.topic.strip())
        if 'error' in data:
            raise HTTPException(status_code=400, detail=data['error'])

        prompt = build_word_prompt(data, language)
        line = await call_llm(prompt, settings,
                              user_message="The word, please.",
                              max_tokens=200, temperature=0.85)
        # Strip surrounding quotes if LLM wrapped it
        line = line.strip().strip('"').strip("'")

        return {
            **data,
            'line': line,
            'version': 1,
            'cache_ttl_seconds': 0,  # KP horary is moment-based
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


the_word_router = router
