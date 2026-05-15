"""
LIFE STORY — Mahadasha chapters from birth to ~100 years.

Two endpoints:
  POST /api/public/life-story          → all chapters + arc summary + titles
  POST /api/public/life-story/chapter  → deep reading of one chapter
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.voice import voice_card
from app.services.features._base import (
    safe, extract_birth, get_engine, call_llm, parse_json_or_text, split_segments,
)


router = APIRouter(prefix="/public", tags=["Life Story"])


DASHA_DURATIONS = {
    'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18, 'Jupiter': 16,
    'Saturn': 19, 'Mercury': 17, 'Ketu': 7, 'Venus': 20,
}

# Per-planet visual color (frontend palette only, not interpretation)
PLANET_COLORS = {
    'Sun': '#E8A317', 'Moon': '#C0C0C0', 'Mars': '#CC4444',
    'Mercury': '#55AA55', 'Jupiter': '#DDAA33', 'Venus': '#EEDDEE',
    'Saturn': '#4466AA', 'Rahu': '#887766', 'Ketu': '#998877',
}


def _build_chapter_skeleton(engine) -> Dict:
    """Compute the chapter structure (math only, no LLM, no interpretation)."""
    periods = safe(lambda: engine.get_vimshottari_periods(120), []) or []
    if not isinstance(periods, list):
        periods = []

    dasha_data = safe(engine.get_vimshottari_dasha, {}) or {}
    if not isinstance(dasha_data, dict): dasha_data = {}
    maha = dasha_data.get('mahadasha', {}) if isinstance(dasha_data.get('mahadasha'), dict) else {}
    current_lord = maha.get('lord', '')

    birth_year = engine.birth_dt.year
    now = datetime.now()
    current_age = now.year - birth_year

    chapters = []
    for p in periods:
        if not isinstance(p, dict): continue
        lord = p.get('lord', '')
        if not lord: continue

        years = p.get('years', 0)
        start_dt = p.get('start')
        end_dt = p.get('end')

        if isinstance(start_dt, datetime):
            start_year = start_dt.year
        elif isinstance(start_dt, str):
            try: start_year = int(start_dt[:4])
            except Exception: start_year = birth_year
        else:
            start_year = birth_year

        if isinstance(end_dt, datetime):
            end_year = end_dt.year
        elif isinstance(end_dt, str):
            try: end_year = int(end_dt[:4])
            except Exception: end_year = start_year + int(years)
        else:
            end_year = start_year + int(years)

        start_age = start_year - birth_year
        end_age = end_year - birth_year

        if end_age < 0 or start_age > 100:
            continue

        if lord == current_lord:
            status = 'current'
        elif end_age <= current_age:
            status = 'past'
        else:
            status = 'future'

        chapters.append({
            'index': len(chapters) + 1,
            'lord': lord,
            'color': PLANET_COLORS.get(lord, '#888'),
            'start_age': max(0, start_age),
            'end_age': min(100, end_age),
            'start_year': start_year,
            'end_year': end_year,
            'duration_years': round(years, 1),
            'status': status,
        })

    current_chapter = next((c for c in chapters if c['status'] == 'current'), None)

    asc = engine.ascendant if isinstance(getattr(engine, 'ascendant', None), dict) else {}

    return {
        'chapters': chapters,
        'total_chapters': len(chapters),
        'current_chapter': current_chapter,
        'birth_year': birth_year,
        'current_age': current_age,
        'ascendant': asc.get('rashi_name', ''),
    }


def build_overview_prompt(data: Dict, language: str = 'en') -> str:
    chap_lines = []
    for c in data['chapters']:
        marker = '◆ NOW' if c['status'] == 'current' else ('✓' if c['status'] == 'past' else '○')
        chap_lines.append(
            f"  {marker} Ch{c['index']}: {c['lord']} Mahadasha, age {c['start_age']}-{c['end_age']} "
            f"({c['start_year']}–{c['end_year']}, {c['duration_years']}y) [{c['status']}]"
        )
    chaps = '\n'.join(chap_lines)

    return f"""{voice_card(language)}

You are previewing this person's complete life story as a sequence of mahadasha chapters.

PERSON: {data['ascendant']} ascendant, born {data['birth_year']}, currently age {data['current_age']}

CHAPTERS:
{chaps}

Return ONLY valid JSON in this exact shape:
{{
  "arc_summary": "<3-5 sentences naming the overall journey: where this soul has been, where it is now, where it is heading. Reference the actual sequence of mahadashas.>",
  "chapters": [
    {{"lord": "Mars", "title": "<2-4 word evocative chapter title>", "oneliner": "<one sentence preview of what this chapter is about for THIS person>"}},
    ...one entry per chapter in the same order...
  ]
}}

