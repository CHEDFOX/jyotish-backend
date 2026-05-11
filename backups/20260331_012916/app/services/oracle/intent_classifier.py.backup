"""
JYOTISH ORACLE — PURE AI INTENT CLASSIFIER

No keywords. No hacks. Pure AI understanding.
Works in ANY language on Earth.

Speed strategy:
1. Cache: Same question pattern → instant (0ms)
2. Parallel: Classification runs alongside engine creation
3. Compact prompt: 2-3s instead of 6-8s

If AI fails (network/timeout): minimal keyword fallback as safety net.
"""

import re
import json
import hashlib
import httpx
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from collections import OrderedDict
from app.core.config import settings


# ═══════════════════════════════════════════════════════════════════
# CLASSIFICATION CACHE
# ═══════════════════════════════════════════════════════════════════

class ClassificationCache:
    """Cache AI classifications. Similar questions get instant results."""

    def __init__(self, max_size: int = 500, ttl_hours: int = 24):
        self._cache = OrderedDict()
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)

    def _normalize(self, message: str) -> str:
        """Normalize message for cache key — strips noise, keeps meaning."""
        # Lowercase, remove extra spaces and punctuation
        msg = message.lower().strip()
        msg = re.sub(r'[^\w\s]', '', msg)
        msg = re.sub(r'\s+', ' ', msg)
        # Remove common filler words
        fillers = {'please', 'can', 'you', 'tell', 'me', 'i', 'want', 'to', 'know',
                   'about', 'my', 'the', 'a', 'an', 'is', 'are', 'will', 'would',
                   'could', 'do', 'does', 'mujhe', 'batao', 'bataiye', 'kya', 'hai',
                   'mera', 'meri', 'mere'}
        words = [w for w in msg.split() if w not in fillers and len(w) > 1]
        core = ' '.join(words[:8])  # First 8 meaningful words
        return hashlib.md5(core.encode()).hexdigest()

    def get(self, message: str) -> Optional[Dict]:
        key = self._normalize(message)
        entry = self._cache.get(key)
        if entry and datetime.now() - entry['time'] < self.ttl:
            entry['hits'] += 1
            # Return a copy with updated message
            result = dict(entry['result'])
            result['original_message'] = message
            result['cache_hit'] = True
            return result
        return None

    def put(self, message: str, result: Dict):
        key = self._normalize(message)
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Remove oldest
        self._cache[key] = {
            'result': result,
            'time': datetime.now(),
            'hits': 0,
        }

    def stats(self) -> Dict:
        return {
            'size': len(self._cache),
            'total_hits': sum(v['hits'] for v in self._cache.values()),
        }


# ═══════════════════════════════════════════════════════════════════
# COMPACT AI PROMPT (small prompt = fast response)
# ═══════════════════════════════════════════════════════════════════

