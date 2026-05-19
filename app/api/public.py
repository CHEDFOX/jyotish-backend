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
    gender: Optional[str] = None
    language: Optional[str] = "en"

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


class ChapterReadRequest(BaseModel):
    chapter_index: int
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


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


# ═══════════════════════════════════════════════════════════════
# THE WORD — Quick KP yes/no on life topics
# ═══════════════════════════════════════════════════════════════

class TheWordRequest(BaseModel):
    topic: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


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


# ═══════════════════════════════════════════════════════════════
# NAME CORRECTION — Numerological name analysis
# ═══════════════════════════════════════════════════════════════

class NameCorrectionRequest(BaseModel):
    name: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


# ═══════════════════════════════════════════════════════════════
# BUSINESS NAME — Numerological business name analysis
# ═══════════════════════════════════════════════════════════════

class BusinessNameRequest(BaseModel):
    business_name: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


# ═══════════════════════════════════════════════════════════════
# MOBILE NUMBER — Phone number numerology
# ═══════════════════════════════════════════════════════════════

class MobileNumberRequest(BaseModel):
    mobile: str
    kundli_data: Optional[dict] = None
    birth_data: Optional[dict] = None
    language: Optional[str] = "en"


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

        def _safe(fn, *args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                return {"error": str(e)}

        gender = (request_body.gender or "male").lower()
        gender_norm = "female" if gender in ("female", "f", "woman", "girl") else "male"

        kp_data = _safe(engine.get_kp_complete)

        western_big_three = _safe(engine.get_western_big_three)
        western_aspects = _safe(engine.get_western_aspects)

        chinese_chart = _safe(engine.get_chinese_chart)
        chinese_animal = _safe(engine.get_chinese_animal)
        chinese_day_master = _safe(engine.get_chinese_day_master)
        chinese_elements = _safe(engine.get_chinese_elements)
        try:
            from app.services.chinese.bazi import BaZiChart
            bc = BaZiChart(engine.birth_local)
            chinese_luck = bc.get_luck_periods(gender=gender_norm)
        except Exception as e:
            chinese_luck = {"error": str(e)}

        numerology_data = _safe(engine.get_numerology, request_body.name)

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
                    "name": request_body.name,
                    "gender": gender_norm,
                    "language": request_body.language or "en",
                },
            },
            "systems": {
                "vedic": {
                    "ascendant": chart["ascendant"]["rashi_name"],
                    "sun_sign": chart["planets"]["Sun"]["rashi_name"],
                    "moon_sign": chart["planets"]["Moon"]["rashi_name"],
                    "nakshatra": chart["planets"]["Moon"]["nakshatra_name"],
                    "current_dasha": {
                        "planet": dasha["mahadasha"]["lord"],
                        "sub": dasha["antardasha"]["lord"],
                        "string": dasha["dasha_string"],
                    },
                    "yogas_count": yogas["summary"]["total_yogas"],
                },
                "kp": kp_data,
                "western": {
                    "big_three": western_big_three,
                    "aspects": western_aspects,
                },
                "chinese": {
                    "chart": chinese_chart,
                    "animal": chinese_animal,
                    "day_master": chinese_day_master,
                    "elements": chinese_elements,
                    "luck_periods": chinese_luck,
                },
                "numerology": numerology_data,
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

GOOGLE_PLACES_KEY = settings.GOOGLE_PLACES_API_KEY

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


@router.get("/onboarding-content")
async def onboarding_content(language: Optional[str] = None):
    from app.services.onboarding_content import build_onboarding_payload
    return {"success": True, "data": await build_onboarding_payload(language)}
