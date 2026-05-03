"""
PORTRAIT MEMORY SYSTEM
One file per user. 500 chars of dense observational shorthand.
Rewritten by LLM after each session. Read by Oracle before each response.

Format is dense shorthand — not prose, not JSON:
  S14|Jan26|en|bphs
  Ask: marriage(4x,active) career(2x,covered)
  Pred: marriage mid26-early27(pending)
  Rem: Venus-mantra-Fri(following)
  Tone: warm+poetic, no-lists
  Open: spouse-nature spiritual-depth
  Avoid: career-aptitude personality-basics
  Note: asks-follow-ups, comes-every-2wks
"""

import json
import hashlib
import os
import httpx
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

PORTRAIT_DIR = Path("data/portraits")
PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# STORAGE — Read / Write / Hash
# ═══════════════════════════════════════════════════════════════

def _user_hash(birth_data: Dict) -> str:
    """Unique hash from birth data."""
    key = f"{birth_data.get('year', 0)}-{birth_data.get('month', 0)}-{birth_data.get('day', 0)}-" \
          f"{birth_data.get('hour', 0)}-{birth_data.get('minute', 0)}-" \
          f"{birth_data.get('lat', 0)}-{birth_data.get('lng', 0)}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _portrait_path(user_hash: str) -> Path:
    return PORTRAIT_DIR / f"{user_hash}.json"