AI_PROMPT = """You are an intent classifier for an astrology app. You read a user message in ANY language and output JSON telling the software which calculation functions to run.

YOU DO NOT ANSWER QUESTIONS. YOU DO NOT REFUSE. YOU ONLY OUTPUT JSON.
Every topic is valid: marriage, death, health, wealth — classify them all.

CRITICAL — FOLLOW-UP DETECTION:
If the user says something short like "yes", "sure", "tell me", "haan", "ok", "go ahead", "why", "how" — 
look at the PREVIOUS assistant message in conversation history. The assistant may have suggested 
a specific topic (like lucky numbers, compatibility, remedies, mantra, muhurta, weekly forecast etc).
The user is responding to THAT suggestion. Classify based on what was suggested, not the word "yes".

Examples:
- Assistant said "Want to know your lucky numbers?" → User says "yes" → intent = numerology
- Assistant said "Share your partner's details for compatibility" → User says "ok" → intent = compatibility  
- Assistant said "There's a mantra for this" → User says "tell me" → intent = mantra
- Assistant said "Want to know when?" → User says "haan" → intent = same topic with timing focus
- Assistant said "Your Navamsa reveals something deeper" → User says "sure" → intent = overview (navamsa)

If no previous suggestion exists and user just says "yes", treat as general/continuation of previous topic.

VALID INTENTS:
marriage, career, wealth, health, children, education, travel, property, legal, love, spiritual, business, remedies, gemstone, mantra, personality, overview, yogas, dasha, transit, compatibility, muhurta, names, numerology, vastu, location, prashna, daily, weekly, longevity, past_event, hourly, general

OUTPUT THIS JSON ONLY (no markdown, no explanation):
{
"t":"english translation",
"i":"primary_intent from list above",
"q":"when|will_it|what_kind|why|what_to_do|describe|yes_no|best_time|compare|general",
"w":"self|father|mother|spouse|child|sibling|partner|family",
"e":"worried|anxious|curious|excited|confused|sad|hopeful|neutral|desperate|scared",
"h":[7,5],
"y":null,"m":null,"d":null,"hr":null,
"c":null,"n":null,"ev":null,"g":null,
"tone":"warm|caring|confident|encouraging|serene|precise|sacred|strategic|joyful|mystical|decisive|reflective|reassuring|empathetic",
"f":["follow-up suggestion 1","follow-up 2"],
"s":"special instruction for response"
}

h=relevant houses: 1=self 2=wealth 3=siblings 4=mother/home 5=children 6=health 7=marriage 8=death 9=father 10=career 11=gains 12=foreign
y=year, m=month, d=day, hr=time, c=city, n=name, ev=event_type, g=gender
KEEP JSON MINIMAL. Use short keys. No null values — omit them."""


# ═══════════════════════════════════════════════════════════════════
# METHOD MAPPING
# ═══════════════════════════════════════════════════════════════════

