"""
CHAT — Universal Oracle chat with per-system, topic-sharded memory.

Endpoints:
  POST /api/public/chat          — non-streaming JSON
  POST /api/public/chat/stream   — Server-Sent Events streaming

Per turn flow:
  1. classifier  → topic, secondary, sections, language, emotion
  2. pipeline    → base_chart + sections + portrait block + persona + user style
  3. LLM         → main response (with recent history)
  4. portraits   → async LLM call updates topic packet(s)

The streaming endpoint runs the pipeline INSIDE the generator so the response
opens immediately with a 'start' event (UX feedback at t=0).
"""

import asyncio
import json
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.features._base import extract_birth


router = APIRouter(prefix="/public", tags=["Chat"])


class _ChatRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    message: str
    history: Optional[List[Dict]] = None
    system: Optional[str] = 'bphs'
    language: Optional[str] = 'en'
    current_section: Optional[str] = None
    astrologer_personality: Optional[str] = None
    voice: Optional[bool] = False
    voice_name: Optional[str] = 'nova'


def _build_messages(system_prompt: str, history: Optional[List[Dict]],
                    user_message: str) -> List[Dict]:
    messages: List[Dict] = [{'role': 'system', 'content': system_prompt}]
    for h in (history or [])[-8:]:
        role = h.get('role', 'user') if isinstance(h, dict) else 'user'
        if role not in ('user', 'assistant'):
            role = 'user'
        content = h.get('content', '') if isinstance(h, dict) else str(h)
        if content:
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': user_message})
    return messages


def _history_with_section_hint(history: List[Dict], current_section: Optional[str]) -> List[Dict]:
    out = list(history or [])
    if current_section:
        out.append({'role': 'user',
                    'content': f'(viewing section: {current_section})'})
    return out


def _validate(request_body: _ChatRequest) -> tuple:
    msg = (request_body.message or '').strip()
    if not msg:
        raise HTTPException(status_code=400, detail='Message required')

    birth_data = extract_birth(request_body.kundli_data) or request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail='Birth data required')

    system = (request_body.system or 'bphs').lower()
    return msg, birth_data, system


# ═══════════════════════════════════════════════════════════════
# /chat — non-streaming
# ═══════════════════════════════════════════════════════════════

async def _call_chat_llm(system_prompt: str, history: Optional[List[Dict]],
                         user_message: str, settings, max_tokens: int = 600) -> str:
    messages = _build_messages(system_prompt, history, user_message)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.OPENROUTER_MODEL,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': 0.75,
            },
            timeout=60.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail='AI service unavailable')
    return resp.json()['choices'][0]['message']['content'].strip()


@router.post('/chat')
async def chat(request_body: _ChatRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    msg, birth_data, system = _validate(request_body)
    history = request_body.history or []
    history_for_classifier = _history_with_section_hint(history, request_body.current_section)

    from app.services.oracle.pipeline import process_oracle_query
    try:
        result = await process_oracle_query(
            user_message=msg,
            birth_data=birth_data,
            conversation_history=history_for_classifier,
            system=system,
            astrologer_personality=request_body.astrologer_personality or "",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Pipeline failed: {str(e)[:120]}')

    try:
        reply = await _call_chat_llm(
            result['system_prompt'], history, msg, settings,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'LLM failed: {str(e)[:120]}')

    from app.services.oracle.portraits import normalize_topic, update_user_portraits
    primary = normalize_topic(result['intent'].get('primary', 'general'))
    secondary = result['intent'].get('secondary')
    secondary = normalize_topic(secondary) if secondary else None

    asyncio.create_task(update_user_portraits(
        birth_data=birth_data,
        user_message=msg,
        oracle_response=reply,
        settings=settings,
        system=system,
    ))

    return {
        'reply': reply,
        'topic': primary,
        'secondary_topic': secondary,
        'system': system,
        'language': result['intent'].get('language'),
        'sections_used': result.get('sections_built', []),
        'cache_hit': result.get('cache_hit', False),
        'processing_time_ms': result.get('processing_time_ms', 0),
        'version': 4,
        'cache_ttl_seconds': 0,
    }


# ═══════════════════════════════════════════════════════════════
# /chat/stream — Server-Sent Events
# ═══════════════════════════════════════════════════════════════


async def _tts_sentence(text: str, settings, voice_name: str = "nova") -> Optional[str]:
    """Call OpenAI TTS for one sentence. Returns base64 mp3 or None on failure."""
    text = (text or "").strip()
    if not text or len(text) > 4000:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice_name,
                    "response_format": "mp3",
                },
            )
        if resp.status_code != 200:
            return None
        import base64
        return base64.b64encode(resp.content).decode("utf-8")
    except Exception:
        return None


_SENTENCE_ENDS = [". ", "! ", "? ", ".\n", "!\n", "?\n", ".\"", "!\"", "?\"", "."]


def _extract_sentence(buffer: str):
    """Return (complete_sentence, remaining_buffer) or (None, buffer) if no end yet."""
    earliest = -1
    earliest_len = 0
    for ch in _SENTENCE_ENDS:
        idx = buffer.find(ch)
        if idx >= 0 and (earliest < 0 or idx < earliest):
            earliest = idx
            earliest_len = len(ch)
    if earliest < 0:
        return None, buffer
    end = earliest + earliest_len
    complete = buffer[:end].strip()
    if len(complete) < 15:
        return None, buffer  # too short, keep accumulating
    return complete, buffer[end:]


