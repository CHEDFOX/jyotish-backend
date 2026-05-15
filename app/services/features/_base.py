"""
SHARED FEATURE HELPERS — used by every feature in this directory.

Goals:
- one place for LLM call shape
- one place for birth-data extraction
- one place for engine caching
- features stay slim (data + prompt + response only)
"""

from datetime import datetime
from typing import Optional

import httpx
from fastapi import HTTPException


def safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def extract_birth(kundli_data) -> Optional[dict]:
    if not kundli_data:
        return None
    raw = kundli_data.get('raw', {})
    birth = raw.get('birth_details', {}) or kundli_data.get('birth_details', {})
    if not birth:
        return None
    try:
        return {
            'year': int(birth.get('year', 2000)),
            'month': int(birth.get('month', 1)),
            'day': int(birth.get('day', 1)),
            'hour': int(birth.get('hour', 12)),
            'minute': int(birth.get('minute', 0)),
            'lat': float(birth.get('latitude', 28.6)),
            'lng': float(birth.get('longitude', 77.2)),
        }
    except (TypeError, ValueError):
        return None


def get_engine(birth_data):
    from app.services.oracle.engine_cache import get_cached_engine
    birth_dt = datetime(
        birth_data['year'], birth_data['month'], birth_data['day'],
        birth_data.get('hour', 12), birth_data.get('minute', 0),
    )
    engine, _ = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
    return engine


async def call_llm(prompt: str, settings, user_message: str = 'Read this for me.',
                   max_tokens: int = 1500, temperature: float = 0.85) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.OPENROUTER_MODEL,
                'messages': [
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': user_message},
                ],
                'max_tokens': max_tokens,
                'temperature': temperature,
            },
            timeout=120.0,
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail='Upstream LLM error')
    return response.json()['choices'][0]['message']['content'].strip().replace('```', '').strip()


def split_segments(raw: str, separator: str = '---') -> list:
    """Split LLM output into segments, falling back to paragraph breaks."""
    segments = [s.strip() for s in raw.split(separator) if s.strip()]
    if len(segments) < 2:
        segments = [s.strip() for s in raw.split('\n\n') if s.strip()]
    return segments


def parse_json_or_text(raw: str) -> dict:
    """Try to parse LLM output as JSON; fall back to {'text': raw}."""
    import json
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find('{'), raw.rfind('}')
        if s >= 0 and e > s:
            try:
                return json.loads(raw[s:e+1])
            except json.JSONDecodeError:
                pass
    return {'text': raw}
