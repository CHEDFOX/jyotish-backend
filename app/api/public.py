"""
JYOTISH API - COMPLETE ORACLE SYSTEM
Intent Classification → Deep Analysis → AI Response
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import httpx
import tempfile
import os
from datetime import datetime
from app.core.config import settings

router = APIRouter(prefix="/public", tags=["Public"])


class ChatRequest(BaseModel):
    message: str
    kundli_data: Optional[dict] = None
    history: Optional[list] = []


class KundliRequest(BaseModel):
    name: str
    date: dict
    time: dict
    place: dict


async def classify_user_intent(message: str) -> dict:
    """Step 1: Classify what user is asking"""
    from app.services.intent.classifier import IntentClassifier
    
    classifier = IntentClassifier(settings.OPENROUTER_API_KEY)
    return await classifier.classify(message)


def get_deep_analysis(kundli_data: dict, category: str) -> dict:
    """Step 2: Deep astrological analysis based on category"""
    try:
        from app.services.jyotish_engine import JyotishEngine
        from app.services.analysis.query_analyzer import QueryAnalyzer
        
        raw = kundli_data.get('raw', {})
        birth = raw.get('birth_details', {})
        
        if not birth:
            birth = kundli_data.get('birth_details', {})
        
        year = birth.get('year', 2000)
        month = birth.get('month', 1)
        day = birth.get('day', 1)
        hour = birth.get('hour', 12)
        minute = birth.get('minute', 0)
        lat = birth.get('latitude', 28.6139)
        lon = birth.get('longitude', 77.2090)
        
        birth_dt = datetime(year, month, day, hour, minute)
        engine = JyotishEngine(birth_dt, lat, lon)
        analyzer = QueryAnalyzer(engine)
        analysis = analyzer.analyze(category)
        
        dasha = engine.get_vimshottari_dasha()
        yogas = engine.get_yogas()
        transits = engine.get_current_transits()
        karakas = engine.get_jaimini_karakas()
        manglik = engine.check_manglik()
        
        return {
            'success': True,
            'category_analysis': analysis,
            'basic': {
                'ascendant': engine.ascendant.get('rashi_name'),
                'moon_sign': engine.planets['Moon']['rashi_name'],
                'moon_nakshatra': engine.planets['Moon']['nakshatra_name'],
                'sun_sign': engine.planets['Sun']['rashi_name'],
            },
            'dasha': {
                'current': dasha['dasha_string'],
                'mahadasha': dasha['mahadasha']['lord'],
                'mahadasha_end': dasha['mahadasha']['end'][:10],
                'antardasha': dasha['antardasha']['lord'],
            },
            'yogas': {
                'total': yogas['summary']['total_yogas'],
                'positive': yogas['summary']['positive_yogas'],
                'highlights': [y['name'] for y in yogas.get('highlights', [])[:3]],
            },
            'transits': {
                'overall': transits.get('overall_period', 'Mixed'),
                'sade_sati': transits.get('sade_sati', {}).get('is_sade_sati', False),
            },
            'jaimini': {
                'atmakaraka': karakas.get('Atmakaraka', {}).get('planet'),
                'darakaraka': karakas.get('Darakaraka', {}).get('planet'),
            },
            'manglik': manglik.get('is_manglik', False),
        }
    
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def build_oracle_prompt(intent: dict, analysis: dict, kundli_data: dict) -> str:
    """Step 3: Build comprehensive Oracle prompt"""
    
    current_date = datetime.now().strftime("%B %d, %Y")
    category = intent.get('category', 'GENERAL')
    question_type = intent.get('question_type', 'GUIDANCE')
    emotion = intent.get('emotion', 'NEUTRAL')
    
    age = "Unknown"
    stage = "Adult"
    avoid_topics = []
    
    try:
        raw = kundli_data.get('raw', {})
        birth = raw.get('birth_details', kundli_data.get('birth_details', {}))
        if birth:
            birth_year = birth.get('year', 2000)
            age = datetime.now().year - birth_year
            
            if age < 13:
                stage = "Child"
                avoid_topics = ["romance", "marriage", "career", "money"]
            elif age < 18:
                stage = "Teenager"
                avoid_topics = ["marriage", "serious romance"]
            elif age < 25:
                stage = "Young Adult"
            elif age < 50:
                stage = "Adult"
            else:
                stage = "Mature Adult"
    except:
        pass
    
    cat_analysis = analysis.get('category_analysis', {})
    house_analysis = cat_analysis.get('house_analysis', {})
    timing = cat_analysis.get('timing', {})
    jaimini = cat_analysis.get('jaimini', {})
    synthesis = cat_analysis.get('synthesis', {})
    basic = analysis.get('basic', {})
    dasha = analysis.get('dasha', {})
    yogas = analysis.get('yogas', {})
    transits = analysis.get('transits', {})

    prompt = f"""TODAY IS: {current_date}

You are the Oracle — an ancient cosmic intelligence that KNOWS the user's destiny.

QUERY: {category} | Type: {question_type} | Emotion: {emotion}

