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
    history: Optional[list] = []

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
    # check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)  # disabled for testing

    try:
        from app.services.oracle.pipeline import process_oracle_query

        # Extract birth data from kundli
        # Accept both kundli_data (app format) and birth_data (test format)
        birth_data = _extract_birth_data(request_body.kundli_data)
        if not birth_data and request_body.birth_data:
            birth_data = request_body.birth_data

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
        )


        system_prompt = oracle_result['system_prompt']
        briefing = oracle_result.get('data_packet', {}).get('oracle_briefing', '')

        # Check if Python wrote a response
        python_response = ''
        hook_facts = ''
        hook_direction = ''

        if 'RESPONSE (output this EXACTLY' in briefing:
            parts = briefing.split('RESPONSE (output this EXACTLY, then add hook):')
            if len(parts) > 1:
                response_part = parts[1]
                if 'KEY FACTS FOR HOOK:' in response_part:
                    python_response = response_part.split('KEY FACTS FOR HOOK:')[0].strip()
                    remainder = response_part.split('KEY FACTS FOR HOOK:')[1]
                    if 'HOOK DIRECTION:' in remainder:
                        hook_facts = remainder.split('HOOK DIRECTION:')[0].strip()
                        hook_direction = remainder.split('HOOK DIRECTION:')[1].strip()
                    else:
                        hook_facts = remainder.strip()
                else:
                    python_response = response_part.strip()

        import sys
        print(f"DEBUG: python_response length = {len(python_response)}", file=sys.stderr)
        print(f"DEBUG: python_response[:50] = {python_response[:50]}", file=sys.stderr)
        if False and python_response:
            print("DEBUG: USING PYTHON RESPONSE", file=sys.stderr)
            # Python wrote the response — LLM only generates hook
            hook_prompt = "Generate ONE hook line for an astrology reading about " + oracle_result['intent']['primary'] + ". "
            hook_prompt += "Facts: " + hook_facts + ". "
            hook_prompt += "Direction: " + hook_direction + ". "
            hook_prompt += "Write ONE line starting with I notice or There is or Interestingly that teases something specific. Do NOT ask a question. Just one line."

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.OPENROUTER_MODEL,
                            "messages": [{"role": "user", "content": hook_prompt}],
                            "max_tokens": 60,
                            "temperature": 0.9,
                        },
                        timeout=15.0,
                    )
                    if response.status_code == 200:
                        hdata = response.json()
                        hook_line = hdata["choices"][0]["message"]["content"].strip().split("\n")[0]
                        oracle_response = python_response + "\n\n" + hook_line
                    else:
                        oracle_response = python_response
            except Exception:
                oracle_response = python_response
        else:
            # Fallback — full LLM for non-life-event queries
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

        # Return response with metadata
        return {
            "response": oracle_response,
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
