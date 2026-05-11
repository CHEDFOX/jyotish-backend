"""
THE WORD — Quick KP yes/no on universal life topics.

Maps each topic to a KP house, runs cuspal sub-lord analysis,
returns yes/no with a short supporting line.

Called by: POST /the-word { topic, kundli_data }
"""

from datetime import datetime
from typing import Dict


# 25 universal human topics → mapped to KP houses
TOPICS = {
    'love':         {'house': 7, 'question': 'Is love coming?', 'category': 'love'},
    'money':        {'house': 2, 'question': 'Will wealth grow?', 'category': 'wealth'},
    'travel':       {'house': 9, 'question': 'Is travel ahead?', 'category': 'travel'},
    'health':       {'house': 1, 'question': 'Is health improving?', 'category': 'health'},
    'career':       {'house': 10, 'question': 'Will career rise?', 'category': 'career'},
    'marriage':     {'house': 7, 'question': 'Is marriage destined?', 'category': 'marriage'},
    'children':     {'house': 5, 'question': 'Are children in the stars?', 'category': 'children'},
    'fame':         {'house': 10, 'question': 'Will recognition come?', 'category': 'career'},
    'enemies':      {'house': 6, 'question': 'Will enemies trouble?', 'category': 'litigation'},
    'property':     {'house': 4, 'question': 'Will you own property?', 'category': 'property'},
    'education':    {'house': 4, 'question': 'Will education succeed?', 'category': 'education'},
    'luck':         {'house': 9, 'question': 'Is luck on your side?', 'category': 'general'},
    'friendship':   {'house': 11, 'question': 'Are true friends near?', 'category': 'general'},
    'spirituality': {'house': 12, 'question': 'Is awakening close?', 'category': 'general'},
    'secrets':      {'house': 8, 'question': 'Will secrets surface?', 'category': 'general'},
    'inheritance':  {'house': 8, 'question': 'Is inheritance likely?', 'category': 'wealth'},
    'promotion':    {'house': 10, 'question': 'Is promotion near?', 'category': 'job_change'},
    'court case':   {'house': 7, 'question': 'Will you win the case?', 'category': 'litigation'},
    'debt':         {'house': 6, 'question': 'Will debts clear?', 'category': 'wealth'},
    'foreign':      {'house': 12, 'question': 'Will you go abroad?', 'category': 'travel'},
    'vehicle':      {'house': 4, 'question': 'Will you get a vehicle?', 'category': 'property'},
    'surgery':      {'house': 8, 'question': 'Is surgery needed?', 'category': 'health'},
    'business':     {'house': 7, 'question': 'Will business succeed?', 'category': 'business'},
    'passion':      {'house': 5, 'question': 'Will passion ignite?', 'category': 'love'},
    'freedom':      {'house': 12, 'question': 'Will you find freedom?', 'category': 'general'},
}

def get_all_topics():
    return list(TOPICS.keys())


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_the_word(engine, topic: str, language: str = 'en') -> Dict:
    """Run KP analysis for a single topic."""

    topic_data = TOPICS.get(topic.lower())
    if not topic_data:
        return {'error': f'Unknown topic: {topic}', 'valid_topics': list(TOPICS.keys())}

    from app.services.kp.kp_complete import KPComplete
    kp = KPComplete(engine)

    house = topic_data['house']
    category = topic_data['category']
    question = topic_data['question']

    # Fruitfulness of the house
    fruit = kp.check_fruitfulness(house)
    if not isinstance(fruit, dict):
        fruit = {}

    verdict_raw = fruit.get('fertility', 'Unknown')
    csl = fruit.get('cusp_sub_lord', '')
    csl_sign = fruit.get('csl_sign', '')

    # Get cusps for chain
    cusps = kp.get_placidus_cusps()
    if not isinstance(cusps, dict):
        cusps = {}
    cusp = cusps.get(house, {})
    if not isinstance(cusp, dict):
        cusp = {}

    sign = cusp.get('rashi_name', '')
    nak = cusp.get('nakshatra', '')
    sub_lord = cusp.get('sub_lord', '')

    # CSL significator check
    csl_sig = {}
    if csl:
        csl_sig = _safe(lambda: kp.get_planet_significators(csl), {})
        if not isinstance(csl_sig, dict):
            csl_sig = {}

    csl_houses = csl_sig.get('all_signified_houses', [])

    # Supporting / negating houses for this category
    from app.services.kp.kp_horary import HORARY_EVENTS
    event_cfg = HORARY_EVENTS.get(category, HORARY_EVENTS['general'])
    supporting = set([house] + event_cfg.get('supporting', []))
    negating = set(event_cfg.get('negating', []))

    fav = set(csl_houses) & supporting
    unfav = set(csl_houses) & negating

    # Determine yes/no
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

    # Ruling planets
    rp = _safe(lambda: kp.get_ruling_planets(), {})
    if not isinstance(rp, dict):
        rp = {}

    briefing = f"""TOPIC: {topic} — "{question}"
House: H{house} | Sign: {sign} | CSL: {csl} in {csl_sign}
Verdict: {verdict_raw} | Answer: {answer.upper()} ({confidence}%)
CSL signifies: {csl_houses}
Favorable: {sorted(fav)} | Unfavorable: {sorted(unfav)}"""

    return {
        'topic': topic,
        'question': question,
        'house': house,
        'sign': sign,
        'csl': csl,
        'answer': answer,
        'confidence': confidence,
        'briefing': briefing,
    }


def build_word_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for a one-line supporting text."""
    briefing = data['briefing']
    answer = data['answer']
    topic = data['topic']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a wise oracle giving a ONE-LINE answer.{lang_note}

{briefing}

The answer is {answer.upper()}.
Write exactly ONE sentence — 8 to 15 words.
No astrology jargon. No house numbers. No planet names.
Just a warm, specific, memorable line about {topic}.
If yes: what's coming. If no: what to do instead. If maybe: what's still shifting."""
