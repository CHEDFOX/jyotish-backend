"""
LIFE STORY — Complete life chapters from birth to ~100 years.

Each chapter = a Mahadasha period.
Returns structured data + LLM-written chapter descriptions.

Called by: POST /life-story { kundli_data }
"""

from datetime import datetime
from typing import Dict, List

PLANET_ORDER = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

# Chapter themes per dasha lord
CHAPTER_THEMES = {
    'Sun':     {'title': 'The Awakening', 'theme': 'Identity, authority, father, visibility', 'lesson': 'Who you are when no mask is worn', 'color': '#E8A317'},
    'Moon':    {'title': 'The Feeling', 'theme': 'Emotions, mother, comfort, intuition', 'lesson': 'Learning to trust what you feel', 'color': '#C0C0C0'},
    'Mars':    {'title': 'The Battle', 'theme': 'Courage, conflict, energy, property', 'lesson': 'What you are willing to fight for', 'color': '#CC4444'},
    'Mercury': {'title': 'The Learning', 'theme': 'Intelligence, speech, trade, adaptability', 'lesson': 'The world is a classroom — every person a teacher', 'color': '#55AA55'},
    'Jupiter': {'title': 'The Expansion', 'theme': 'Wisdom, teachers, children, dharma', 'lesson': 'Grace arrives when you stop forcing', 'color': '#DDAA33'},
    'Venus':   {'title': 'The Desire', 'theme': 'Love, beauty, marriage, art, pleasure', 'lesson': 'What you love reveals what you are', 'color': '#EEDDEE'},
    'Saturn':  {'title': 'The Reckoning', 'theme': 'Discipline, karma, delays, endurance', 'lesson': 'The reward is on the other side of patience', 'color': '#4466AA'},
    'Rahu':    {'title': 'The Hunger', 'theme': 'Obsession, ambition, foreign, illusion', 'lesson': 'Chase what scares you — or it chases you', 'color': '#887766'},
    'Ketu':    {'title': 'The Release', 'theme': 'Detachment, past lives, spiritual insight', 'lesson': 'Letting go is the last form of courage', 'color': '#998877'},
}

DASHA_DURATIONS = {
    'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18, 'Jupiter': 16,
    'Saturn': 19, 'Mercury': 17, 'Ketu': 7, 'Venus': 20,
}

