"""
JYOTISH API - COMPLETE ORACLE SYSTEM
v2: Rate limiting, input validation, fixed hardcoded coords
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel, field_validator
from typing import Optional
import httpx
import tempfile
import os
from datetime import datetime
from app.core.config import settings
from app.core.rate_limiter import check_rate_limit

router = APIRouter(prefix="/public", tags=["Public"])


class ChatRequest(BaseModel):
    message: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"
    history: Optional[list] = []
    system: Optional[str] = "bphs"  # "bphs" | "kp" | "western" | "chinese"
    gender: Optional[str] = None     # "male" | "female" — used by Chinese Da Yun
    kp_number: Optional[int] = None  # 1-249 — used by KP Horary

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 2000:
            raise ValueError("Message too long (max 2000 chars)")
        return v


class KundliRequest(BaseModel):
    name: str
    date: dict
    time: dict
    place: dict

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("Name must be 1-100 characters")
        return v


def _validate_birth_params(date_dict: dict, time_dict: dict, place_dict: dict):
    try:
        year = int(date_dict.get("year", 0))
        month = int(date_dict.get("month", 0))
        day = int(date_dict.get("day", 0))
        hour = int(time_dict.get("hour", 0))
        minute = int(time_dict.get("minute", 0))
        lat = float(place_dict.get("lat", 0))
        lon = float(place_dict.get("lng", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid birth data format")

    if not (1900 <= year <= 2100):
        raise HTTPException(status_code=400, detail=f"Year must be 1900-2100, got {year}")
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail=f"Month must be 1-12, got {month}")
    if not (1 <= day <= 31):
        raise HTTPException(status_code=400, detail=f"Day must be 1-31, got {day}")
    if not (0 <= hour <= 23):
        raise HTTPException(status_code=400, detail=f"Hour must be 0-23, got {hour}")
    if not (0 <= minute <= 59):
        raise HTTPException(status_code=400, detail=f"Minute must be 0-59, got {minute}")
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail=f"Latitude must be -90 to 90, got {lat}")
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail=f"Longitude must be -180 to 180, got {lon}")

    try:
        birth_dt = datetime(year, month, day, hour, minute)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date: {e}")

    return year, month, day, hour, minute, lat, lon, birth_dt


# ═══════════════════════════════════════════════════════════════
# ORACLE CHAT — Powered by 100+ calculation systems
# ═══════════════════════════════════════════════════════════════

def _extract_birth_data(kundli_data: dict) -> dict:
    """Extract birth data from kundli_data format for Oracle pipeline."""
    if not kundli_data:
        return None

    raw = kundli_data.get("raw", {})
    birth = raw.get("birth_details", {})
    if not birth:
        birth = kundli_data.get("birth_details", {})

    if not birth:
        return None

    try:
        return {
            'year': int(birth.get('year', 2000)),
            'month': int(birth.get('month', 1)),
            'day': int(birth.get('day', 1)),
            'hour': int(birth.get('hour', 12)),
            'minute': int(birth.get('minute', 0)),
            'lat': float(birth.get('latitude', 28.6139)),
            'lng': float(birth.get('longitude', 77.2090)),
        }
    except (TypeError, ValueError):
        return None


@router.post("/chat")
async def oracle_chat(request_body: ChatRequest, request: Request):
    check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)

    try:
        from app.services.oracle.pipeline import process_oracle_query

        # Extract birth data from kundli
        # Accept both kundli_data (app format) and birth_data (test format)
        birth_data = _extract_birth_data(request_body.kundli_data)
        if not birth_data and request_body.birth_data:
            birth_data = request_body.birth_data

        # Rewrite portrait from previous session if needed
        if birth_data:
            try:
                from app.services.oracle.portrait import get_session_buffer, rewrite_portrait_sync
                buf = get_session_buffer(birth_data)
                if buf and buf.get('exchanges'):
                    # Check if last exchange was >10 min ago (new session)
                    from datetime import datetime as dt_check
                    last_started = buf.get('last_exchange', buf.get('started', ''))
                    if last_started:
                        last_dt = dt_check.fromisoformat(last_started)
                        gap = (dt_check.now() - last_dt).total_seconds()
                        if gap > 600:  # 10 minutes = new session
                            rewrite_portrait_sync(
                                birth_data, settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL
                            )
            except Exception:
                pass

        # Build conversation history
        history = []
        if request_body.history:
            for msg in request_body.history[-8:]:
                if msg.get("role") == "user":
                    history.append(msg.get("content", ""))

        # Run Oracle pipeline (classify → cache → assemble → prompt)
        oracle_result = process_oracle_query(
            request_body.message,
            birth_data,
            history,
            system=request_body.system or "bphs",
            extras={
                'gender': request_body.gender,
                'kp_number': request_body.kp_number,
            },
        )


        system_prompt = oracle_result['system_prompt']
        briefing = oracle_result.get('data_packet', {}).get('oracle_briefing', '')

        # ─── Full LLM response ───
        api_messages = [{"role": "system", "content": system_prompt}]
        if request_body.history:
            for msg in request_body.history[-8:]:
                role = msg.get("role", "user")
                if role == "oracle":
                    role = "assistant"
                if role in ["user", "assistant"]:
                    api_messages.append({"role": role, "content": msg.get("content", "")})
        if not request_body.history or request_body.history[-1].get("content") != request_body.message:
            api_messages.append({"role": "user", "content": request_body.message})
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": api_messages,
                    "max_tokens": 500,
                    "temperature": 0.75,
                },
                timeout=60.0,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="AI service unavailable")
            data = response.json()
            oracle_response = data["choices"][0]["message"]["content"]

        # Log conversation for research
        try:
            import json as jjson
            from pathlib import Path
            log_dir = Path("/var/www/jyotish/backend/logs")
            log_dir.mkdir(exist_ok=True)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "message": request_body.message,
                "response": oracle_response,
                "hook": "",
                "intent": oracle_result['intent']['primary'],
                "language": oracle_result['intent'].get('language', 'en'),
                "processing_ms": oracle_result['processing_time_ms'],
            }
            with open(log_dir / "conversations.jsonl", "a") as lf:
                lf.write(jjson.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # Split hook from response
        hook_line = ""
        if oracle_response and "\n\n" in oracle_response:
            parts = oracle_response.rsplit("\n\n", 1)
            last = parts[-1].strip()
            hook_starters = ["I notice", "I see", "There is", "There's", "Interestingly",
                             "What's interesting", "One thing", "Something",
                             "दिलचस्प", "मैंने देखा", "मुझे दिख", "एक और बात",
                             "मैं देख", "यहाँ एक", "आपके", "विशेष",
                             "注意到", "有趣的是", "值得注意",
                             "Noto que", "Percebo", "Lo interesante",
                             "気づいた", "興味深い"]
            if any(last.startswith(s) for s in hook_starters):
                oracle_response = parts[0].strip()
                hook_line = last

        # Track exchange in portrait session buffer
        try:
            from app.services.oracle.portrait import add_exchange
            add_exchange(
                birth_data,
                request_body.message,
                oracle_response,
                classifier_output=oracle_result.get('intent', {}),
                sections_used=oracle_result.get('sections_built', []),
                system=request_body.system or "bphs",
            )
        except Exception:
            pass

        # Return response with metadata
        return {
            "response": oracle_response,
            "hook": hook_line,
            "intent": oracle_result['intent']['primary'],
            "tone": oracle_result['intent']['tone'],
            "confidence": oracle_result['intent']['confidence'],
            "methods_used": len(oracle_result['methods_fired']),
            "classifier": oracle_result['intent'].get('classifier', 'unknown'),
            "processing_ms": oracle_result['processing_time_ms'],
            "follow_ups": oracle_result['intent'].get('follow_up_suggestions', []),
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


# ═══════════════════════════════════════════════════════════════
# FEATURE ENDPOINTS — minimal anchor/line/hold/thread shape
# ═══════════════════════════════════════════════════════════════

class FeatureRequest(BaseModel):
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


async def _render_feature(feature_id: str, request_body: FeatureRequest, request: Request):
    """Shared handler: build engine, call writer, attach thread, return."""
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from datetime import datetime
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.writers import write_feature, extract_context
        from app.services.features.threads import pick_thread

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])

        # Produce the minimal reading
        reading = write_feature(feature_id, engine, language=getattr(request_body, 'language', 'en') or 'en')

        # Attach thread based on chart context
        ctx = extract_context(engine)
        thread = pick_thread(feature_id, ctx)

        return {
            'feature_id': feature_id,
            'anchor': reading.get('anchor', ''),
            'line': reading.get('line', ''),
            'hold': reading.get('hold', ''),
            'math': reading.get('math', {}),
            'thread': thread,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Feature error: {str(e)[:200]}")


@router.post("/daily-vibe")
async def feature_daily_vibe(body: FeatureRequest, request: Request):
    return await _render_feature("daily-vibe", body, request)

@router.post("/power-hours")
async def feature_power_hours(body: FeatureRequest, request: Request):
    return await _render_feature("power-hours", body, request)

@router.post("/planet-strength")
async def feature_planet_strength(body: FeatureRequest, request: Request):
    return await _render_feature("planet-strength", body, request)

@router.post("/year-map")
async def feature_year_map(body: FeatureRequest, request: Request):
    return await _render_feature("year-map", body, request)

@router.post("/danger-radar")
async def feature_danger_radar(body: FeatureRequest, request: Request):
    return await _render_feature("danger-radar", body, request)

@router.post("/gemstone-profile")
async def feature_gemstone(body: FeatureRequest, request: Request):
    return await _render_feature("gemstone-profile", body, request)

@router.post("/personal-deities")
async def feature_deities(body: FeatureRequest, request: Request):
    return await _render_feature("personal-deities", body, request)

@router.post("/soul-profile-v2")
async def feature_soul_profile_v2(body: FeatureRequest, request: Request):
    return await _render_feature("soul-profile", body, request)

@router.post("/rare-traits")
async def feature_rare_traits(body: FeatureRequest, request: Request):
    return await _render_feature("rare-traits", body, request)

@router.post("/cosmic-novel")
async def feature_cosmic_novel(body: FeatureRequest, request: Request):
    return await _render_feature("cosmic-novel", body, request)

@router.post("/money-calendar")
async def feature_money_calendar(body: FeatureRequest, request: Request):
    return await _render_feature("money-calendar", body, request)

@router.post("/festivals")
async def feature_festivals(body: FeatureRequest, request: Request):
    return await _render_feature("festivals", body, request)

@router.post("/ideal-partner")
async def feature_ideal_partner(body: FeatureRequest, request: Request):
    return await _render_feature("ideal-partner", body, request)

@router.post("/active-yogas")
async def feature_active_yogas(body: FeatureRequest, request: Request):
    return await _render_feature("active-yogas", body, request)

@router.post("/health-map")
async def feature_health_map(body: FeatureRequest, request: Request):
    return await _render_feature("health-map", body, request)

@router.post("/career-path")
async def feature_career_path(body: FeatureRequest, request: Request):
    return await _render_feature("career-path", body, request)

@router.post("/eclipse-impact")
async def feature_eclipse_impact(body: FeatureRequest, request: Request):
    return await _render_feature("eclipse-impact", body, request)

@router.post("/nadi-reading")
async def feature_nadi_reading(body: FeatureRequest, request: Request):
    return await _render_feature("nadi-reading", body, request)

@router.post("/weekly-forecast")
async def feature_weekly_forecast(body: FeatureRequest, request: Request):
    return await _render_feature("weekly-forecast", body, request)

@router.post("/numerology")
async def feature_numerology(body: FeatureRequest, request: Request):
    return await _render_feature("numerology", body, request)

@router.post("/vastu")
async def feature_vastu(body: FeatureRequest, request: Request):
    return await _render_feature("vastu", body, request)

@router.post("/nakshatra-profile")
async def feature_nakshatra_profile(body: FeatureRequest, request: Request):
    return await _render_feature("nakshatra-profile", body, request)


# ═══════════════════════════════════════════════════════════════
# PLANET DETAIL — Deep single-planet reading with LLM interpretation
# ═══════════════════════════════════════════════════════════════

class PlanetDetailRequest(BaseModel):
    planet: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"

    @field_validator("planet")
    @classmethod
    def planet_valid(cls, v):
        valid = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
        if v not in valid:
            raise ValueError(f"Planet must be one of: {', '.join(valid)}")
        return v


@router.post("/planet-detail")
async def get_planet_detail(request_body: PlanetDetailRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.planet_detail import build_planet_detail, build_llm_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])

        # Build structured planet data
        planet_data = build_planet_detail(engine, request_body.planet, request_body.language or 'en')

        if 'error' in planet_data:
            raise HTTPException(status_code=400, detail=planet_data['error'])

        # Build LLM prompt and get interpretation
        system_prompt = build_llm_prompt(planet_data, request_body.language or 'en')
        user_prompt = f"Read {request_body.planet} in my chart."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 350,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        interpretation = ""
        if response.status_code == 200:
            data = response.json()
            interpretation = data["choices"][0]["message"]["content"].strip()

        # Split interpretation into three sections
        about = interpretation
        significance = ""
        current_effect = ""
        parts = [p.strip() for p in interpretation.split("\n\n") if p.strip()]
        if len(parts) >= 3:
            about = parts[0]
            significance = parts[1]
            current_effect = parts[2]
        elif len(parts) == 2:
            about = parts[0]
            current_effect = parts[1]

        # Remove briefing from response (internal only)
        planet_data.pop('briefing', None)

        return {
            'planet_data': planet_data,
            'about': about,
            'significance': significance,
            'current_effect': current_effect,
            'full_reading': interpretation,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Planet detail error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# LIFE STORY — Complete life chapters
# ═══════════════════════════════════════════════════════════════

@router.post("/life-story")
async def get_life_story(request_body: FeatureRequest, request: Request):
    """Return all life chapters (dasha periods) with metadata."""
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.life_story import build_life_story

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        story = build_life_story(engine, request_body.language or 'en')

        story.pop('briefing', None)
        return story

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Life story error: {str(e)[:200]}")


class ChapterReadRequest(BaseModel):
    chapter_index: int
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


@router.post("/life-story/chapter")
async def get_chapter_reading(request_body: ChapterReadRequest, request: Request):
    """Get LLM-written reading for a single life chapter."""
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.life_story import build_life_story, build_chapter_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        story = build_life_story(engine, request_body.language or 'en')

        idx = request_body.chapter_index
        chapters = story.get('chapters', [])
        if idx < 1 or idx > len(chapters):
            raise HTTPException(status_code=400, detail=f"Chapter index must be 1-{len(chapters)}")

        chapter = chapters[idx - 1]
        system_prompt = build_chapter_prompt(chapter, story, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Write chapter {idx}: {chapter['title']}"},
                    ],
                    "max_tokens": 250,
                    "temperature": 0.75,
                },
                timeout=30.0,
            )

        reading = ""
        if response.status_code == 200:
            data = response.json()
            reading = data["choices"][0]["message"]["content"].strip()

        return {
            'chapter': chapter,
            'reading': reading,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chapter reading error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# PAST LIFE — Who you were before
# ═══════════════════════════════════════════════════════════════

@router.post("/past-life")
async def get_past_life(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.past_life import build_past_life, build_past_life_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        past_data = build_past_life(engine, request_body.language or 'en')

        system_prompt = build_past_life_prompt(past_data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Tell me about my past life."},
                    ],
                    "max_tokens": 400,
                    "temperature": 0.8,
                },
                timeout=30.0,
            )

        story_text = ""
        if response.status_code == 200:
            data = response.json()
            story_text = data["choices"][0]["message"]["content"].strip()

        # Split into segments by ---
        segments = [s.strip() for s in story_text.split('---') if s.strip()]
        # Ensure we have 5 segments
        while len(segments) < 5:
            segments.append('')

        past_data.pop('briefing', None)

        return {
            'past_life_data': past_data,
            'segments': segments[:5],
            'full_story': story_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Past life error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# FOUR PILLARS — Kama · Karma · Dharma · Moksha
# ═══════════════════════════════════════════════════════════════

@router.post("/four-pillars")
async def get_four_pillars(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.four_pillars import build_four_pillars, build_pillars_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_four_pillars(engine, request_body.language or 'en')

        system_prompt = build_pillars_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Read my four pillars."},
                    ],
                    "max_tokens": 450,
                    "temperature": 0.75,
                },
                timeout=30.0,
            )

        llm_text = ""
        if response.status_code == 200:
            resp_data = response.json()
            llm_text = resp_data["choices"][0]["message"]["content"].strip()

        # Parse LLM response into structured pillars
        parsed = _parse_pillars_response(llm_text)

        data.pop('briefing', None)

        return {
            'pillars_data': data['pillars'],
            'ascendant': data['ascendant'],
            'readings': parsed,
            'raw_text': llm_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Four pillars error: {str(e)[:200]}")


def _parse_pillars_response(text: str) -> dict:
    """Parse LLM response into per-pillar word + note + closing."""
    result = {'kama': {}, 'karma': {}, 'dharma': {}, 'moksha': {}, 'closing': ''}
    current = None

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        upper = line.upper()
        if upper.startswith('KAMA'):
            current = 'kama'; continue
        elif upper.startswith('KARMA'):
            current = 'karma'; continue
        elif upper.startswith('DHARMA'):
            current = 'dharma'; continue
        elif upper.startswith('MOKSHA'):
            current = 'moksha'; continue
        elif upper.startswith('CLOSING'):
            current = 'closing'; continue

        if current == 'closing':
            result['closing'] = line
            continue

        if current and current in result and isinstance(result[current], dict):
            lower = line.lower()
            if lower.startswith('word:'):
                result[current]['word'] = line.split(':', 1)[1].strip().rstrip('.')
            elif lower.startswith('note:'):
                result[current]['note'] = line.split(':', 1)[1].strip()
            elif 'note' not in result[current] and 'word' in result[current]:
                # continuation of note
                existing = result[current].get('note', '')
                result[current]['note'] = (existing + ' ' + line).strip() if existing else line

    return result


# ═══════════════════════════════════════════════════════════════
# TODAY — What the day holds
# ═══════════════════════════════════════════════════════════════

@router.post("/today")
async def get_today(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.today_sky import build_today, build_today_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        today_data = build_today(engine, request_body.language or 'en')

        system_prompt = build_today_prompt(today_data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Tell me about today."},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        reading = ""
        if response.status_code == 200:
            resp_data = response.json()
            reading = resp_data["choices"][0]["message"]["content"].strip()

        today_data.pop('briefing', None)

        return {
            'today': today_data,
            'reading': reading,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Today error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# KP HOUSE CLOCK — 12 houses via cuspal sub-lord theory
# ═══════════════════════════════════════════════════════════════

@router.post("/kp-house-clock")
async def get_kp_house_clock(request_body: FeatureRequest, request: Request):
    """Return all 12 houses with KP analysis."""
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.kp_house_clock import build_kp_house_clock

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_kp_house_clock(engine, request_body.language or 'en')

        data.pop('briefing', None)
        return data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"KP house clock error: {str(e)[:200]}")


class KPHouseReadRequest(BaseModel):
    house: int
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"

    @field_validator("house")
    @classmethod
    def house_valid(cls, v):
        if v < 1 or v > 12:
            raise ValueError("House must be 1-12")
        return v


@router.post("/kp-house-clock/read")
async def read_kp_house(request_body: KPHouseReadRequest, request: Request):
    """Get LLM reading for a single house."""
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.kp_house_clock import build_kp_house_clock, build_house_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_kp_house_clock(engine, request_body.language or 'en')

        houses = data.get('houses', [])
        idx = request_body.house - 1
        if idx < 0 or idx >= len(houses):
            raise HTTPException(status_code=400, detail="Invalid house")

        house_data = houses[idx]
        system_prompt = build_house_prompt(house_data, houses, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Read house {request_body.house}."},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        reading_text = ""
        if response.status_code == 200:
            resp = response.json()
            reading_text = resp["choices"][0]["message"]["content"].strip()

        # Split into 3 parts
        parts = [p.strip() for p in reading_text.split('---') if p.strip()]
        while len(parts) < 3:
            parts.append('')

        return {
            'house_data': house_data,
            'life_area_text': parts[0],
            'verdict_text': parts[1],
            'insight_text': parts[2],
            'full_reading': reading_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"KP house read error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# KP HORARY — Number-based instant prediction
# ═══════════════════════════════════════════════════════════════

class KPHoraryRequest(BaseModel):
    number: int
    question: Optional[str] = ""
    category: Optional[str] = "general"
    kundli_data: Optional[dict] = None
    language: Optional[str] = "en"

    @field_validator("number")
    @classmethod
    def number_valid(cls, v):
        if v < 1 or v > 249:
            raise ValueError("Number must be 1-249")
        return v


@router.post("/kp-horary")
async def get_kp_horary(request_body: KPHoraryRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    try:
        from app.services.features.kp_horary_feature import build_kp_horary, build_horary_prompt

        # Get location from kundli if available
        lat, lng = 25.35, 74.64
        if request_body.kundli_data:
            bd = _extract_birth_data(request_body.kundli_data)
            if bd:
                lat = bd.get('lat', lat)
                lng = bd.get('lng', lng)

        data = build_kp_horary(
            number=request_body.number,
            question=request_body.question or '',
            category=request_body.category or 'general',
            latitude=lat,
            longitude=lng,
        )

        system_prompt = build_horary_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Number {request_body.number}. {request_body.question or 'What does the universe say?'}"},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.8,
                },
                timeout=30.0,
            )

        reading = ""
        if response.status_code == 200:
            resp = response.json()
            reading = resp["choices"][0]["message"]["content"].strip()

        data.pop('briefing', None)

        return {
            'horary': data,
            'reading': reading,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"KP horary error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# THE WORD — Quick KP yes/no on life topics
# ═══════════════════════════════════════════════════════════════

class TheWordRequest(BaseModel):
    topic: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


@router.post("/the-word")
async def get_the_word(request_body: TheWordRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.the_word import build_the_word, build_word_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_the_word(engine, request_body.topic, request_body.language or 'en')

        if 'error' in data:
            raise HTTPException(status_code=400, detail=data['error'])

        system_prompt = build_word_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"The word on {request_body.topic}."},
                    ],
                    "max_tokens": 60,
                    "temperature": 0.8,
                },
                timeout=30.0,
            )

        line = ""
        if response.status_code == 200:
            resp = response.json()
            line = resp["choices"][0]["message"]["content"].strip().strip('"').strip("'")

        data.pop('briefing', None)

        return {
            'topic': data['topic'],
            'question': data['question'],
            'answer': data['answer'],
            'confidence': data['confidence'],
            'line': line,
            'house': data['house'],
            'csl': data['csl'],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"The word error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# THE BLUNT SEER — Astrological roast
# ═══════════════════════════════════════════════════════════════

@router.post("/blunt-seer")
async def get_blunt_seer(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.blunt_seer import build_blunt_seer, build_roast_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_blunt_seer(engine, request_body.language or 'en')

        system_prompt = build_roast_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Roast me."},
                    ],
                    "max_tokens": 200,
                    "temperature": 1.0,
                },
                timeout=30.0,
            )

        roast = ""
        if response.status_code == 200:
            resp = response.json()
            roast = resp["choices"][0]["message"]["content"].strip()

        data.pop('briefing', None)

        return {
            'seer_data': data,
            'roast': roast,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Blunt seer error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# WESTERN PLANET — Single planet with all aspects
# ═══════════════════════════════════════════════════════════════

class WesternPlanetRequest(BaseModel):
    planet: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"

    @field_validator("planet")
    @classmethod
    def planet_valid(cls, v):
        valid = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
        if v not in valid:
            raise ValueError(f"Planet must be one of: {', '.join(valid)}")
        return v


@router.post("/western-planet")
async def get_western_planet(request_body: WesternPlanetRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.western_planets import build_western_planet, build_western_planet_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_western_planet(engine, request_body.planet, request_body.language or 'en')

        if 'error' in data:
            raise HTTPException(status_code=400, detail=data['error'])

        system_prompt = build_western_planet_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Read {request_body.planet} and its aspects."},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        reading_text = ""
        if response.status_code == 200:
            resp = response.json()
            reading_text = resp["choices"][0]["message"]["content"].strip()

        # Clean LLM label headers
        import re
        reading_text = re.sub(r'(?i)^PART\s*\d+\s*[—\-:]+\s*(SIGNIFICANCE|ASPECTS)\s*\n?', '', reading_text, flags=re.MULTILINE).strip()

        # Split into significance + aspects
        significance = reading_text
        aspects_text = ""
        if "===" in reading_text:
            parts = reading_text.split("===", 1)
            significance = parts[0].strip()
            aspects_text = parts[1].strip()
        else:
            # LLM often skips ===. Split by finding aspect lines.
            # Aspect lines match: "{planet} {aspect_word} {other} —"
            aspect_words = ['conjunct', 'conjunction', 'oppose', 'opposition', 'trine', 'square', 'sextile', 'quincunx', 'semi-square']
            lines = reading_text.split('\n')
            sig_lines = []
            asp_lines = []
            found_aspects = False
            planet_lower = request_body.planet.lower()
            for line in lines:
                line_lower = line.strip().lower()
                if not found_aspects and any(
                    line_lower.startswith(planet_lower) and aw in line_lower
                    for aw in aspect_words
                ):
                    found_aspects = True
                if found_aspects:
                    asp_lines.append(line)
                else:
                    sig_lines.append(line)
            if asp_lines:
                significance = '\n'.join(sig_lines).strip()
                aspects_text = '\n'.join(asp_lines).strip()

        data.pop('briefing', None)

        return {
            'planet_data': data,
            'significance': significance,
            'aspects_reading': aspects_text,
            'full_reading': reading_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Western planet error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# TIME READING — Today · Week · Month
# ═══════════════════════════════════════════════════════════════

@router.post("/time-reading")
async def get_time_reading(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.time_reading import build_time_reading, build_time_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_time_reading(engine, request_body.language or 'en')

        system_prompt = build_time_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Read my time — today, this week, this month."},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        reading_text = ""
        if response.status_code == 200:
            resp = response.json()
            reading_text = resp["choices"][0]["message"]["content"].strip()

        # Split into 3 segments
        segments = [s.strip() for s in reading_text.split('---') if s.strip()]
        while len(segments) < 3:
            segments.append('')

        data.pop('briefing', None)

        return {
            'time_data': data,
            'today_reading': segments[0],
            'week_reading': segments[1],
            'month_reading': segments[2],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Time reading error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# FIVE ELEMENTS — Chinese element wheel
# ═══════════════════════════════════════════════════════════════

@router.post("/five-elements")
async def get_five_elements(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.five_elements import build_five_elements

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_five_elements(engine, request_body.language or 'en')
        data.pop('briefing', None)
        return data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Five elements error: {str(e)[:200]}")


class ElementReadRequest(BaseModel):
    element: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"

    @field_validator("element")
    @classmethod
    def element_valid(cls, v):
        valid = ['Wood', 'Fire', 'Earth', 'Metal', 'Water']
        if v not in valid:
            raise ValueError(f"Element must be one of: {', '.join(valid)}")
        return v


@router.post("/five-elements/read")
async def read_element(request_body: ElementReadRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.five_elements import build_five_elements, build_element_prompt

        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0),
        )
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_five_elements(engine, request_body.language or 'en')

        elem_data = None
        for e in data.get('elements', []):
            if e['element'] == request_body.element:
                elem_data = e
                break
        if not elem_data:
            raise HTTPException(status_code=400, detail="Element not found")

        system_prompt = build_element_prompt(elem_data, data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Tell me about {request_body.element} in my chart."},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )

        reading = ""
        if response.status_code == 200:
            resp = response.json()
            reading = resp["choices"][0]["message"]["content"].strip()

        return {
            'element_data': elem_data,
            'reading': reading,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Element read error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# THE ZOO — 4 Chinese pillar animals
# ═══════════════════════════════════════════════════════════════

@router.post("/the-zoo")
async def get_the_zoo(request_body: FeatureRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))
    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")
    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.the_zoo import build_the_zoo
        birth_dt = datetime(birth_data['year'], birth_data['month'], birth_data['day'], birth_data.get('hour', 12), birth_data.get('minute', 0))
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_the_zoo(engine, request_body.language or 'en')
        data.pop('briefing', None)
        return data
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"The zoo error: {str(e)[:200]}")


class ZooReadRequest(BaseModel):
    pillar: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"

    @field_validator("pillar")
    @classmethod
    def pillar_valid(cls, v):
        if v not in ['year', 'month', 'day', 'hour']:
            raise ValueError("Pillar must be year, month, day, or hour")
        return v


@router.post("/the-zoo/read")
async def read_zoo_animal(request_body: ZooReadRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))
    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")
    try:
        from app.services.oracle.engine_cache import get_cached_engine
        from app.services.features.the_zoo import build_the_zoo, build_zoo_prompt
        birth_dt = datetime(birth_data['year'], birth_data['month'], birth_data['day'], birth_data.get('hour', 12), birth_data.get('minute', 0))
        engine, _cached = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
        data = build_the_zoo(engine, request_body.language or 'en')
        animal_data = None
        for a in data.get('animals', []):
            if a['pillar'] == request_body.pillar:
                animal_data = a; break
        if not animal_data:
            raise HTTPException(status_code=400, detail="Pillar not found")
        system_prompt = build_zoo_prompt(animal_data, data, request_body.language or 'en')
        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.OPENROUTER_MODEL, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Read my {request_body.pillar} animal."},
                ], "max_tokens": 200, "temperature": 0.75}, timeout=30.0)
        reading = ""
        if response.status_code == 200:
            reading = response.json()["choices"][0]["message"]["content"].strip()
        return {'animal_data': animal_data, 'reading': reading}
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Zoo read error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# NAME CORRECTION — Numerological name analysis
# ═══════════════════════════════════════════════════════════════

class NameCorrectionRequest(BaseModel):
    name: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


@router.post("/name-correction")
async def get_name_correction(request_body: NameCorrectionRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")
    if not request_body.name or len(request_body.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name required")

    try:
        from app.services.features.name_correction import build_name_correction, build_name_prompt
        from datetime import date as dt_date

        bd = dt_date(birth_data['year'], birth_data['month'], birth_data['day'])
        data = build_name_correction(request_body.name.strip(), bd, request_body.language or 'en')

        system_prompt = build_name_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.OPENROUTER_MODEL, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze my name: {request_body.name}"},
                ], "max_tokens": 250, "temperature": 0.7}, timeout=30.0)

        reading = ""
        if response.status_code == 200:
            reading = response.json()["choices"][0]["message"]["content"].strip()

        data.pop('briefing', None)
        return {'name_data': data, 'reading': reading}

    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Name correction error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# CORE NUMBERS — All key numerology numbers
# ═══════════════════════════════════════════════════════════════

@router.post("/core-numbers")
async def get_core_numbers(request_body: NameCorrectionRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))

    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")

    try:
        from app.services.features.core_numbers import build_core_numbers, build_core_numbers_prompt
        from datetime import date as dt_date

        bd = dt_date(birth_data['year'], birth_data['month'], birth_data['day'])
        data = build_core_numbers(bd, request_body.name or '', request_body.language or 'en')

        system_prompt = build_core_numbers_prompt(data, request_body.language or 'en')

        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.OPENROUTER_MODEL, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Read my numbers."},
                ], "max_tokens": 300, "temperature": 0.7}, timeout=30.0)

        reading = ""
        if response.status_code == 200:
            reading = response.json()["choices"][0]["message"]["content"].strip()

        data.pop('briefing', None)
        return {'numbers_data': data, 'reading': reading}

    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Core numbers error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# BUSINESS NAME — Numerological business name analysis
# ═══════════════════════════════════════════════════════════════

class BusinessNameRequest(BaseModel):
    business_name: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


@router.post("/business-name")
async def get_business_name(request_body: BusinessNameRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))
    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")
    if not request_body.business_name or len(request_body.business_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Business name required")
    try:
        from app.services.features.business_name import build_business_name, build_business_prompt
        from datetime import date as dt_date
        bd = dt_date(birth_data['year'], birth_data['month'], birth_data['day'])
        data = build_business_name(request_body.business_name.strip(), bd, request_body.language or 'en')
        system_prompt = build_business_prompt(data, request_body.language or 'en')
        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.OPENROUTER_MODEL, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze my business name: {request_body.business_name}"},
                ], "max_tokens": 200, "temperature": 0.7}, timeout=30.0)
        reading = ""
        if response.status_code == 200:
            reading = response.json()["choices"][0]["message"]["content"].strip()
        data.pop('briefing', None)
        return {'biz_data': data, 'reading': reading}
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Business name error: {str(e)[:200]}")


# ═══════════════════════════════════════════════════════════════
# MOBILE NUMBER — Phone number numerology
# ═══════════════════════════════════════════════════════════════

class MobileNumberRequest(BaseModel):
    mobile: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


@router.post("/mobile-number")
async def get_mobile_number(request_body: MobileNumberRequest, request: Request):
    check_rate_limit(request, "feature", getattr(settings, "RATE_LIMIT_FEATURE", 60))
    birth_data = _extract_birth_data(request_body.kundli_data)
    if not birth_data and request_body.birth_data:
        birth_data = request_body.birth_data
    if not birth_data:
        raise HTTPException(status_code=400, detail="Birth data required")
    if not request_body.mobile or len(request_body.mobile.strip()) < 4:
        raise HTTPException(status_code=400, detail="Mobile number required")
    try:
        from app.services.features.mobile_number import build_mobile_number, build_mobile_prompt
        from datetime import date as dt_date
        bd = dt_date(birth_data['year'], birth_data['month'], birth_data['day'])
        data = build_mobile_number(request_body.mobile.strip(), bd, request_body.language or 'en')
        if 'error' in data:
            raise HTTPException(status_code=400, detail=data['error'])
        system_prompt = build_mobile_prompt(data, request_body.language or 'en')
        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": settings.OPENROUTER_MODEL, "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze my number: {request_body.mobile}"},
                ], "max_tokens": 200, "temperature": 0.7}, timeout=30.0)
        reading = ""
        if response.status_code == 200:
            reading = response.json()["choices"][0]["message"]["content"].strip()
        data.pop('briefing', None)
        return {'mobile_data': data, 'reading': reading}
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Mobile number error: {str(e)[:200]}")


@router.post("/kundli/generate")
async def generate_kundli(request_body: KundliRequest, request: Request):
    check_rate_limit(request, "kundli", settings.RATE_LIMIT_KUNDLI)

    try:
        from app.services.jyotish_engine import JyotishEngine

        year, month, day, hour, minute, lat, lon, birth_dt = _validate_birth_params(
            request_body.date, request_body.time, request_body.place
        )

        engine = JyotishEngine(birth_dt, lat, lon)
        chart = engine.get_rashi_chart()
        dasha = engine.get_vimshottari_dasha()
        yogas = engine.get_yogas()

        return {
            "success": True,
            "kundli": {
                "ascendant": chart["ascendant"]["rashi_name"],
                "sun_sign": chart["planets"]["Sun"]["rashi_name"],
                "moon_sign": chart["planets"]["Moon"]["rashi_name"],
                "nakshatra": chart["planets"]["Moon"]["nakshatra_name"],
                "planets": {
                    name: {
                        "rashi": data["rashi_name"],
                        "nakshatra": data["nakshatra_name"],
                        "house": data["house"],
                        "degree": round(data["longitude"] % 30, 2),
                        "retrograde": data.get("retrograde", False),
                    }
                    for name, data in chart["planets"].items()
                },
                "current_dasha": {
                    "planet": dasha["mahadasha"]["lord"],
                    "sub": dasha["antardasha"]["lord"],
                    "string": dasha["dasha_string"],
                },
                "yogas_count": yogas["summary"]["total_yogas"],
            },
            "raw": {
                "chart": chart,
                "birth_details": {
                    "year": year, "month": month, "day": day,
                    "hour": hour, "minute": minute,
                    "latitude": lat, "longitude": lon,
                },
            },
            "sun_sign": chart["planets"]["Sun"]["rashi_name"],
            "moon_sign": chart["planets"]["Moon"]["rashi_name"],
            "ascendant": chart["ascendant"]["rashi_name"],
            "nakshatra": chart["planets"]["Moon"]["nakshatra_name"],
            "current_dasha": dasha["mahadasha"]["lord"],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Kundli generation failed")


@router.post("/whisper/transcribe")
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    check_rate_limit(request, "whisper", settings.RATE_LIMIT_WHISPER)

    tmp_path = None
    try:
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        async with httpx.AsyncClient() as client:
            with open(tmp_path, "rb") as audio_file:
                files = {"file": ("audio.m4a", audio_file, "audio/m4a")}
                data = {"model": "whisper-1"}
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files=files,
                    data=data,
                    timeout=60.0,
                )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Transcription service failed")

        result = response.json()
        return {"text": result.get("text", ""), "transcript": result.get("text", "")}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/tts")
async def text_to_speech(request: Request, request_body: dict):
    check_rate_limit(request, "tts", settings.RATE_LIMIT_TTS)

    text = request_body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "nova",
                    "response_format": "mp3",
                },
                timeout=60.0,
            )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="TTS service failed")

        import base64
        audio_base64 = base64.b64encode(response.content).decode("utf-8")
        return {"audio": audio_base64, "format": "mp3"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="TTS failed")


@router.post("/daily-ritual")
async def get_daily_ritual(request_body: dict):
    try:
        from app.services.jyotish_engine import JyotishEngine

        user_name = request_body.get("name", "Seeker")
        now = datetime.now()

        kundli = request_body.get("kundli_data", {})
        raw = kundli.get("raw", {})
        birth = raw.get("birth_details", kundli.get("birth_details", {}))
        lat = birth.get("latitude", 28.6139)
        lon = birth.get("longitude", 77.2090)

        engine = JyotishEngine(now, lat, lon)
        panchanga = engine.get_panchanga()
        muhurta = engine.get_muhurta()

        transits = engine.ephemeris.get_current_transits()
        moon_nakshatra = transits["Moon"]["nakshatra_name"]

        nakshatra_energies = {
            "Ashwini": {"energy": "ACTIVE", "word": "ACTION"},
            "Bharani": {"energy": "TRANSFORMATIVE", "word": "RELEASE"},
            "Krittika": {"energy": "PURIFYING", "word": "CLARITY"},
            "Rohini": {"energy": "CREATIVE", "word": "CREATE"},
            "Mrigashira": {"energy": "CURIOUS", "word": "EXPLORE"},
            "Ardra": {"energy": "INTENSE", "word": "FEEL"},
            "Punarvasu": {"energy": "RENEWING", "word": "RESTORE"},
            "Pushya": {"energy": "NURTURING", "word": "CARE"},
            "Ashlesha": {"energy": "INTUITIVE", "word": "TRUST"},
            "Magha": {"energy": "POWERFUL", "word": "LEAD"},
            "Purva Phalguni": {"energy": "JOYFUL", "word": "ENJOY"},
            "Uttara Phalguni": {"energy": "SUPPORTIVE", "word": "HELP"},
            "Hasta": {"energy": "SKILLFUL", "word": "CRAFT"},
            "Chitra": {"energy": "CREATIVE", "word": "DESIGN"},
            "Swati": {"energy": "FLEXIBLE", "word": "ADAPT"},
            "Vishakha": {"energy": "DETERMINED", "word": "FOCUS"},
            "Anuradha": {"energy": "DEVOTED", "word": "CONNECT"},
            "Jyeshtha": {"energy": "PROTECTIVE", "word": "GUARD"},
            "Mula": {"energy": "TRANSFORMATIVE", "word": "TRUTH"},
            "Purva Ashadha": {"energy": "INVINCIBLE", "word": "COURAGE"},
            "Uttara Ashadha": {"energy": "VICTORIOUS", "word": "WIN"},
            "Shravana": {"energy": "RECEPTIVE", "word": "LISTEN"},
            "Dhanishta": {"energy": "PROSPEROUS", "word": "GROW"},
            "Shatabhisha": {"energy": "HEALING", "word": "HEAL"},
            "Purva Bhadrapada": {"energy": "FIERY", "word": "TRANSFORM"},
            "Uttara Bhadrapada": {"energy": "DEEP", "word": "REFLECT"},
            "Revati": {"energy": "COMPASSIONATE", "word": "LOVE"},
        }

        info = nakshatra_energies.get(moon_nakshatra, {"energy": "BALANCED", "word": "PATIENCE"})
        hour = now.hour
        greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"

        return {
            "success": True,
            "date": now.strftime("%B %d, %Y"),
            "greeting": f"{greeting}, {user_name}",
            "energy": info["energy"],
            "word": info["word"],
            "moon_nakshatra": moon_nakshatra,
            "moon_sign": transits["Moon"]["rashi_name"],
            "tithi": panchanga["tithi"]["tithi_name"],
            "yoga": panchanga["yoga"]["yoga_name"],
            "rahu_kalam": muhurta["inauspicious"]["rahu_kalam"],
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get("/panchanga")
async def get_panchanga(lat: float = 28.6139, lon: float = 77.2090):
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    try:
        from app.services.jyotish_engine import JyotishEngine
        now = datetime.now()
        engine = JyotishEngine(now, lat, lon)
        return {
            "success": True,
            "date": now.strftime("%B %d, %Y"),
            "panchanga": engine.get_panchanga(),
            "muhurta": engine.get_muhurta(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/compatibility")
async def check_compatibility(request_body: dict):
    try:
        from app.services.compatibility.ashtakoota import AshtakootaMatch

        boy_moon = float(request_body.get("boy_moon_longitude", 0))
        girl_moon = float(request_body.get("girl_moon_longitude", 0))

        if not (0 <= boy_moon <= 360) or not (0 <= girl_moon <= 360):
            raise HTTPException(status_code=400, detail="Moon longitude must be 0-360")

        match = AshtakootaMatch(boy_moon, girl_moon)
        return {"success": True, "compatibility": match.calculate_total()}

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/match")
async def match_compatibility(request: Request, body: dict):
    """Ashtakoota compatibility matching between two charts"""
    try:
        from app.services.jyotish_engine import JyotishEngine
        from datetime import datetime
        
        kundli_data = body.get('kundli_data', {})
        partner = body.get('partner', {})
        
        # Get person 1's birth details from kundli_data
        raw = kundli_data.get('raw', {})
        bd = raw.get('birth_details', {})
        
        # Create engine for person 1
        e1 = JyotishEngine(
            datetime(
                int(bd.get('year', 2000)),
                int(bd.get('month', 1)),
                int(bd.get('day', 1)),
                int(bd.get('hour', 12)),
                int(bd.get('minute', 0))
            ),
            float(bd.get('latitude', 28.6)),
            float(bd.get('longitude', 77.2))
        )
        
        # Create engine for person 2
        e2 = JyotishEngine(
            datetime(
                int(partner.get('year', 2000)),
                int(partner.get('month', 1)),
                int(partner.get('day', 1)),
                int(partner.get('hour', 12)),
                int(partner.get('minute', 0))
            ),
            float(partner.get('lat', 28.6)),
            float(partner.get('lng', 77.2))
        )
        
        # Run ashtakoota matching
        moon2_long = e2.planets['Moon']['longitude']
        result = e1.match_compatibility(moon2_long)
        
        # Format kootas for frontend
        kootas_list = []
        for key in ['varna', 'vashya', 'tara', 'yoni', 'graha_maitri', 'gana', 'bhakoot', 'nadi']:
            k = result.get('kootas', {}).get(key, {})
            kootas_list.append({
                'name': k.get('koota', key),
                'score': k.get('points', 0),
                'max': k.get('max_points', 0),
                'description': k.get('description', ''),
            })
        
        return {
            'success': True,
            'data': {
                'total_score': result.get('total_points', 0),
                'max_score': 36,
                'percentage': result.get('percentage', 0),
                'compatibility': result.get('compatibility', ''),
                'recommendation': result.get('recommendation', ''),
                'kootas': kootas_list,
                'doshas': result.get('doshas', []),
                'has_major_dosha': result.get('has_major_dosha', False),
                'boy': result.get('boy', {}),
                'girl': result.get('girl', {}),
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.post("/soul-profile")
async def generate_soul_profile(body: FeatureRequest, request: Request):
    return await _render_feature("soul-profile", body, request)

@router.post("/soul-profile-old")
async def generate_soul_profile_old(request: Request, body: dict):
    try:
        from app.services.jyotish_engine import JyotishEngine
        from app.core.config import settings
        from datetime import datetime
        import json
        import httpx

        kundli_data = body.get("kundli_data", {})
        language = body.get("language", "en")
        raw = kundli_data.get("raw", {})
        bd = raw.get("birth_details", {})

        e = JyotishEngine(
            datetime(int(bd.get("year",2000)), int(bd.get("month",1)), int(bd.get("day",1)),
                     int(bd.get("hour",12)), int(bd.get("minute",0))),
            float(bd.get("latitude", 28.6)), float(bd.get("longitude", 77.2))
        )

        ascendant = e.planets.get("Ascendant", {}).get("rashi_name", "Pisces")
        moon_sign = e.planets.get("Moon", {}).get("rashi_name", "Gemini")
        moon_nak = e.get_nakshatra_profile().get("moon_profile", {})
        nakshatra = moon_nak.get("nakshatra", "Ardra")
        yogas = e.get_yogas()
        yoga_names = [y.get("name", "") for y in yogas.get("highlights", [])][:3]

        planet_summary = []
        for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
            pd = e.planets.get(p, {})
            planet_summary.append(p + " H" + str(pd.get("house","?")) + "-" + str(pd.get("rashi_name","?")))

        lang_note = ""
        if language == "hi":
            lang_note = "Respond in Hindi Devanagari script."
        elif language != "en":
            lm = {"zh":"Chinese","es":"Spanish","pt":"Portuguese","ja":"Japanese"}
            lang_note = "Respond in " + lm.get(language, "English") + "."

        chart = "Asc:" + ascendant + " Moon:" + moon_sign + "/" + nakshatra
        chart += " Yogas:" + (",".join(yoga_names) if yoga_names else "none")
        chart += " " + " ".join(planet_summary)

        prompt = (
            "You are a Vedic astrology poet. Chart: " + chart + ". "
            "Return ONLY valid JSON, no markdown, no backticks: "
            '{"archetype":"2-3 word personal title like The Restless Flame",'
            '"dharma":"4-6 word phrase about life purpose from 10th house",'
            '"karma":"4-6 word phrase about karmic lesson from ascendant",'
            '"kama":"4-6 word phrase about desire from Venus/7th house",'
            '"moksha":"4-6 word phrase about liberation from 12th/Ketu"} '
            "Be poetic but specific to THIS chart. " + lang_note
        )

        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + settings.OPENROUTER_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek/deepseek-chat",
                "max_tokens": 300,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15.0,
        )

        text = resp.json()["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(text)
        except Exception:
            result = {
                "archetype": "Seeker of Truth",
                "dharma": "purpose unfolds in silence",
                "karma": "learn through experience",
                "kama": "heart seeks connection",
                "moksha": "freedom through understanding"
            }

        return {"success": True, "data": result}

    except Exception as ex:
        return {"success": False, "error": str(ex)}


@router.post("/register-push")
async def register_push_token(request: Request, body: dict):
    """Register a user's Expo push token for notifications."""
    try:
        import json as jjson
        from pathlib import Path

        user_id = body.get("user_id", "")
        push_token = body.get("push_token", "")
        birth_details = body.get("birth_details", {})
        language = body.get("language", "en")

        if not push_token:
            return {"success": False, "error": "No push token provided"}

        data_dir = Path("/var/www/jyotish/backend/data")
        data_dir.mkdir(exist_ok=True)
        users_file = data_dir / "push_users.jsonl"

        # Load existing users
        existing = []
        if users_file.exists():
            with open(users_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            existing.append(jjson.loads(line))
                        except jjson.JSONDecodeError:
                            pass

        # Update or add user
        found = False
        for user in existing:
            if user.get("user_id") == user_id:
                user["push_token"] = push_token
                user["birth_details"] = birth_details
                user["language"] = language
                user["updated_at"] = datetime.now().isoformat()
                found = True
                break

        if not found:
            existing.append({
                "user_id": user_id,
                "push_token": push_token,
                "birth_details": birth_details,
                "language": language,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            })

        with open(users_file, "w") as f:
            for user in existing:
                f.write(jjson.dumps(user, ensure_ascii=False) + "\n")

        return {"success": True, "message": "Push token registered"}

    except Exception as ex:
        return {"success": False, "error": str(ex)}



# ═══════════════════════════════════════════════════════════════
# GOOGLE PLACES PROXY — keeps API key server-side
# ═══════════════════════════════════════════════════════════════
import httpx, os

GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

@router.post("/places/autocomplete")
async def places_search(body: dict):
    query = body.get("query", "")
    if not query or len(query) < 2:
        return {"predictions": []}
    try:
        async with httpx.AsyncClient(timeout=5, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
            r = await client.get(
                "https://maps.googleapis.com/maps/api/place/autocomplete/json",
                params={"input": query, "types": "(cities)", "key": GOOGLE_PLACES_KEY}
            )
            return r.json()
    except Exception as e:
        return {"predictions": [], "error": str(e)}

@router.post("/places/details")
async def places_details(body: dict):
    place_id = body.get("place_id", "")
    if not place_id:
        return {"result": {}}
    try:
        async with httpx.AsyncClient(timeout=5, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
            r = await client.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={"place_id": place_id, "fields": "geometry,formatted_address", "key": GOOGLE_PLACES_KEY}
            )
            return r.json()
    except Exception as e:
        return {"result": {}, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# SIDE SCREEN CHAT — bond + other sky
# ═══════════════════════════════════════════════════════════════
from starlette.responses import StreamingResponse as StarletteStreamingResponse
import json as json_mod

async def _side_chat_stream(main_chart, other_chart, message, history, language, mode, extra_context=""):
    """Shared streaming chat for bond + other sky modes."""
    from app.services.jyotish_engine import JyotishEngine
    from datetime import datetime
    import os

    # Build both charts
    charts = []
    for label, chart_data in [("MAIN USER", main_chart), ("OTHER PERSON", other_chart)]:
        bd = (chart_data or {}).get("raw", chart_data or {}).get("birth_details", chart_data or {})
        if bd.get("year"):
            try:
                eng = JyotishEngine(
                    datetime(bd["year"], bd["month"], bd["day"], bd.get("hour", 12), bd.get("minute", 0)),
                    bd.get("latitude", 28.6), bd.get("longitude", 77.2)
                )
                summary = eng.get_chart_summary() if hasattr(eng, "get_chart_summary") else str(eng.planets)[:500]
                charts.append(f"[{label}]\n{summary}")
            except:
                charts.append(f"[{label}] Chart data incomplete.")
        else:
            charts.append(f"[{label}] No birth data provided.")

    chart_block = "\n\n".join(charts)

    if mode == "bond":
        system = f"""You are the Oracle of Jyotish AI — the voice of the stars. Ancient, warm, mystical, true.
You are reading the connection between two people. The MAIN USER is asking you questions.

{chart_block}

{extra_context}

Read the bond between these two charts. Be specific about planetary connections, house overlaps, nakshatra compatibility.
Speak to the main user directly. Use Vedic astrology language. Be warm but precise.
Reply in {language}. Keep responses focused — 2-4 sentences unless asked for more."""
    else:
        system = f"""You are the Oracle of Jyotish AI — the voice of the stars. Ancient, warm, mystical, true.
You are reading another person's chart FOR the main user. The main user wants to understand someone else.

{chart_block}

{extra_context}

Read the OTHER PERSON's chart and explain it to the main user. Help them understand this person.
Be specific about planetary positions, dashas, strengths. Use Vedic astrology.
Reply in {language}. Keep responses focused — 2-4 sentences unless asked for more."""

    messages = [{"role": "system", "content": system}]
    for h in (history or [])[-8:]:
        role = "assistant" if h.get("role") in ["oracle", "assistant"] else "user"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})

    api_key = settings.OPENROUTER_API_KEY

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream("POST", "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": settings.OPENROUTER_MODEL, "messages": messages, "max_tokens": 400, "temperature": 0.8, "stream": True},
                ) as resp:
                    full = ""
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json_mod.loads(payload)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                full += text
                                yield f"data: {json_mod.dumps({'type': 'delta', 'text': text})}\n\n"
                        except:
                            continue
                    yield f"data: {json_mod.dumps({'type': 'done', 'response': full})}\n\n"
        except Exception as e:
            yield f"data: {json_mod.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StarletteStreamingResponse(generate(), media_type="text/event-stream")