def read_portrait(birth_data: Dict) -> Dict:
    """Read user's portrait. Returns empty dict if new user."""
    uh = _user_hash(birth_data)
    path = _portrait_path(uh)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def save_portrait(birth_data: Dict, portrait_text: str, session_count: int):
    """Save updated portrait."""
    uh = _user_hash(birth_data)
    path = _portrait_path(uh)
    data = {
        'portrait': portrait_text[:500],
        'session_count': session_count,
        'updated_at': datetime.now().isoformat(),
        'user_hash': uh,
    }
    path.write_text(json.dumps(data, ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════
# SESSION BUFFER — Tracks conversation in memory
# ═══════════════════════════════════════════════════════════════

# In-memory buffer + disk persistence
_session_buffers: Dict[str, Dict] = {}


def _buffer_path(user_hash: str) -> Path:
    return PORTRAIT_DIR / f"{user_hash}_buffer.json"


def _load_buffer(user_hash: str) -> Dict:
    path = _buffer_path(user_hash)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_buffer(user_hash: str, buffer: Dict):
    path = _buffer_path(user_hash)
    try:
        path.write_text(json.dumps(buffer, ensure_ascii=False))
    except Exception:
        pass


def _delete_buffer(user_hash: str):
    path = _buffer_path(user_hash)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def add_exchange(birth_data: Dict, user_message: str, oracle_response: str,
                  classifier_output: Dict = None, sections_used: List = None,
                  system: str = "bphs"):
    """Add an exchange to the current session buffer."""
    uh = _user_hash(birth_data)
    if uh not in _session_buffers:
        _session_buffers[uh] = {
            'exchanges': [],
            'system': system,
            'started': datetime.now().isoformat(),
            'last_exchange': datetime.now().isoformat(),
        }

    _session_buffers[uh]['exchanges'].append({
        'user': user_message[:300],
        'oracle': oracle_response[:500],
        'topic': classifier_output.get('topic', '') if classifier_output else '',
        'tone': classifier_output.get('emotional_tone', '') if classifier_output else '',
        'sections': sections_used or [],
    })
    _session_buffers[uh]['system'] = system
    _session_buffers[uh]['last_exchange'] = datetime.now().isoformat()

    # Persist to disk
    _save_buffer(uh, _session_buffers[uh])


def get_session_buffer(birth_data: Dict) -> Dict:
    """Get current session buffer."""
    uh = _user_hash(birth_data)
    if uh in _session_buffers:
        return _session_buffers[uh]
    return _load_buffer(uh)


def clear_session_buffer(birth_data: Dict):
    """Clear session buffer after portrait rewrite."""
    uh = _user_hash(birth_data)
    _session_buffers.pop(uh, None)
    _delete_buffer(uh)


# ═══════════════════════════════════════════════════════════════
# FORMAT CONVERSATION FOR REWRITER
# ═══════════════════════════════════════════════════════════════

def _format_session_for_rewrite(session: Dict) -> str:
    """Format session exchanges in clean organized structure."""
    exchanges = session.get('exchanges', [])
    if not exchanges:
        return "No exchanges"

    lines = []
    lines.append(f"System: {session.get('system', 'bphs')}")
    lines.append(f"Exchanges: {len(exchanges)}")
    lines.append("")

    for i, ex in enumerate(exchanges):
        lines.append(f"Q{i + 1}: {ex['user']}")
        lines.append(f"A{i + 1}: {ex['oracle']}")
        if ex.get('sections'):
            lines.append(f"Sections: {', '.join(ex['sections'][:5])}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# PORTRAIT REWRITE — LLM call
# ═══════════════════════════════════════════════════════════════

REWRITE_PROMPT = """You write a 500-char briefing that an astrologer reads BEFORE speaking to this client.

Every word must change how the astrologer responds.
If removing a word wouldn't change the response, don't write it.

FORMAT (dense shorthand, not prose):
S{n}|{month+year}|{lang}|{system}
Ask: topic(count,status) — status: active/covered/resolved
Pred: event timeframe(pending/confirmed/missed) — NEVER drop predictions
Rem: remedy(following/suggested/stopped)
Tone: what-works, what-fails
Open: what's unresolved — these should come up naturally
Avoid: what's been said — never repeat these
Note: patterns only the astrologer would notice

TEST EACH LINE: "Will this make the next response smarter?"
No → delete it.
Yes → keep it.

NEVER WRITE:
- "user is curious" (everyone is)
- "user asks questions" (obviously)
- "first seen date" (doesn't change response)
- anything about the chart (Oracle already has chart data)
- interpretations of WHY the user feels something

ALWAYS WRITE:
- exact predictions with timeframes (Oracle must be able to reference them)
- exact remedies suggested (Oracle must be able to follow up)
- topics fully covered (Oracle must not repeat)
- what tone/style landed (Oracle must match it)
- what's unresolved (Oracle should address when relevant)

═══ EXISTING PORTRAIT ═══
{old_portrait}

═══ TODAY'S SESSION ═══
{session_data}

Write the updated portrait (500 chars max, dense shorthand):"""


async def rewrite_portrait(birth_data: Dict, api_key: str, model: str) -> str:
    """Rewrite portrait after session ends. Async, non-blocking."""
    old = read_portrait(birth_data)
    old_portrait = old.get('portrait', 'New client — first session')
    old_count = old.get('session_count', 0)
    new_count = old_count + 1

    session = get_session_buffer(birth_data)
    if not session or not session.get('exchanges'):
        return old_portrait

    session_formatted = _format_session_for_rewrite(session)

    prompt = REWRITE_PROMPT.replace("{old_portrait}", old_portrait) \
                            .replace("{session_data}", session_formatted)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You write dense shorthand that changes how an astrologer responds. 500 chars. Every word must earn its place."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 250,
                    "temperature": 0.3,
                },
                timeout=15.0,
            )

            if response.status_code == 200:
                data = response.json()
                new_portrait = data["choices"][0]["message"]["content"].strip()
                # Ensure max 500 chars
                new_portrait = new_portrait[:500]
                save_portrait(birth_data, new_portrait, new_count)
                clear_session_buffer(birth_data)
                return new_portrait
    except Exception as e:
        print(f"[Portrait] Rewrite failed: {e}")

    return old_portrait


def rewrite_portrait_sync(birth_data: Dict, api_key: str, model: str) -> str:
    """Sync version for non-async contexts."""
    old = read_portrait(birth_data)
    old_portrait = old.get('portrait', 'New client — first session')
    old_count = old.get('session_count', 0)
    new_count = old_count + 1

    session = get_session_buffer(birth_data)
    if not session or not session.get('exchanges'):
        return old_portrait

    session_formatted = _format_session_for_rewrite(session)

    prompt = REWRITE_PROMPT.replace("{old_portrait}", old_portrait) \
                            .replace("{session_data}", session_formatted)

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You write dense shorthand that changes how an astrologer responds. 500 chars. Every word must earn its place."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 250,
                "temperature": 0.3,
            },
            timeout=15.0,
        )

        if response.status_code == 200:
            data = response.json()
            new_portrait = data["choices"][0]["message"]["content"].strip()[:500]
            save_portrait(birth_data, new_portrait, new_count)
            clear_session_buffer(birth_data)
            return new_portrait
    except Exception as e:
        print(f"[Portrait] Sync rewrite failed: {e}")

    return old_portrait


# ═══════════════════════════════════════════════════════════════
# BUILD PORTRAIT BLOCK FOR ORACLE
# ═══════════════════════════════════════════════════════════════

def build_portrait_block(birth_data: Dict) -> str:
    """Build the THIS PERSON block for injection into Oracle briefing."""
    data = read_portrait(birth_data)
    portrait = data.get('portrait', '')

    if not portrait:
        return ""

    return f"THIS PERSON:\n{portrait}"
