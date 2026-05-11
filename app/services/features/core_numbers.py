"""
CORE NUMBERS — All key numerology numbers with short significance notes.

Mulank, Bhagyank, Personal Year/Month/Day, Lo Shu missing numbers.
LLM writes a flowing reading about all numbers together.

Called by: POST /core-numbers { kundli_data, name }
"""

from datetime import datetime, date
from typing import Dict


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_core_numbers(birth_date: date, name: str = '', language: str = 'en') -> Dict:
    """Build all core numerology numbers."""

    from app.services.numerology.core import NumerologyEngine

    ne = NumerologyEngine(name=name, birth_date=birth_date)

    mulank = ne.get_mulank()
    if not isinstance(mulank, dict): mulank = {}
    bhagyank = ne.get_bhagyank()
    if not isinstance(bhagyank, dict): bhagyank = {}
    personal_year = ne.get_personal_year()
    if not isinstance(personal_year, dict): personal_year = {}
    personal_month = ne.get_personal_month()
    if not isinstance(personal_month, dict): personal_month = {}
    personal_day = ne.get_personal_day()
    if not isinstance(personal_day, dict): personal_day = {}
    lo_shu = ne.get_lo_shu_grid()
    if not isinstance(lo_shu, dict): lo_shu = {}

    namank = {}
    if name:
        namank = ne.get_namank()
        if not isinstance(namank, dict): namank = {}

    chaldean = namank.get('chaldean', {}) if namank else {}
    if not isinstance(chaldean, dict): chaldean = {}

    missing = lo_shu.get('missing', [])
    if not isinstance(missing, list): missing = []
    repeated = lo_shu.get('repeated', {})
    if not isinstance(repeated, dict): repeated = {}

    numbers = [
        {
            'key': 'mulank',
            'label': 'Root Number',
            'number': mulank.get('number', 0),
            'planet': mulank.get('planet', ''),
            'name': mulank.get('name', ''),
            'traits': mulank.get('traits', ''),
            'note': f"Born on the {birth_date.day}th — this is your core vibration, your driver.",
            'color': mulank.get('color', ''),
            'day': mulank.get('day', ''),
        },
        {
            'key': 'bhagyank',
            'label': 'Destiny Number',
            'number': bhagyank.get('number', 0),
            'planet': bhagyank.get('planet', ''),
            'name': bhagyank.get('name', ''),
            'traits': bhagyank.get('traits', ''),
            'note': f"Your life path — where the universe is taking you.",
            'calculation': bhagyank.get('calculation', ''),
            'is_master': bhagyank.get('is_master', False),
        },
        {
            'key': 'personal_year',
            'label': 'Personal Year',
            'number': personal_year.get('number', 0),
            'theme': personal_year.get('theme', ''),
            'note': f"The energy governing {datetime.now().year} for you.",
        },
        {
            'key': 'personal_month',
            'label': 'Personal Month',
            'number': personal_month.get('number', 0),
            'theme': personal_month.get('theme', ''),
            'note': f"This month's vibration within your year cycle.",
        },
        {
            'key': 'personal_day',
            'label': 'Today',
            'number': personal_day.get('number', 0),
            'theme': personal_day.get('theme', ''),
            'note': f"Today's number — the energy of this specific day for you.",
        },
    ]

    if name and chaldean.get('root'):
        numbers.insert(2, {
            'key': 'namank',
            'label': 'Name Number',
            'number': chaldean.get('root', 0),
            'note': f"Your name \"{name}\" vibrates at this frequency.",
            'total': chaldean.get('total', 0),
        })

    # Build briefing
    briefing_lines = [f"CORE NUMBERS for {birth_date} (name: {name or 'not provided'})\n"]
    for n in numbers:
        briefing_lines.append(f"{n['label']}: {n['number']} — {n.get('name', n.get('theme', ''))}")
        if n.get('planet'):
            briefing_lines.append(f"  Planet: {n['planet']} | Traits: {n.get('traits', '')}")

    briefing_lines.append(f"\nLo Shu missing: {missing}")
    briefing_lines.append(f"Lo Shu repeated: {repeated}")

    return {
        'numbers': numbers,
        'missing_numbers': missing,
        'repeated_numbers': repeated,
        'lo_shu_grid': lo_shu.get('grid', {}),
        'briefing': '\n'.join(briefing_lines),
    }


def build_core_numbers_prompt(data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for core numbers reading."""
    briefing = data['briefing']
    numbers = data['numbers']
    missing = data['missing_numbers']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    num_summary = ', '.join(f"{n['label']}={n['number']}" for n in numbers)

    return f"""You are a numerologist — clear, warm, insightful.{lang_note}

{briefing}

Write a FLOWING reading about this person's numbers. 6-8 sentences.

Cover:
- The Root Number — what drives them daily (1 sentence)
- The Destiny Number — where life is pulling them (1 sentence)
- How Root and Destiny work together or clash (1 sentence)
- The Personal Year — what {datetime.now().year} is about for them (1 sentence)
- Today's number — one line about what today brings (1 sentence)
- Missing numbers from Lo Shu ({missing}) — what gaps exist (1 sentence)
- End with one surprising connection between their numbers

Under 130 words. No headers, no bullets, no number labels like "Number 1:".
Just flowing text — each sentence about a different number.
Reference the actual numbers and their planets/themes."""
