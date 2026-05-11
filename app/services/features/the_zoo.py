"""
THE ZOO — Your 4 animals from the Chinese Four Pillars.

Year animal = social identity (what people think you are)
Month animal = career/parents energy
Day animal = true self (inner nature)
Hour animal = hidden self / children / old age

Called by: POST /the-zoo { kundli_data }
"""

from datetime import datetime
from typing import Dict


PILLAR_MEANING = {
    'year':  {'label': 'Year', 'role': 'Your outer mask', 'governs': 'Social identity, grandparents, early childhood', 'ages': '0-16'},
    'month': {'label': 'Month', 'role': 'Your career self', 'governs': 'Parents, career, how the world uses you', 'ages': '17-32'},
    'day':   {'label': 'Day', 'role': 'Your true self', 'governs': 'Inner nature, spouse, your real personality', 'ages': '33-48'},
    'hour':  {'label': 'Hour', 'role': 'Your hidden self', 'governs': 'Children, ambitions, old age, secret desires', 'ages': '49+'},
}

ANIMAL_NATURE = {
    'Rat':     {'nature': 'Clever, resourceful, quick-witted. First of the cycle — the initiator.', 'shadow': 'Can be manipulative and hoarding.'},
    'Ox':      {'nature': 'Patient, reliable, determined. The unstoppable worker.', 'shadow': 'Stubborn to a fault, slow to forgive.'},
    'Tiger':   {'nature': 'Brave, competitive, magnetic. Born to lead and roar.', 'shadow': 'Reckless, rebellious, hard to contain.'},
    'Rabbit':  {'nature': 'Gentle, elegant, diplomatic. Sees beauty others miss.', 'shadow': 'Avoids conflict, can be passive-aggressive.'},
    'Dragon':  {'nature': 'Powerful, lucky, charismatic. The mythical overachiever.', 'shadow': 'Arrogant, demands too much from others.'},
    'Snake':   {'nature': 'Wise, intuitive, mysterious. Thinks ten moves ahead.', 'shadow': 'Secretive, jealous, cold when threatened.'},
    'Horse':   {'nature': 'Free, energetic, adventurous. Needs wide open space.', 'shadow': 'Impatient, commitment-phobic, burns out fast.'},
    'Goat':    {'nature': 'Creative, gentle, empathetic. The artist of the zodiac.', 'shadow': 'Indecisive, dependent, prone to worry.'},
    'Monkey':  {'nature': 'Witty, inventive, playful. Solves problems nobody else can.', 'shadow': 'Tricky, restless, hard to trust fully.'},
    'Rooster': {'nature': 'Honest, hardworking, punctual. Says what others think.', 'shadow': 'Critical, vain, can be abrasive.'},
    'Dog':     {'nature': 'Loyal, honest, protective. The moral compass of the zodiac.', 'shadow': 'Anxious, pessimistic, stubborn about right/wrong.'},
    'Pig':     {'nature': 'Kind, generous, tolerant. Enjoys life without pretense.', 'shadow': 'Naive, overindulgent, avoids hard truths.'},
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_the_zoo(engine, language: str = 'en') -> Dict:
    """Build the 4 animals from BaZi pillars."""

    from app.services.chinese.bazi import BaZiChart

    bazi = BaZiChart(engine.birth_dt)
    pillars = bazi.get_four_pillars()
    if not isinstance(pillars, dict): pillars = {}

    year_animal_sign = bazi.get_animal_sign()
    if not isinstance(year_animal_sign, dict): year_animal_sign = {}
    year_animal = year_animal_sign.get('animal', '')

    animals = []
    briefing_lines = [f"THE ZOO — 4 Animals\nYear animal (public): {year_animal}\n"]

    for key in ['year', 'month', 'day', 'hour']:
        p = pillars.get(key, {})
        if not isinstance(p, dict): p = {}

        branch = p.get('branch', {})
        if not isinstance(branch, dict): branch = {}
        stem = p.get('stem', {})
        if not isinstance(stem, dict): stem = {}

        animal = branch.get('animal', '')
        animal_element = branch.get('element', '')
        stem_element = stem.get('element', '')
        stem_name = stem.get('name', '')
        chinese = branch.get('chinese', '')
        polarity = stem.get('polarity', '')

        meta = PILLAR_MEANING.get(key, {})
        nature = ANIMAL_NATURE.get(animal, {})

        entry = {
            'pillar': key,
            'label': meta.get('label', key),
            'role': meta.get('role', ''),
            'governs': meta.get('governs', ''),
            'ages': meta.get('ages', ''),
            'animal': animal,
            'animal_chinese': chinese,
            'animal_element': animal_element,
            'stem_element': stem_element,
            'stem_name': stem_name,
            'polarity': polarity,
            'nature': nature.get('nature', ''),
            'shadow': nature.get('shadow', ''),
            'full_pillar': f"{polarity} {stem_element} {animal}",
        }
        animals.append(entry)

        briefing_lines.append(
            f"{meta.get('label',key).upper()} PILLAR ({meta.get('role','')}):\n"
            f"  Animal: {animal} ({chinese}) | Element: {animal_element} | Stem: {polarity} {stem_element}\n"
            f"  Governs: {meta.get('governs','')}\n"
            f"  Nature: {nature.get('nature','')}\n"
            f"  Shadow: {nature.get('shadow','')}\n"
        )

    return {
        'animals': animals,
        'year_animal': year_animal,
        'briefing': '\n'.join(briefing_lines),
    }


def build_zoo_prompt(animal_data: Dict, all_data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for a single pillar animal."""
    briefing = all_data['briefing']
    pillar = animal_data['pillar']
    animal = animal_data['animal']
    role = animal_data['role']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    return f"""You are a Chinese astrology master — vivid, warm, a great storyteller.{lang_note}

{briefing}

READING THE {pillar.upper()} ANIMAL: {animal}
Role: {role}
Governs: {animal_data['governs']}
Element: {animal_data['polarity']} {animal_data['stem_element']} {animal}
Nature: {animal_data['nature']}
Shadow: {animal_data['shadow']}

Write 4-5 sentences about what this {animal} means in the {pillar} position:
1. What this animal reveals about this part of their life ({role}).
2. How the element ({animal_data['stem_element']}) modifies this animal's energy.
3. The strength and the vulnerability this creates.
4. One surprising truth about having {animal} here.

{f"IMPORTANT: This is the DAY pillar — this is who they REALLY are, not who they show the world. The year animal ({all_data['year_animal']}) is just the mask." if pillar == 'day' else ""}

Under 80 words. No jargon. Vivid and specific."""