Rules:
- Each "title" is 2-4 words, unique to THIS chart (not a generic planet label)
- Each "oneliner" reflects the chapter's position: past = reflective, current = present-tense, future = anticipatory
- Title and oneliner together should feel like the spine label of a book chapter
- Total under 400 words
- Do NOT include any text outside the JSON"""


def build_chapter_prompt(chapter: Dict, life_data: Dict, language: str = 'en') -> str:
    today = datetime.now().strftime('%B %d, %Y')
    status_clause = {
        'past': "This chapter is COMPLETE. Reflect on what it taught — past tense, warm hindsight.",
        'current': "This is the CURRENT chapter — they are living it right now. Speak present tense.",
        'future': "This chapter is AHEAD. Preview it with honesty and hope.",
    }.get(chapter['status'], '')

    chap_list = ', '.join(
        f"{c['lord']}({c['start_age']}-{c['end_age']})"
        for c in life_data['chapters']
    )

    return f"""{voice_card(language)}

You are writing one chapter of this person's life story.

TODAY: {today}
PERSON: {life_data['ascendant']} ascendant, born {life_data['birth_year']}, currently age {life_data['current_age']}
Full life arc: {chap_list}

CHAPTER: {chapter['lord']} Mahadasha, age {chapter['start_age']}–{chapter['end_age']} ({chapter['duration_years']} years)
Status: {chapter['status']} — {status_clause}

Write TWO pieces, separated by exactly ---

1. ASTROLOGY (2-3 sentences, museum-label voice, NO "you" pronouns):
   What a {chapter['lord']} mahadasha IS in Vedic astrology — its archetypal energy, the life domains it governs, the recurring themes a {chapter['lord']} period brings. Factual-mystical.

2. READING (5-7 sentences, second person):
   The personal narrative for THIS person at age {chapter['start_age']}–{chapter['end_age']}.
   First sentence: set the scene — what age, what energy enters.
   Middle: what happens — relationships, career, health, growth, challenges.
   Last: what this chapter ultimately teaches. Make it land.
   Speak in the tense that matches status: past=reflect, current=present-tense, future=preview.

Rules:
- ASTROLOGY under 60 words, no "you"
- READING under 130 words, second person, specific to chart
- Separate the two with exactly ---
- No headers, no "ASTROLOGY:" or "READING:" labels in the output"""


class _LifeStoryRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


class _ChapterRequest(BaseModel):
    lord: Optional[str] = None
    index: Optional[int] = None
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = 'en'


@router.post('/life-story')
async def get_life_story(request_body: _LifeStoryRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        skeleton = _build_chapter_skeleton(engine)
        prompt = build_overview_prompt(skeleton, language)
        raw = await call_llm(prompt, settings,
                             user_message="Title each chapter and summarize the arc.",
                             max_tokens=2000, temperature=0.8)
        parsed = parse_json_or_text(raw)

        # Zip LLM titles + oneliners back into structured chapters
        llm_chapters = parsed.get('chapters', []) if isinstance(parsed.get('chapters'), list) else []
        llm_by_lord = {}
        for entry in llm_chapters:
            if isinstance(entry, dict) and entry.get('lord'):
                llm_by_lord[entry['lord']] = entry

        merged = []
        for c in skeleton['chapters']:
            llm = llm_by_lord.get(c['lord'], {})
            merged.append({
                **c,
                'title': llm.get('title', f"{c['lord']} Mahadasha"),
                'oneliner': llm.get('oneliner', ''),
            })

        current = next((c for c in merged if c['status'] == 'current'), None)

        return {
            'chapters': merged,
            'total_chapters': len(merged),
            'current_chapter': current,
            'arc_summary': parsed.get('arc_summary', ''),
            'birth_year': skeleton['birth_year'],
            'current_age': skeleton['current_age'],
            'ascendant': skeleton['ascendant'],
            'version': 1,
            'cache_ttl_seconds': 86400,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post('/life-story/chapter')
async def get_life_chapter(request_body: _ChapterRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')
    if not request_body.lord and request_body.index is None:
        raise HTTPException(status_code=400, detail='Must provide lord or index')

    try:
        engine = get_engine(birth_data)
        language = request_body.language or 'en'

        skeleton = _build_chapter_skeleton(engine)

        # Find requested chapter
        target = None
        if request_body.lord:
            target = next((c for c in skeleton['chapters'] if c['lord'] == request_body.lord), None)
        if target is None and request_body.index is not None:
            target = next((c for c in skeleton['chapters'] if c['index'] == request_body.index), None)

        if target is None:
            raise HTTPException(status_code=404, detail='Chapter not found')

        prompt = build_chapter_prompt(target, skeleton, language)
        raw = await call_llm(prompt, settings,
                             user_message=f"Tell the {target['lord']} chapter.",
                             max_tokens=1000, temperature=0.85)
        segments = split_segments(raw)
        astrology = segments[0] if len(segments) > 0 else ''
        reading = segments[1] if len(segments) > 1 else (segments[0] if len(segments) == 1 else '')

        return {
            **target,
            'astrology': astrology,
            'reading': reading,
            'version': 2,
            'cache_ttl_seconds': 86400,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


life_story_router = router