CHAPTER_DEEP = {
    'Sun': 'The Sun period brings you face to face with who you really are. Authority figures — father, bosses, government — play a central role. You seek recognition, leadership, and a place in the world. Health of the heart and bones may need attention. Ego confrontations are likely but necessary. This is when you discover your core identity.',
    'Moon': 'The Moon period is deeply emotional. Your relationship with your mother, your inner world, your sleep patterns — everything runs through feeling. Public image shifts. Travel over water is likely. Mental health matters most here. This is when you learn to sit with your emotions instead of running from them.',
    'Mars': 'The Mars period is pure action. Property deals, physical challenges, conflicts with siblings, legal disputes — Mars doesn\'t do subtlety. Accidents are possible if Mars is afflicted. But if well-placed, this is when you build empires, win competitions, and claim territory. The body leads, the mind follows.',
    'Mercury': 'The Mercury period sharpens the mind. Education, business ventures, writing, communication skills — everything intellectual accelerates. Skin and nervous system need care. Short trips multiply. This is the chapter where you learn to think precisely, speak carefully, and trade wisely. Adaptability is your superpower.',
    'Jupiter': 'The Jupiter period is the most blessed chapter of your life. Marriage, children, spiritual growth, meeting your guru — all happen under Jupiter\'s grace. Wealth expands naturally. Philosophy deepens. This is when you understand why you are here. The danger is over-expansion — growing too fast, promising too much.',
    'Venus': 'The Venus period is the longest chapter — 20 years of desire, beauty, and relationships. Marriage and love take center stage. Creative expression peaks. Luxury and comfort increase. Vehicles, art, music, beauty routines — Venus refines everything. The challenge is knowing the difference between what you want and what you need.',
    'Saturn': 'The Saturn period is the hardest chapter — 19 years of karmic reckoning. Nothing comes easy, but nothing earned here can be taken away. Career builds slowly but permanently. Chronic health patterns emerge. Discipline becomes your religion. This is when you discover that the universe rewards persistence, not talent.',
    'Rahu': 'The Rahu period is the wildest ride — 18 years of obsession, ambition, and transformation. Foreign connections, technology, unconventional paths — Rahu tears up the rulebook. Sudden rises and sudden falls are both possible. Addiction risks increase. This is when you discover what you are truly hungry for — and whether that hunger serves you.',
    'Ketu': 'The Ketu period strips away everything unnecessary. Relationships end, possessions lose meaning, spiritual insight deepens. This is not loss — it is liberation. Psychic sensitivity increases. Past-life patterns surface. The chapter teaches you that who you are without anything is who you actually are.',
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_life_story(engine, language: str = 'en') -> Dict:
    """Build the complete life story from dasha periods."""

    # Get all mahadasha periods
    periods = _safe(lambda: engine.get_vimshottari_periods(120), [])
    if not isinstance(periods, list):
        periods = []

    # Get current dasha info
    dasha_data = _safe(engine.get_vimshottari_dasha, {})
    if not isinstance(dasha_data, dict):
        dasha_data = {}
    current_lord = ''
    maha = dasha_data.get('mahadasha', {})
    if isinstance(maha, dict):
        current_lord = maha.get('lord', '')

    # Birth year
    birth_year = engine.birth_dt.year
    now = datetime.now()
    current_age = now.year - birth_year

    # Build chapters
    chapters = []
    for i, period in enumerate(periods):
        if not isinstance(period, dict):
            continue

        lord = period.get('lord', '')
        if not lord:
            continue

        start_dt = period.get('start')
        end_dt = period.get('end')
        years = period.get('years', 0)

        if isinstance(start_dt, datetime):
            start_year = start_dt.year
            start_age = start_year - birth_year
        elif isinstance(start_dt, str):
            try:
                start_year = int(start_dt[:4])
                start_age = start_year - birth_year
            except:
                start_age = 0
                start_year = birth_year
        else:
            start_age = 0
            start_year = birth_year

        if isinstance(end_dt, datetime):
            end_year = end_dt.year
            end_age = end_year - birth_year
        elif isinstance(end_dt, str):
            try:
                end_year = int(end_dt[:4])
                end_age = end_year - birth_year
            except:
                end_age = start_age + int(years)
                end_year = start_year + int(years)
        else:
            end_age = start_age + int(years)
            end_year = start_year + int(years)

        # Skip chapters that end before age 0 or start after 100
        if end_age < 0 or start_age > 100:
            continue

        theme_data = CHAPTER_THEMES.get(lord, {})
        is_current = (lord == current_lord)
        is_past = end_age <= current_age
        is_future = start_age > current_age

        status = 'current' if is_current else ('past' if is_past else 'future')

        chapter = {
            'index': len(chapters) + 1,
            'lord': lord,
            'title': theme_data.get('title', lord),
            'theme': theme_data.get('theme', ''),
            'lesson': theme_data.get('lesson', ''),
            'color': theme_data.get('color', '#888'),
            'start_age': max(0, start_age),
            'end_age': min(100, end_age),
            'start_year': start_year,
            'end_year': end_year,
            'duration_years': round(years, 1),
            'status': status,
            'deep_description': CHAPTER_DEEP.get(lord, ''),
        }
        chapters.append(chapter)

    # Summary
    current_chapter = None
    for ch in chapters:
        if ch['status'] == 'current':
            current_chapter = ch
            break

    # Yogas for LLM briefing
    yoga_data = _safe(engine.get_yogas, {})
    if not isinstance(yoga_data, dict):
        yoga_data = {}
    yoga_summary = yoga_data.get('summary', {})
    if not isinstance(yoga_summary, dict):
        yoga_summary = {}
    total_yogas = yoga_summary.get('total_yogas', 0)

    # Ascendant
    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}
    asc_sign = asc.get('rashi_name', '')

    # Build briefing for LLM
    briefing_lines = [
        f"LIFE STORY for person born {birth_year} (age {current_age})",
        f"Ascendant: {asc_sign}",
        f"Total yogas: {total_yogas}",
        f"Chapters: {len(chapters)}",
        "",
    ]
    for ch in chapters:
        marker = "◆ NOW" if ch['status'] == 'current' else ("✓" if ch['status'] == 'past' else "○")
        briefing_lines.append(
            f"{marker} Ch{ch['index']}: {ch['lord']} ({ch['title']}) — age {ch['start_age']}-{ch['end_age']} ({ch['duration_years']}y)"
        )

    briefing = '\n'.join(briefing_lines)

    return {
        'chapters': chapters,
        'total_chapters': len(chapters),
        'current_chapter': current_chapter,
        'birth_year': birth_year,
        'current_age': current_age,
        'ascendant': asc_sign,
        'briefing': briefing,
    }


def build_chapter_prompt(chapter: Dict, life_data: Dict, language: str = 'en') -> str:
    """Build LLM prompt for a single chapter reading."""
    lord = chapter['lord']
    title = chapter['title']
    status = chapter['status']
    briefing = life_data['briefing']

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    today = datetime.now().strftime('%B %d, %Y')

    status_context = {
        'past': f"This chapter is COMPLETE. The person lived through it. Reflect on what it taught.",
        'current': f"This is their CURRENT chapter. They are living it RIGHT NOW. Be present-tense and relevant.",
        'future': f"This chapter is AHEAD. Give them a preview of what's coming — with hope and preparation.",
    }.get(status, '')

    return f"""You are the voice of the stars — ancient, warm, mystical, true.
You are writing one chapter of this person's life story.

TODAY: {today}{lang_note}

{briefing}

CHAPTER: {chapter['index']} — "{title}" ({lord} Mahadasha)
Age {chapter['start_age']} to {chapter['end_age']} ({chapter['duration_years']} years)
Status: {status_context}

Theme: {chapter['theme']}
Core lesson: {chapter['lesson']}

Write a vivid 4-6 sentence description of this life chapter.
First sentence: set the scene — what age range, what energy enters.
Middle sentences: what happens — relationships, career, health, growth, challenges.
Last sentence: what this chapter ultimately teaches. Make it land.

Be SPECIFIC to {lord}'s energy. Not generic life advice.
If this is the current chapter, address them directly.
If past, reflect with warmth. If future, preview with honesty.

Maximum 100 words. No headers, no bullets. One flowing paragraph."""