METHOD_MAP = {
    'marriage': {
        'when': ['get_classical_analysis:marriage', 'predict_event:marriage', 'kp_event_analysis:marriage', 'validate_event:marriage', 'get_vimshottari_dasha', 'get_pratyantar_dasha', 'get_transit_deep', 'get_future_transits', 'get_navamsa_analysis', 'get_nadi_reading', 'get_bhava_chalit'],
        'what_kind': ['get_navamsa_analysis', 'get_nadi_reading', 'get_kp_complete', 'get_varga_analysis', 'get_personality', 'get_nakshatra_profile'],
        'will_it': ['kp_event_analysis:marriage', 'predict_event:marriage', 'validate_event:marriage', 'get_navamsa_analysis', 'cross_validate_dashas'],
        'best_time': ['predict_event:marriage', 'find_muhurta:marriage', 'get_future_transits', 'get_vimshottari_dasha', 'get_eclipse_calendar'],
        'what_to_do': ['get_remedies', 'get_dynamic_remedies', 'get_gemstone_recommendations', 'get_navamsa_analysis', 'get_chakra_analysis'],
        'default': ['get_classical_analysis:marriage', 'predict_event:marriage', 'kp_event_analysis:marriage', 'get_navamsa_analysis', 'get_nadi_reading', 'validate_event:marriage', 'get_bhava_chalit', 'get_yoga_timing'],
    },
    'career': {
        'when': ['get_classical_analysis:career', 'predict_event:career', 'kp_event_analysis:career', 'validate_event:career', 'get_vimshottari_dasha', 'get_pratyantar_dasha', 'get_transit_deep', 'get_future_transits', 'get_ashtakavarga_transits', 'get_nadi_reading'],
        'what_kind': ['get_career_aptitude', 'get_career_analysis', 'get_nadi_reading', 'get_personality', 'get_nakshatra_profile', 'get_shadbala_complete'],
        'yes_no': ['cast_prashna:job', 'predict_event:career', 'kp_event_analysis:career', 'get_career_aptitude', 'get_transit_aspects'],
        'what_to_do': ['get_career_aptitude', 'get_remedies', 'get_dynamic_remedies', 'get_gemstone_recommendations', 'get_dynamic_mantra'],
        'default': ['get_classical_analysis:career', 'predict_event:career', 'get_career_aptitude', 'get_career_analysis', 'kp_event_analysis:career', 'get_nadi_reading', 'get_vimshottari_dasha', 'get_yoga_timing'],
    },
    'wealth': {
        'when': ['get_classical_analysis:wealth', 'predict_event:wealth', 'kp_event_analysis:wealth', 'validate_event:wealth', 'get_vimshottari_dasha', 'get_future_transits', 'get_ashtakavarga_transits'],
        'default': ['get_classical_analysis:wealth', 'predict_event:wealth', 'kp_event_analysis:wealth', 'get_yogas', 'get_yoga_timing', 'get_nadi_reading', 'validate_event:wealth', 'get_ishta_kashta'],
        'what_to_do': ['get_remedies', 'get_dynamic_remedies', 'get_gemstone_recommendations', 'get_dynamic_mantra'],
    },
    'health': {
        'default': ['get_classical_analysis:health_issue', 'get_medical_report', 'get_chakra_analysis', 'get_nadi_reading', 'predict_event:health_issue', 'get_dynamic_remedies', 'get_shadbala_complete', 'get_bhava_chalit'],
        'what_to_do': ['get_medical_report', 'get_remedies', 'get_dynamic_remedies', 'get_chakra_analysis', 'get_gemstone_recommendations', 'get_dynamic_mantra'],
        'when': ['get_medical_report', 'predict_event:health_issue', 'get_transit_deep', 'get_vimshottari_dasha', 'get_eclipse_calendar'],
    },
    'children': {
        'when': ['get_classical_analysis:childbirth', 'predict_event:childbirth', 'kp_event_analysis:childbirth', 'find_muhurta:medical', 'get_varga_analysis', 'get_nadi_reading', 'get_medical_report', 'get_transit_deep', 'get_future_transits'],
        'best_time': ['predict_event:childbirth', 'find_muhurta:medical', 'get_medical_report', 'get_varga_analysis', 'get_nadi_reading', 'get_eclipse_calendar', 'get_vimshottari_dasha'],
        'default': ['get_classical_analysis:childbirth', 'predict_event:childbirth', 'kp_event_analysis:childbirth', 'get_varga_analysis', 'get_nadi_reading', 'get_medical_report', 'get_bhava_chalit'],
    },
    'education': {
        'when': ['predict_event:education', 'kp_event_analysis:education', 'validate_event:education', 'get_vimshottari_dasha', 'get_future_transits'],
        'default': ['get_classical_analysis:education', 'predict_event:education', 'kp_event_analysis:education', 'get_varga_analysis', 'get_career_aptitude', 'get_nadi_reading', 'get_yoga_timing'],
    },
    'travel': {
        'default': ['get_classical_analysis:foreign', 'predict_event:foreign', 'kp_event_analysis:travel_foreign', 'get_nadi_reading', 'get_yogas', 'validate_event:foreign', 'get_transit_deep', 'get_future_transits'],
    },
    'property': {
        'default': ['get_classical_analysis:property', 'predict_event:property', 'kp_event_analysis:property', 'get_nadi_reading', 'find_muhurta:property', 'validate_event:property'],
    },
    'legal': {
        'default': ['predict_event:litigation', 'kp_event_analysis:litigation_win', 'get_nadi_reading', 'cast_prashna:general'],
    },
    'love': {
        'when': ['predict_event:relationship', 'get_navamsa_analysis', 'get_transit_deep', 'get_future_transits', 'get_vimshottari_dasha'],
        'what_kind': ['get_navamsa_analysis', 'get_nadi_reading', 'get_personality', 'get_nakshatra_profile', 'get_kp_complete'],
        'what_to_do': ['get_remedies', 'get_dynamic_remedies', 'get_chakra_analysis', 'get_gemstone_recommendations'],
        'default': ['predict_event:relationship', 'get_navamsa_analysis', 'get_nadi_reading', 'get_chakra_analysis', 'get_kp_complete', 'get_personality'],
    },
    'spiritual': {
        'default': ['get_classical_analysis:spiritual', 'get_nadi_reading', 'get_chakra_analysis', 'get_yogas', 'get_natal_retrogrades', 'predict_event:spiritual', 'get_pushkara', 'get_dynamic_mantra', 'get_varga_analysis'],
    },
    'business': {
        'default': ['get_classical_analysis:business', 'predict_event:business', 'kp_event_analysis:career', 'get_career_aptitude', 'find_muhurta:business', 'get_nadi_reading', 'get_yogas'],
        'yes_no': ['cast_prashna:business', 'predict_event:business', 'kp_event_analysis:career', 'get_transit_aspects'],
        'best_time': ['find_muhurta:business', 'get_future_transits', 'get_eclipse_calendar', 'predict_event:business'],
    },
    'remedies': {
        'default': ['get_remedies', 'get_dynamic_remedies', 'get_chakra_analysis', 'get_gemstone_recommendations', 'get_dynamic_mantra', 'get_shadbala_complete', 'get_ishta_kashta'],
    },
    'gemstone': {
        'default': ['get_gemstone_recommendations', 'get_remedies'],
    },
    'mantra': {
        'default': ['get_dynamic_mantra', 'get_remedies'],
    },
    'personality': {
        'default': ['get_personality', 'get_nakshatra_profile', 'get_nadi_reading', 'get_chart_strength', 'get_yogas', 'get_yoga_timing', 'get_shadbala_complete', 'get_natal_retrogrades', 'get_pushkara'],
        'describe': ['get_personality', 'get_nakshatra_profile', 'get_nadi_reading', 'get_chart_strength', 'get_yogas', 'get_ishta_kashta', 'get_chakra_analysis'],
    },
    'overview': {
        'default': ['get_chart_strength', 'get_yogas', 'get_yoga_timing', 'get_personality', 'get_life_timeline', 'scan_all_predictions', 'get_nadi_reading', 'get_natal_retrogrades', 'get_pushkara', 'get_ishta_kashta', 'get_shadbala_complete', 'get_vimshottari_dasha'],
    },
    'yogas': {
        'default': ['get_yogas', 'get_yoga_timing', 'get_chart_strength', 'get_pushkara', 'get_natal_retrogrades', 'get_shadbala_complete'],
    },
    'dasha': {
        'default': ['get_vimshottari_dasha', 'get_pratyantar_dasha', 'get_period_analysis', 'get_chara_dasha_analysis', 'cross_validate_dashas', 'get_yoga_timing', 'get_ashtakavarga_transits'],
    },
    'transit': {
        'default': ['get_transit_deep', 'get_ashtakavarga_transits', 'get_transit_aspects', 'get_future_transits', 'get_eclipse_calendar', 'get_sarvatobhadra', 'get_dynamic_remedies'],
    },
    'compatibility': {
        'default': ['match_compatibility', 'get_synastry'],
    },
    'muhurta': {
        'default': ['find_muhurta', 'get_daily_timing'],
    },
    'names': {
        'default': ['get_baby_names', 'get_nakshatra_profile'],
    },
    'numerology': {
        'default': ['get_numerology', 'get_lucky_numbers', 'get_personality', 'get_nakshatra_profile'],
    },
    'vastu': {
        'default': ['get_vastu'],
    },
    'location': {
        'default': ['compare_locations', 'analyze_location', 'get_vastu', 'get_career_aptitude'],
    },
    'prashna': {
        'default': ['cast_prashna'],
    },
    'daily': {
        'default': ['get_realtime_dashboard', 'get_daily_ritual', 'get_color_metal_food', 'get_dynamic_mantra', 'get_biorhythm', 'get_yoga_timing', 'get_transit_aspects', 'get_pratyantar_dasha'],
    },
    'weekly': {
        'default': ['get_weekly_forecast', 'get_realtime_dashboard', 'get_transit_aspects', 'get_eclipse_calendar', 'get_pratyantar_dasha'],
    },
    'longevity': {
        'default': ['get_classical_analysis:health_issue', 'get_medical_report'],
    },
    'past_event': {
        'default': ['explain_past_event', 'get_vimshottari_dasha', 'get_transit_deep'],
    },
    'hourly': {
        'default': ['analyze_hour'],
    },
    'general': {
        'default': ['get_realtime_dashboard', 'get_chart_strength', 'get_daily_ritual', 'get_dynamic_mantra'],
    },
}