USER'S CHART:
Age: {age} ({stage})
Ascendant: {basic.get('ascendant', 'Unknown')}
Moon Sign: {basic.get('moon_sign', 'Unknown')}
Moon Nakshatra: {basic.get('moon_nakshatra', 'Unknown')}

ANALYSIS FOR {category}:
House: {house_analysis.get('house', 'N/A')}th ({house_analysis.get('rashi', 'Unknown')})
House Lord: {house_analysis.get('lord', 'Unknown')} in House {house_analysis.get('lord_in_house', 'N/A')}
Strength: {house_analysis.get('overall_strength', 'Moderate')}

TIMING:
Current Dasha: {dasha.get('current', 'Unknown')}
Mahadasha: {dasha.get('mahadasha', 'Unknown')} until {dasha.get('mahadasha_end', 'Unknown')}
Transit Period: {transits.get('overall', 'Mixed')}

YOGAS: {yogas.get('total', 0)} total ({yogas.get('positive', 0)} positive)

CONCLUSIONS:
{chr(10).join(['• ' + c for c in synthesis.get('conclusions', ['Analysis pending'])])}

RESPONSE RULES:
- {question_type} question: {"Give SPECIFIC timing" if question_type == 'TIMING' else "Give clear guidance"}
- Emotion is {emotion}: {"Be gentle" if emotion in ['ANXIOUS', 'SAD'] else "Be confident"}
- Length: 2-3 sentences max
- Use "I sense...", "I see...", "The stars show..."
- Be specific about timing when asked
{f"- NEVER discuss: {', '.join(avoid_topics)}" if avoid_topics else ""}