class SideChatRequest(BaseModel):
    message: str
    kundli_data: Optional[dict] = None
    partner_data: Optional[dict] = None
    other_kundli: Optional[dict] = None
    other_birth: Optional[dict] = None
    match_result: Optional[dict] = None
    partner_type: Optional[str] = "life"
    history: Optional[list] = []
    language: Optional[str] = "en"


@router.post("/chat/bond/stream")
async def chat_bond_stream(body: SideChatRequest):
    match_info = ""
    if body.match_result:
        mr = body.match_result
        match_info = f"Match score: {mr.get('total_score', '?')}/{mr.get('max_score', '?')} ({mr.get('percentage', '?')}%). Partner type: {body.partner_type}."
    return await _side_chat_stream(
        body.kundli_data, body.partner_data, body.message,
        body.history, body.language, "bond", match_info
    )


@router.post("/chat/other-sky/stream")
async def chat_other_sky_stream(body: SideChatRequest):
    extra = ""
    if body.other_birth:
        ob = body.other_birth
        extra = f"Other person born: {ob.get('day','?')}/{ob.get('month','?')}/{ob.get('year','?')} at {ob.get('place','unknown')}."
    return await _side_chat_stream(
        body.kundli_data, body.other_kundli or body.other_birth, body.message,
        body.history, body.language, "other", extra
    )


