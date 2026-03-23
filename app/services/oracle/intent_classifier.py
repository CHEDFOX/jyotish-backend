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

AI_PROMPT = """You are the brain of a Jyotish astrology system. Analyze the user message and return JSON.

ONE QUESTION: Does this need birth chart calculations?
If NO (greetings, thanks, emotions, clarifications, general chat) → needs_chart: false
If YES (any life question, astrology topic, specific request) → needs_chart: true

RETURN ONLY JSON:
{
"needs_chart": true,
"houses": [7, 2],
"topic": "marriage",
"calculations": ["classical_rules", "dasha", "navamsa"],
"oracle_instruction": "Answer marriage prospects honestly.",
"max_words": 80,
"language": "english",
"translated": "english translation if not english",
"emotion": "curious",
"is_delivery": false
}

HOUSES: 1=Self 2=Wealth/speech 3=Siblings 4=Mother/property/vehicles 5=Children/education 6=Enemies/legal/disease 7=Marriage/partner 8=Death/secrets/inheritance 9=Father/luck/travel 10=Career/government 11=Gains/friends 12=Foreign/loss/spirituality

CALCULATIONS (pick only what is needed):
classical_rules = Lord+planet analysis for the relevant houses
dasha = Current dasha period
navamsa = D9 soul chart (marriage/partner questions)
transits = Current transits on relevant houses
yogas = Relevant yogas
upapada = Marriage-specific arudha
longevity = 3-pair life span method
numerology = Name/number analysis
compatibility = Partner matching (needs partner data)
remedies = Gemstone/mantra/ritual recommendations
chakra = Energy center analysis

is_delivery: true when user is asking for something SPECIFIC that was teased before (mantra text, lucky numbers, gemstone name). Oracle must GIVE the answer, not tease again.

EXAMPLES:

"will I get married?" → {"needs_chart":true,"houses":[7,2,12],"topic":"marriage","calculations":["classical_rules","dasha","navamsa","upapada"],"oracle_instruction":"Answer marriage prospects. Be honest about difficulties.","max_words":80,"language":"english","emotion":"curious","is_delivery":false}

"will I win my court case?" → {"needs_chart":true,"houses":[6,7,1],"topic":"legal","calculations":["classical_rules","dasha","transits"],"oracle_instruction":"6th house = litigation. Check 6th lord strength vs 7th.","max_words":80,"language":"english","emotion":"worried","is_delivery":false}

"how is my father?" → {"needs_chart":true,"houses":[9,4,8],"topic":"father","calculations":["classical_rules","dasha"],"oracle_instruction":"9th house = father. 4th from 9th shows his longevity.","max_words":80,"language":"english","emotion":"worried","is_delivery":false}

"should I buy a car?" → {"needs_chart":true,"houses":[4,2,11],"topic":"vehicle","calculations":["classical_rules","dasha","transits"],"oracle_instruction":"4th house = vehicles. Check timing.","max_words":80,"language":"english","emotion":"curious","is_delivery":false}

"tell me the mantra" → {"needs_chart":true,"houses":[],"topic":"mantra","calculations":["remedies"],"oracle_instruction":"DELIVER the actual mantra for their nakshatra. Give the Sanskrit text. Do NOT tease.","max_words":100,"language":"english","emotion":"curious","is_delivery":true}

"what are my lucky numbers?" → {"needs_chart":true,"houses":[],"topic":"numerology","calculations":["numerology"],"oracle_instruction":"GIVE the actual lucky numbers. Do not tease.","max_words":60,"language":"english","emotion":"curious","is_delivery":true}

"hello" → {"needs_chart":false,"houses":[],"topic":"greeting","calculations":[],"oracle_instruction":"Respond warmly in 1 line.","max_words":20,"language":"english","emotion":"neutral","is_delivery":false}

"thanks" → {"needs_chart":false,"houses":[],"topic":"gratitude","calculations":[],"oracle_instruction":"Acknowledge warmly. Suggest what else to ask.","max_words":30,"language":"english","emotion":"neutral","is_delivery":false}

"I feel sad today" → {"needs_chart":false,"houses":[],"topic":"emotional","calculations":[],"oracle_instruction":"Be empathetic. Then offer to look at their chart for this period.","max_words":50,"language":"english","emotion":"sad","is_delivery":false}

"kab shaadi hogi?" → {"needs_chart":true,"houses":[7,2,12],"topic":"marriage","calculations":["classical_rules","dasha","navamsa"],"oracle_instruction":"Marriage timing. Be specific.","max_words":80,"language":"hindi","translated":"When will I get married?","emotion":"curious","is_delivery":false}

"which gemstone should I wear?" → {"needs_chart":true,"houses":[1,9],"topic":"gemstone","calculations":["classical_rules","remedies"],"oracle_instruction":"GIVE specific gemstone based on lagna lord. Name, weight, finger, day to wear.","max_words":100,"language":"english","emotion":"curious","is_delivery":true}

"what is a dasha?" → {"needs_chart":false,"houses":[],"topic":"education","calculations":[],"oracle_instruction":"Explain dasha in simple terms. Use analogy of seasons. Connect to their chart if data available.","max_words":80,"language":"english","emotion":"curious","is_delivery":false}

"sex" → {"needs_chart":true,"houses":[7,12,8],"topic":"intimacy","calculations":["classical_rules","dasha","navamsa","chakra"],"oracle_instruction":"Answer about intimacy naturally. 7th=relationships, 12th=bed pleasures, 8th=sexual energy.","max_words":80,"language":"english","emotion":"curious","is_delivery":false}

CONVERSATION HISTORY:
{history}

CLASSIFY THIS MESSAGE:"""