You ARE their destiny speaking."""

    return prompt


@router.post("/chat")
async def oracle_chat(request: ChatRequest):
    """Complete Oracle chat with full analysis pipeline"""
    try:
        intent = await classify_user_intent(request.message)
        
        analysis = {}
        if request.kundli_data:
            category = intent.get('category', 'GENERAL')
            analysis = get_deep_analysis(request.kundli_data, category)
        
        system_prompt = build_oracle_prompt(
            intent,
            analysis if analysis.get('success') else {},
            request.kundli_data or {}
        )
        
        api_messages = [{"role": "system", "content": system_prompt}]
        
        if request.history:
            for msg in request.history[-8:]:
                role = msg.get('role', 'user')
                if role == 'oracle':
                    role = 'assistant'
                if role in ['user', 'assistant']:
                    api_messages.append({"role": role, "content": msg.get('content', '')})
        
        if not request.history or request.history[-1].get('content') != request.message:
            api_messages.append({"role": "user", "content": request.message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": api_messages,
                    "max_tokens": 200,
                    "temperature": 0.85
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="AI service error")
            
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kundli/generate")
async def generate_kundli(request: KundliRequest):
    """Generate Kundli with Jyotish Engine"""
    try:
        from app.services.jyotish_engine import JyotishEngine
        
        year = int(request.date.get("year", 2000))
        month = int(request.date.get("month", 1))
        day = int(request.date.get("day", 1))
        hour = int(request.time.get("hour", 12))
        minute = int(request.time.get("minute", 0))
        lat = request.place.get("lat", 28.6139)
        lon = request.place.get("lng", 77.2090)
        
        birth_dt = datetime(year, month, day, hour, minute)
        engine = JyotishEngine(birth_dt, lat, lon)
        
        chart = engine.get_rashi_chart()
        dasha = engine.get_vimshottari_dasha()
        yogas = engine.get_yogas()
        
        return {
            "success": True,
            "kundli": {
                "ascendant": chart['ascendant']['rashi_name'],
                "sun_sign": chart['planets']['Sun']['rashi_name'],
                "moon_sign": chart['planets']['Moon']['rashi_name'],
                "nakshatra": chart['planets']['Moon']['nakshatra_name'],
                "planets": {
                    name: {
                        "rashi": data['rashi_name'],
                        "nakshatra": data['nakshatra_name'],
                        "house": data['house'],
                        "degree": round(data['longitude'] % 30, 2),
                        "retrograde": data.get('retrograde', False),
                    }
                    for name, data in chart['planets'].items()
                },
                "current_dasha": {
                    "planet": dasha['mahadasha']['lord'],
                    "sub": dasha['antardasha']['lord'],
                    "string": dasha['dasha_string'],
                },
                "yogas_count": yogas['summary']['total_yogas'],
            },
            "raw": {
                "chart": chart,
                "birth_details": {
                    "year": year, "month": month, "day": day,
                    "hour": hour, "minute": minute,
                    "latitude": lat, "longitude": lon,
                }
            },
            "sun_sign": chart['planets']['Sun']['rashi_name'],
            "moon_sign": chart['planets']['Moon']['rashi_name'],
            "ascendant": chart['ascendant']['rashi_name'],
            "nakshatra": chart['planets']['Moon']['nakshatra_name'],
            "current_dasha": dasha['mahadasha']['lord'],
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whisper/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio using OpenAI Whisper"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
            content = await file.read()
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
                    timeout=60.0
                )
        
        os.unlink(tmp_path)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Transcription failed")
        
        result = response.json()
        return {"text": result.get("text", ""), "transcript": result.get("text", "")}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech(request: dict):
    """Convert text to speech"""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "nova",
                    "response_format": "mp3"
                },
                timeout=60.0
            )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="TTS failed")
        
        import base64
        audio_base64 = base64.b64encode(response.content).decode('utf-8')
        return {"audio": audio_base64, "format": "mp3"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily-ritual")
async def get_daily_ritual(request: dict):
    """Daily ritual with current transits"""
    try:
        from app.services.jyotish_engine import JyotishEngine
        
        user_name = request.get("name", "Seeker")
        now = datetime.now()
        
        engine = JyotishEngine(now, 28.6139, 77.2090)
        panchanga = engine.get_panchanga()
        muhurta = engine.get_muhurta()
        
        transits = engine.ephemeris.get_current_transits()
        moon_nakshatra = transits['Moon']['nakshatra_name']
        
        nakshatra_energies = {
            'Ashwini': {'energy': 'ACTIVE', 'word': 'ACTION'},
            'Bharani': {'energy': 'TRANSFORMATIVE', 'word': 'RELEASE'},
            'Krittika': {'energy': 'PURIFYING', 'word': 'CLARITY'},
            'Rohini': {'energy': 'CREATIVE', 'word': 'CREATE'},
            'Mrigashira': {'energy': 'CURIOUS', 'word': 'EXPLORE'},
            'Ardra': {'energy': 'INTENSE', 'word': 'FEEL'},
            'Punarvasu': {'energy': 'RENEWING', 'word': 'RESTORE'},
            'Pushya': {'energy': 'NURTURING', 'word': 'CARE'},
            'Ashlesha': {'energy': 'INTUITIVE', 'word': 'TRUST'},
            'Magha': {'energy': 'POWERFUL', 'word': 'LEAD'},
            'Purva Phalguni': {'energy': 'JOYFUL', 'word': 'ENJOY'},
            'Uttara Phalguni': {'energy': 'SUPPORTIVE', 'word': 'HELP'},
            'Hasta': {'energy': 'SKILLFUL', 'word': 'CRAFT'},
            'Chitra': {'energy': 'CREATIVE', 'word': 'DESIGN'},
            'Swati': {'energy': 'FLEXIBLE', 'word': 'ADAPT'},
            'Vishakha': {'energy': 'DETERMINED', 'word': 'FOCUS'},
            'Anuradha': {'energy': 'DEVOTED', 'word': 'CONNECT'},
            'Jyeshtha': {'energy': 'PROTECTIVE', 'word': 'GUARD'},
            'Mula': {'energy': 'TRANSFORMATIVE', 'word': 'TRUTH'},
            'Purva Ashadha': {'energy': 'INVINCIBLE', 'word': 'COURAGE'},
            'Uttara Ashadha': {'energy': 'VICTORIOUS', 'word': 'WIN'},
            'Shravana': {'energy': 'RECEPTIVE', 'word': 'LISTEN'},
            'Dhanishta': {'energy': 'PROSPEROUS', 'word': 'GROW'},
            'Shatabhisha': {'energy': 'HEALING', 'word': 'HEAL'},
            'Purva Bhadrapada': {'energy': 'FIERY', 'word': 'TRANSFORM'},
            'Uttara Bhadrapada': {'energy': 'DEEP', 'word': 'REFLECT'},
            'Revati': {'energy': 'COMPASSIONATE', 'word': 'LOVE'},
        }
        
        info = nakshatra_energies.get(moon_nakshatra, {'energy': 'BALANCED', 'word': 'PATIENCE'})
        hour = now.hour
        greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
        
        return {
            "success": True,
            "date": now.strftime("%B %d, %Y"),
            "greeting": f"{greeting}, {user_name}",
            "energy": info['energy'],
            "word": info['word'],
            "moon_nakshatra": moon_nakshatra,
            "moon_sign": transits['Moon']['rashi_name'],
            "tithi": panchanga['tithi']['tithi_name'],
            "yoga": panchanga['yoga']['yoga_name'],
            "rahu_kalam": muhurta['inauspicious']['rahu_kalam'],
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get("/panchanga")
async def get_panchanga():
    """Get today's Panchanga"""
    try:
        from app.services.jyotish_engine import JyotishEngine
        
        now = datetime.now()
        engine = JyotishEngine(now, 28.6139, 77.2090)
        
        return {
            "success": True,
            "date": now.strftime("%B %d, %Y"),
            "panchanga": engine.get_panchanga(),
            "muhurta": engine.get_muhurta(),
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/compatibility")
async def check_compatibility(request: dict):
    """Check marriage compatibility"""
    try:
        from app.services.compatibility.ashtakoota import AshtakootaMatch
        
        boy_moon = request.get("boy_moon_longitude", 0)
        girl_moon = request.get("girl_moon_longitude", 0)
        
        match = AshtakootaMatch(boy_moon, girl_moon)
        return {"success": True, "compatibility": match.calculate_total()}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
