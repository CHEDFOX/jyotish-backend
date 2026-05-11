from datetime import datetime
from typing import Dict
import random

def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default

def build_blunt_seer(engine, language='en'):
    from app.services.western.chart import WesternChart
    from app.services.western.profiles import WesternProfiles
    from app.services.western.extras import calculate_lilith
    from app.services.western.hellenistic import calculate_profections

    chart = WesternChart(engine.birth_dt, engine.latitude, engine.longitude)
    big3 = _safe(chart.get_big_three, {})
    if not isinstance(big3, dict): big3 = {}
    sun_sign = big3.get('sun', {}).get('sign', '') if isinstance(big3.get('sun'), dict) else ''
    moon_sign = big3.get('moon', {}).get('sign', '') if isinstance(big3.get('moon'), dict) else ''
    rising_sign = big3.get('rising', {}).get('sign', '') if isinstance(big3.get('rising'), dict) else ''
    elements = _safe(chart.get_element_balance, {})
    if not isinstance(elements, dict): elements = {}
    dominant_element = elements.get('dominant', '')
    weakest_element = ''
    elem_counts = elements.get('counts', {})
    if isinstance(elem_counts, dict) and elem_counts:
        weakest_element = min(elem_counts, key=elem_counts.get)
    aspects = _safe(chart.get_aspects, [])
    if not isinstance(aspects, list): aspects = []
    harsh_aspects = []
    for a in aspects:
        if not isinstance(a, dict): continue
        if a.get('aspect', '') in ('square', 'opposition'):
            harsh_aspects.append(a.get('planet1','') + ' ' + a.get('aspect','') + ' ' + a.get('planet2',''))
    planets_data = {}
    if hasattr(chart, '_planets') and isinstance(chart._planets, dict):
        planets_data = chart._planets
    retros = []
    for pname, pdata in planets_data.items():
        if isinstance(pdata, dict) and (pdata.get('retrograde', False) or pdata.get('is_retrograde', False)):
            retros.append(pname)
    lilith = _safe(lambda: calculate_lilith(engine.birth_dt), {})
    if not isinstance(lilith, dict): lilith = {}
    lilith_sign = lilith.get('sign', '')
    profection = _safe(lambda: calculate_profections(engine.birth_dt), {})
    if not isinstance(profection, dict): profection = {}
    dasha = _safe(engine.get_vimshottari_dasha, {})
    if not isinstance(dasha, dict): dasha = {}
    dasha_string = dasha.get('dasha_string', '')
    age = datetime.now().year - engine.birth_dt.year
    briefing = 'ROAST TARGET:\n'
    briefing += 'Age: ' + str(age) + '\n'
    briefing += 'Sun: ' + sun_sign + ' | Moon: ' + moon_sign + ' | Rising: ' + rising_sign + '\n'
    briefing += 'Lilith: ' + lilith_sign + '\n'
    briefing += 'Dominant element: ' + dominant_element + ' | Weakest: ' + weakest_element + '\n'
    briefing += 'Harsh aspects: ' + ', '.join(harsh_aspects[:4]) + '\n'
    briefing += 'Retrogrades at birth: ' + ', '.join(retros) + '\n'
    briefing += 'Current dasha: ' + dasha_string + '\n'
    return {
        'sun': sun_sign, 'moon': moon_sign, 'rising': rising_sign,
        'lilith': lilith_sign, 'dominant_element': dominant_element,
        'weakest_element': weakest_element, 'harsh_aspects': harsh_aspects[:4],
        'natal_retrogrades': retros, 'dasha': dasha_string, 'age': age,
        'briefing': briefing,
    }

def build_roast_prompt(data, language='en'):
    briefing = data['briefing']
    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = '\nRespond in ' + language + '.'
    angles = [
        'their love life and dating patterns',
        'their work ethic and career habits',
        'how they handle money and spending',
        'their texting and communication style',
        'their emotional patterns and moods',
        'what they are like at parties and social events',
        'their morning routine and daily habits',
        'their ego and how they seek validation',
        'their hidden guilty pleasures',
        'how they handle arguments and conflict',
    ]
    angle = random.choice(angles)
    prompt = 'You are a stand-up comedian who knows astrology. '
    prompt += 'You roast people at their birthday party. Funny, specific, lovable.'
    prompt += lang_note + '\n\n'
    prompt += briefing + '\n\n'
    prompt += 'ANGLE: Focus on ' + angle + '\n\n'
    prompt += 'Write a FUNNY roast in 4-5 sentences.\n'
    prompt += '- Make them LAUGH at themselves, not feel bad.\n'
    prompt += '- Use their actual chart but connect to everyday life: dating apps, Netflix, texting, cooking.\n'
    prompt += '- Start with something unexpected.\n'
    prompt += '- End with one line so specific they will screenshot it.\n'
    prompt += '- Under 80 words. NO jargon. NO bullets in the output. Just funny flowing text.\n'
    prompt += '- COMEDY not cruelty. Playful not painful.'
    return prompt