WHOM_EXTRA = {
    'father': ['get_medical_report'], 'mother': ['get_vastu'],
    'spouse': ['get_navamsa_analysis'], 'child': ['get_varga_analysis'],
    'partner': ['get_navamsa_analysis', 'get_career_aptitude'],
}

EMOTION_TONE = {
    'worried': 'caring', 'anxious': 'reassuring', 'curious': 'warm',
    'excited': 'warm', 'confused': 'empathetic', 'sad': 'caring',
    'hopeful': 'encouraging', 'neutral': 'warm', 'desperate': 'caring',
    'scared': 'reassuring',
}


# ═══════════════════════════════════════════════════════════════════
# MINIMAL KEYWORD FALLBACK (only when AI is completely dead)
# ═══════════════════════════════════════════════════════════════════

EMERGENCY_KEYWORDS = {
    'marriage': ['marriage', 'married', 'shaadi', 'wedding', 'spouse', 'husband', 'wife'],
    'career': ['career', 'job', 'naukri', 'promotion', 'salary', 'work'],
    'wealth': ['wealth', 'money', 'rich', 'financial', 'income'],
    'health': ['health', 'disease', 'hospital', 'doctor', 'sick'],
    'children': ['child', 'baby', 'pregnant', 'conceive', 'fertility'],
    'education': ['education', 'exam', 'study', 'college', 'university'],
    'travel': ['foreign', 'abroad', 'visa', 'immigration'],
    'property': ['property', 'house', 'flat', 'land', 'vehicle', 'car'],
    'love': ['love', 'boyfriend', 'girlfriend', 'breakup', 'relationship'],
    'spiritual': ['spiritual', 'moksha', 'meditation', 'karma'],
    'business': ['business', 'startup', 'entrepreneur'],
    'remedies': ['remedy', 'upay', 'solution'],
    'gemstone': ['gemstone', 'stone', 'ruby', 'diamond', 'emerald'],
    'mantra': ['mantra', 'chant', 'jaap'],
    'personality': ['about me', 'personality', 'who am i', 'my nature'],
    'overview': ['kundli', 'horoscope', 'chart', 'reading'],
    'yogas': ['yoga', 'yog', 'raja yoga'],
    'dasha': ['dasha', 'mahadasha', 'antardasha'],
    'transit': ['sade sati', 'shani', 'saturn'],
    'compatibility': ['compatibility', 'matching', 'gun milan'],
    'muhurta': ['muhurat', 'auspicious', 'shubh'],
    'names': ['baby name', 'naam', 'naamkaran'],
    'numerology': ['numerology', 'lucky number'],
    'vastu': ['vastu', 'direction'],
    'location': ['which city', 'move to', 'relocat'],
    'daily': ['today', 'aaj', 'right now'],
    'weekly': ['this week', 'weekly'],
    'longevity': ['death', 'lifespan'],
    'general': ['hello', 'hi', 'hey', 'namaste'],
}