@router.post("/chat/side/stream")
async def chat_side_stream(body: dict):
    """Unified side chat — routes bond vs other_sky by mode field."""
    mode = body.get("mode", "bond")
    message = body.get("message", "")
    kundli = body.get("kundli_data", {})
    other = body.get("other_kundli_data", body.get("partner_data", {}))
    history = body.get("history", [])
    language = body.get("language", "en")
    other_name = body.get("other_name", "")
    match_result = body.get("match_result", {})

    extra = ""
    if mode == "bond":
        mr = match_result
        if mr:
            extra = f"Match score: {mr.get('total_score', '?')}/{mr.get('max_score', '?')}. Partner: {other_name}."
        else:
            extra = f"Partner: {other_name}." if other_name else ""
    else:
        extra = f"Other person: {other_name}." if other_name else ""

    return await _side_chat_stream(kundli, other, message, history, language, "bond" if mode == "bond" else "other", extra)


from fastapi.responses import HTMLResponse

@router.get('/privacy')
async def privacy():
    return HTMLResponse(open('static/privacy.html').read())

@router.get("/delete-account")
async def delete_account():
    return HTMLResponse(open("static/delete.html").read())


@router.get("/media-manifest")
async def media_manifest():
    from app.services.features.media_manifest import _build_manifest; import datetime
    return {"version": int(datetime.datetime.now().timestamp()), "files": _build_manifest()}