# ═══════════════════════════════════════════════════════════════════
# METHOD MAPPING
# ═══════════════════════════════════════════════════════════════════

METHOD_MAP = {
    # Simplified — classifier now tells us exactly what to calculate
    # This is only used as fallback by _emergency_fallback
    'marriage': {'default': ['get_classical_analysis:marriage', 'get_vimshottari_dasha', 'get_navamsa_analysis']},
    'career': {'default': ['get_classical_analysis:career', 'get_vimshottari_dasha', 'get_yogas']},
    'wealth': {'default': ['get_classical_analysis:wealth', 'get_vimshottari_dasha', 'get_yogas']},
    'health': {'default': ['get_classical_analysis:health_issue', 'get_vimshottari_dasha']},
    'children': {'default': ['get_classical_analysis:childbirth', 'get_vimshottari_dasha']},
    'education': {'default': ['get_classical_analysis:education', 'get_vimshottari_dasha']},
    'travel': {'default': ['get_classical_analysis:foreign', 'get_vimshottari_dasha']},
    'property': {'default': ['get_classical_analysis:property', 'get_vimshottari_dasha']},
    'legal': {'default': ['get_classical_analysis:career', 'get_vimshottari_dasha']},
    'love': {'default': ['get_classical_analysis:love', 'get_vimshottari_dasha', 'get_navamsa_analysis']},
    'spiritual': {'default': ['get_classical_analysis:spiritual', 'get_vimshottari_dasha']},
    'business': {'default': ['get_classical_analysis:business', 'get_vimshottari_dasha']},
    'general': {'default': ['get_vimshottari_dasha', 'get_personality']},
    'remedies': {'default': ['get_remedies', 'get_dynamic_remedies', 'get_gemstone_recommendations']},
    'gemstone': {'default': ['get_gemstone_recommendations']},
    'mantra': {'default': ['get_dynamic_mantra']},
    'numerology': {'default': ['get_numerology', 'get_lucky_numbers']},
    'compatibility': {'default': ['get_synastry']},
    'daily': {'default': ['get_realtime_dashboard']},
    'dasha': {'default': ['get_vimshottari_dasha', 'get_pratyantar_dasha']},
    'yogas': {'default': ['get_yogas', 'get_yoga_timing']},
    'transit': {'default': ['get_transit_deep', 'get_future_transits']},
    'longevity': {'default': ['get_classical_analysis:health_issue', 'get_vimshottari_dasha']},
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
        """Build result from new smart classifier JSON."""
        needs_chart = ai.get('needs_chart', True)
        houses = ai.get('houses', [])
        topic = ai.get('topic', 'general')
        calculations = ai.get('calculations', [])
        oracle_instruction = ai.get('oracle_instruction', '')
        max_words = ai.get('max_words', 80)
        language = ai.get('language', 'english')
        translated = ai.get('translated', original)
        emotion = ai.get('emotion', 'neutral')
        is_delivery = ai.get('is_delivery', False)

        # Build methods from calculations list
        methods = []
        calc_to_method = {
            'classical_rules': 'get_classical_analysis',
            'dasha': 'get_vimshottari_dasha',
            'navamsa': 'get_navamsa_analysis',
            'transits': 'get_transit_deep',
            'yogas': 'get_yogas',
            'upapada': 'get_classical_analysis',
            'longevity': 'get_classical_analysis',
            'numerology': 'get_numerology',
            'compatibility': 'get_synastry',
            'remedies': 'get_remedies',
            'chakra': 'get_chakra_analysis',
        }
        
        for calc in calculations:
            method = calc_to_method.get(calc, '')
            if method and method not in methods:
                # For classical_rules, append the topic
                if calc == 'classical_rules' and topic:
                    event_map = {
                        'marriage': 'marriage', 'career': 'career', 'wealth': 'wealth',
                        'health': 'health_issue', 'children': 'childbirth', 'education': 'education',
                        'travel': 'foreign', 'property': 'property', 'legal': 'career',
                        'love': 'love', 'spiritual': 'spiritual', 'business': 'business',
                        'father': 'health_issue', 'mother': 'health_issue', 'vehicle': 'property',
                        'intimacy': 'love', 'longevity': 'longevity',
                    }
                    event = event_map.get(topic, topic)
                    methods.append(f'get_classical_analysis:{event}')
                else:
                    methods.append(method)

        # Map topic to primary_intent for backward compatibility
        intent = topic
        if intent not in METHOD_MAP:
            intent = 'general'

        is_worried = emotion in ('worried', 'anxious', 'sad', 'desperate', 'scared')
        tone_map = {
            'worried': 'empathetic', 'anxious': 'reassuring', 'curious': 'warm',
            'excited': 'encouraging', 'confused': 'precise', 'sad': 'caring',
            'hopeful': 'encouraging', 'neutral': 'warm', 'desperate': 'empathetic',
            'scared': 'reassuring',
        }
        tone = tone_map.get(emotion, 'warm')

        return {
            'primary_intent': intent,
            'needs_chart': needs_chart,
            'relevant_houses': houses,
            'calculations': calculations,
            'oracle_instruction': oracle_instruction,
            'max_words': max_words,
            'is_delivery': is_delivery,
            'confidence': 0.95,
            'methods': methods[:8],
            'response_type': topic,
            'emotional_tone': tone,
            'tone': tone,
            'entities': {},
            'time_context': None,
            'is_worried': is_worried,
            'emotion': emotion,
            'about_whom': 'self',
            'question_type': 'default',
            'language': language,
            'translated': translated,
            'original_message': original,
            'classifier': 'ai_v2',
            'response_style': {
                'tone': tone,
                'special_instruction': oracle_instruction,
            },
            'follow_up_suggestions': [],
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