@router.post('/chat/stream')
async def chat_stream(request_body: _ChatRequest, request: Request):
    from app.core.config import settings
    from app.core.rate_limiter import check_rate_limit

    check_rate_limit(request, 'feature', getattr(settings, 'RATE_LIMIT_FEATURE', 60))

    msg, birth_data, system = _validate(request_body)
    history = request_body.history or []
    history_for_classifier = _history_with_section_hint(history, request_body.current_section)

    async def event_stream():
        # 1. Immediate ack — opens HTTP response at t=0
        yield 'data: ' + json.dumps({'type': 'start'}) + '\n\n'

        # 2. Pipeline (classifier + engine in parallel + portrait + persona)
        from app.services.oracle.pipeline import process_oracle_query
        try:
            result = await process_oracle_query(
                user_message=msg, birth_data=birth_data,
                conversation_history=history_for_classifier,
                system=system,
                astrologer_personality=request_body.astrologer_personality or "",
            )
        except Exception as e:
            yield 'data: ' + json.dumps({
                'type': 'error', 'message': f'Pipeline failed: {str(e)[:120]}',
            }) + '\n\n'
            return

        from app.services.oracle.portraits import normalize_topic, update_user_portraits
        primary = normalize_topic(result['intent'].get('primary', 'general'))
        secondary = result['intent'].get('secondary')
        secondary = normalize_topic(secondary) if secondary else None

        # 3. Meta event
        yield 'data: ' + json.dumps({
            'type': 'meta',
            'topic': primary,
            'secondary_topic': secondary,
            'system': system,
            'language': result['intent'].get('language'),
            'sections_used': result.get('sections_built', []),
        }) + '\n\n'

        # 4. Main LLM stream + parallel TTS per sentence
        messages = _build_messages(result['system_prompt'], history, msg)
        full_text = ''
        voice_enabled = bool(request_body.voice)
        voice_name = request_body.voice_name or 'nova'

        # Queue carries both text deltas and audio chunks for ordered yield
        event_queue: asyncio.Queue = asyncio.Queue()
        pending_tts = [0]  # mutable counter
        text_done = [False]

        async def tts_worker(sentence_text: str, seq: int):
            audio_b64 = await _tts_sentence(sentence_text, settings, voice_name)
            if audio_b64:
                await event_queue.put({
                    'type': 'audio',
                    'seq': seq,
                    'mime': 'audio/mpeg',
                    'data': audio_b64,
                    'text': sentence_text,
                })
            pending_tts[0] -= 1

        async def text_producer():
            nonlocal full_text
            sentence_buffer = ''
            sentence_seq = 0
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    async with client.stream(
                        'POST',
                        'https://openrouter.ai/api/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                            'Content-Type': 'application/json',
                        },
                        json={
                            'model': settings.OPENROUTER_MODEL,
                            'messages': messages,
                            'max_tokens': 600,
                            'temperature': 0.75,
                            'stream': True,
                        },
                    ) as resp:
                        if resp.status_code != 200:
                            await event_queue.put({
                                'type': 'error',
                                'message': f'AI service HTTP {resp.status_code}',
                            })
                            return

                        async for line in resp.aiter_lines():
                            if await request.is_disconnected():
                                return
                            if not line or not line.startswith('data: '):
                                continue
                            payload = line[6:].strip()
                            if payload == '[DONE]':
                                break
                            try:
                                chunk = json.loads(payload)
                                delta = chunk.get('choices', [{}])[0].get('delta', {})
                                text = delta.get('content', '')
                                if text:
                                    full_text += text
                                    sentence_buffer += text
                                    await event_queue.put({
                                        'type': 'delta', 'text': text,
                                    })

                                    # Sentence boundary check (fire TTS asynchronously)
                                    if voice_enabled:
                                        while True:
                                            complete, sentence_buffer = _extract_sentence(sentence_buffer)
                                            if not complete:
                                                break
                                            sentence_seq += 1
                                            pending_tts[0] += 1
                                            asyncio.create_task(tts_worker(complete, sentence_seq))
                            except Exception:
                                continue

                # Flush any tail buffer as final sentence
                if voice_enabled and sentence_buffer.strip():
                    sentence_seq += 1
                    pending_tts[0] += 1
                    asyncio.create_task(tts_worker(sentence_buffer.strip(), sentence_seq))
            except Exception as e:
                await event_queue.put({
                    'type': 'error', 'message': str(e)[:120],
                })
            finally:
                text_done[0] = True

        # Run text producer, drain queue
        producer_task = asyncio.create_task(text_producer())
        while True:
            if text_done[0] and pending_tts[0] == 0 and event_queue.empty():
                break
            try:
                evt = await asyncio.wait_for(event_queue.get(), timeout=0.2)
            except asyncio.TimeoutError:
                if await request.is_disconnected():
                    producer_task.cancel()
                    return
                continue
            yield 'data: ' + json.dumps(evt) + '\n\n'
            if evt.get('type') == 'error':
                return

        # 5. Done event
        yield 'data: ' + json.dumps({
            'type': 'done',
            'full_text': full_text,
            'topic': primary,
            'secondary_topic': secondary,
            'system': system,
            'language': result['intent'].get('language'),
            'sections_used': result.get('sections_built', []),
            'processing_time_ms': result.get('processing_time_ms', 0),
            'version': 4,
        }) + '\n\n'

        # 6. Fire portrait update (async, doesn't block)
        if full_text:
            asyncio.create_task(update_user_portraits(
                birth_data=birth_data,
                user_message=msg,
                oracle_response=full_text,
                settings=settings,
                system=system,
            ))

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


# ═══════════════════════════════════════════════════════════════
# /chat/reset
# ═══════════════════════════════════════════════════════════════

@router.post('/chat/reset')
async def chat_reset(request_body: dict, request: Request):
    """Drop any client-side notion of session (portraits stay — they're persistent)."""
    return {'ok': True}


chat_router = router