class IntentClassifier:
    """Pure AI classifier with smart caching. Works in any language."""

    def __init__(self):
        self._cache = ClassificationCache()
        self._ai_failures = 0
        self._max_failures = 10

    def classify(self, message: str, conversation_history: List[str] = None) -> Dict:
        """
        Classify any message in any language.
        1. Check cache (0ms)
        2. Call AI (2-3s)
        3. Emergency keyword fallback (50ms)
        """
        # Step 1: Cache check
        cached = self._cache.get(message)
        if cached:
            return cached

        # Step 2: AI classification
        if self._ai_failures < self._max_failures:
            try:
                result = self._call_ai(message, conversation_history)
                if result:
                    self._ai_failures = 0
                    self._cache.put(message, result)
                    return result
            except Exception:
                self._ai_failures += 1

        # Step 3: Emergency fallback
        result = self._emergency_fallback(message)
        return result

    async def classify_async(self, message: str, conversation_history: List[str] = None) -> Dict:
        """Async version."""
        cached = self._cache.get(message)
        if cached:
            return cached

        if self._ai_failures < self._max_failures:
            try:
                result = await self._call_ai_async(message, conversation_history)
                if result:
                    self._ai_failures = 0
                    self._cache.put(message, result)
                    return result
            except Exception:
                self._ai_failures += 1

        return self._emergency_fallback(message)

    # ═══════════════════════════════════════════════════════════════
    # AI CLASSIFICATION
    # ═══════════════════════════════════════════════════════════════

    def _call_ai(self, message: str, history: List[str] = None) -> Optional[Dict]:
        """Call AI for classification."""
        user_content = message
        if history and len(history) > 0:
            ctx = "Previous: " + " | ".join(history[-3:])
            user_content = f"{ctx}\nNow: {message}"

        try:
            response = httpx.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'deepseek/deepseek-chat',
                    'max_tokens': 300,
                    'temperature': 0,
                    'messages': [
                        {'role': 'system', 'content': AI_PROMPT},
                        {'role': 'user', 'content': user_content},
                    ],
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                return None

            content = response.json()['choices'][0]['message']['content']
            content = content.strip()
            if content.startswith('```'):
                content = '\n'.join(content.split('\n')[1:])
            if content.endswith('```'):
                content = '\n'.join(content.split('\n')[:-1])
            content = content.replace('```json', '').replace('```', '').strip()

            ai = json.loads(content)
            return self._build_result(ai, message)

        except Exception:
            return None

    async def _call_ai_async(self, message: str, history: List[str] = None) -> Optional[Dict]:
        """Async AI call."""
        user_content = message
        if history and len(history) > 0:
            ctx = "Previous: " + " | ".join(history[-3:])
            user_content = f"{ctx}\nNow: {message}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': 'deepseek/deepseek-chat',
                        'max_tokens': 300,
                        'temperature': 0,
                        'messages': [
                            {'role': 'system', 'content': AI_PROMPT},
                            {'role': 'user', 'content': user_content},
                        ],
                    },
                    timeout=10.0,
                )

                if response.status_code != 200:
                    return None

                content = response.json()['choices'][0]['message']['content']
                content = content.strip()
                if content.startswith('```'):
                    content = '\n'.join(content.split('\n')[1:])
                if content.endswith('```'):
                    content = '\n'.join(content.split('\n')[:-1])
                content = content.replace('```json', '').replace('```', '').strip()

                ai = json.loads(content)
                return self._build_result(ai, message)

        except Exception:
            return None

    def _build_result(self, ai: Dict, original: str) -> Dict:
        """Build standardized result from AI compact JSON."""
        intent = ai.get('i', 'general')
        if intent not in METHOD_MAP:
            intent = 'general'

        q_type = ai.get('q', 'default')
        emotion = ai.get('e', 'neutral')
        about = ai.get('w', 'self')
        houses = ai.get('h', [])
        tone = ai.get('tone', EMOTION_TONE.get(emotion, 'warm'))

        # Get methods
        intent_methods = METHOD_MAP.get(intent, METHOD_MAP['general'])
        methods = list(intent_methods.get(q_type, intent_methods.get('default', [])))

        # Add about-whom extras
        if about != 'self' and about in WHOM_EXTRA:
            for m in WHOM_EXTRA[about]:
                if m not in methods:
                    methods.append(m)

        # Worried → add remedies
        is_worried = emotion in ('worried', 'anxious', 'sad', 'desperate', 'scared')
        if is_worried:
            if 'get_remedies' not in methods:
                methods.append('get_remedies')
            if 'get_dynamic_remedies' not in methods:
                methods.append('get_dynamic_remedies')

        # Time handling
        entities = {}
        time_context = None
        if ai.get('y'):
            entities['year'] = ai['y']
            time_context = {'type': 'year', 'value': ai['y']}
            if f'get_varshaphal:{ai["y"]}' not in ' '.join(methods):
                methods.append(f'get_varshaphal:{ai["y"]}')
        if ai.get('m'):
            entities['month'] = ai['m']
            if not time_context:
                time_context = {'type': 'month', 'value': {'year': ai.get('y', datetime.now().year), 'month': ai['m']}}
        if ai.get('hr'):
            entities['time'] = ai['hr']
        if ai.get('c'):
            entities['city'] = ai['c']
        if ai.get('n'):
            entities['name'] = ai['n']
        if ai.get('ev'):
            entities['event_type'] = ai['ev']
        if ai.get('g'):
            entities['gender'] = ai['g']

        return {
            'primary_intent': intent,
            'secondary_intents': [],
            'confidence': 0.92,
            'methods': methods[:10],
            'method_reasons': {},
            'response_type': intent,
            'emotional_tone': tone,
            'entities': entities,
            'time_context': time_context,
            'is_worried': is_worried,
            'emotion': emotion,
            'about_whom': about,
            'question_type': q_type,
            'relevant_houses': houses if isinstance(houses, list) else [],
            'language': ai.get('l', 'english'),
            'translated': ai.get('t', original),
            'understanding': '',
            'original_message': original,
            'classifier': 'ai',
            'response_style': {
                'tone': tone,
                'length': 'medium',
                'should_include_remedy': is_worried,
                'special_instruction': ai.get('s', ''),
            },
            'follow_up_suggestions': ai.get('f', []),
            'cache_hit': False,
        }

    # ═══════════════════════════════════════════════════════════════
    # EMERGENCY FALLBACK (only when AI is completely dead)
    # ═══════════════════════════════════════════════════════════════

    def _emergency_fallback(self, message: str) -> Dict:
        """Last resort. Simple keyword match."""
        msg = message.lower()
        best = 'general'
        best_score = 0

        for cat, keywords in EMERGENCY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in msg)
            if score > best_score:
                best = cat
                best_score = score

        intent_methods = METHOD_MAP.get(best, METHOD_MAP['general'])
        methods = list(intent_methods.get('default', []))

        worry_words = ['worried', 'tension', 'problem', 'scared', 'help']
        is_worried = any(w in msg for w in worry_words)
        if is_worried and 'get_remedies' not in methods:
            methods.append('get_remedies')

        return {
            'primary_intent': best,
            'secondary_intents': [],
            'confidence': 0.50,
            'methods': methods,
            'method_reasons': {},
            'response_type': best,
            'emotional_tone': 'caring' if is_worried else 'warm',
            'entities': {},
            'time_context': None,
            'is_worried': is_worried,
            'emotion': 'worried' if is_worried else 'neutral',
            'about_whom': 'self',
            'question_type': 'default',
            'relevant_houses': [],
            'language': 'unknown',
            'translated': message,
            'understanding': '',
            'original_message': message,
            'classifier': 'emergency_fallback',
            'response_style': {'tone': 'warm', 'length': 'medium', 'should_include_remedy': is_worried, 'special_instruction': ''},
            'follow_up_suggestions': [],
            'cache_hit': False,
        }

    def get_stats(self) -> Dict:
        return {
            'cache': self._cache.stats(),
            'ai_failures': self._ai_failures,
        }


# Singleton
_classifier = IntentClassifier()

def classify_intent(message: str, history: List[str] = None) -> Dict:
    return _classifier.classify(message, history)

async def classify_intent_async(message: str, history: List[str] = None) -> Dict:
    return await _classifier.classify_async(message, history)

def get_classifier_stats() -> Dict:
    return _classifier.get_stats()
