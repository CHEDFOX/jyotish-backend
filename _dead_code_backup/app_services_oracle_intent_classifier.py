"""
JYOTISH ORACLE - INTENT CLASSIFIER v4
The routing brain. LLM reads available systems and decides what to call.

Design principles:
- LLM decides everything - no keyword fallback
- oracle_instruction points to DATA FIELDS only, never to conclusions
  (prevents hallucination - the data decides the verdict, not the instruction)
- All 20 systems documented accurately
- Full timing chain awareness
- 3 history messages for follow-up context
"""

import re
import json
import hashlib
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
from app.core.config import settings


class ClassificationCache:
    def __init__(self, max_size=500, ttl_hours=24):
        self._cache = OrderedDict()
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)

    def _key(self, message: str) -> str:
        msg = re.sub(r'[^\w\s]', '', message.lower().strip())
        words = [w for w in msg.split() if len(w) > 2][:8]
        return hashlib.md5(' '.join(words).encode()).hexdigest()

    def get(self, message: str) -> Optional[Dict]:
        entry = self._cache.get(self._key(message))
        if entry and datetime.now() - entry['time'] < self.ttl:
            result = dict(entry['result'])
            result['original_message'] = message
            result['cache_hit'] = True
            return result
        return None

    def put(self, message: str, result: Dict):
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        self._cache[self._key(message)] = {'result': result, 'time': datetime.now()}

    def stats(self):
        return {'size': len(self._cache)}


AI_PROMPT = """You are the routing brain of a Jyotish Oracle.
Identify the QUESTION TYPE first, then route to the right systems.

CRITICAL RULE: oracle_instruction must point to DATA only.
WRONG: Tell them they will get married in 2026
RIGHT: Read KP VERDICT field. State it directly. Check CONTRADICTION in synthesis.

QUESTION TYPES:

TYPE 1 - NATURE: What kind/type/suits me. No timing needed.
Examples: What career suits me? What kind of person will I marry? What are my strengths?
Systems: classical_rules + yogas + nadi_reading. NO dasha.
oracle_instruction: Read NATURE indicators - 10th house lord, dominant planet, yogas. What KIND suits this chart. Do NOT give timing dates.

TYPE 2 - TIMING: Will it happen / when will it happen.
Examples: Will I get married? When will I get a job? Will I have children?
Systems: classical_rules + dasha + kp_analysis + chara_dasha + yogini_dasha
oracle_instruction: Read KP VERDICT first - state it directly. Give LIFE MAP from synthesis. Give pratyantar date as current window.

TYPE 3 - EMOTIONAL: Feeling states, pain, confusion.
Examples: I feel lost. I am depressed. Why do I feel alone. Hard time.
Systems: dasha + classical_rules + remedies
oracle_instruction: ONE line acknowledgment. Name planet causing this. Give exact date it ends. ONE specific remedy for this planet.

TYPE 4 - SOUL/IDENTITY: Purpose, past life, nature, dharma.
Examples: What is my purpose? Why was I born? What are my strengths?
Systems: classical_rules + yogas + nadi_reading + navamsa
oracle_instruction: Read Atmakaraka meaning. Read nakshatra depth. Read CONVERGENCE. Connect to soul purpose. No timing.

TYPE 5 - BROAD LIFE: Future, big picture, what lies ahead.
Examples: What does the future hold? What does this year look like? When will things improve?
Systems: dasha + life_timeline + classical_rules + transits
oracle_instruction: Give LIFE MAP across all periods. The 3 most important phases coming. Specific years not months.

TYPE 6 - DAILY/PRACTICAL: Today, this week, should I do this now.
Examples: Is today good? Should I sign today? What does this week look like?
Systems: panchanga + weekly_forecast + prashna + dasha
oracle_instruction: Read panchanga for today. Read prashna ruling planets. Give practical guidance.

TYPE 7 - WORLD/MUNDANE: Countries, politics, global events.
Examples: How does global situation affect me? Will India win? Is war coming?
Systems: mundane_national + mundane_personal + dasha
oracle_instruction: Read mundane planetary weather. Connect to this person natal houses. Make it personal.

TYPE 8 - DELIVERY: Give me the specific thing already mentioned.
Examples: Tell me the mantra. What is the gemstone. Give me the numbers.
Systems: remedies + numerology. is_delivery: true
oracle_instruction: Deliver the exact item from data. No preamble. No hook.

AVAILABLE SYSTEMS (needs_chart: true unless noted):

classical_rules - BPHS house analysis. Use for almost all questions.
dasha - Vimshottari timing chain. Use for TIMING questions. NOT for nature questions.
navamsa - D9 soul chart. Marriage nature, spouse description.
transits - Current planets on natal houses. Use for what is happening now.
yogas - Special combinations. Use for nature and identity questions.
kp_analysis - KP YES/NO verdict. Use for timing and event questions.
upapada - Marriage manifestation quality. Use with navamsa for marriage.
remedies - Gemstones, mantras. Use when user is worried or asks what can I do.
chakra - Energy centers. Use for spiritual/healing questions.
numerology - Numbers. Use when asked for lucky numbers or name analysis.
compatibility - Synastry. Use when user mentions a specific person.
prashna - Horary chart NOW. Use for should I do this today questions.
yogini_dasha - Cross-validates timing quality. Use for timing questions.
chara_dasha - Independent timing check. Use for will it happen questions.
varshaphal - Annual return. Use for this year questions.
muhurta - Best timing. Use for when is best time to start questions.
panchanga - Daily almanac. Use for is today good questions.
weekly_forecast - 7-day forecast. Use for this week questions.
life_timeline - 5-year forecast. Use for big picture questions.
nadi_reading - Specific destiny predictions. Use for nature and identity questions.
medical_astrology - ONLY when user explicitly mentions health or disease.
mundane_national - One country chart. needs_chart: false.
mundane_personal - World transits on user natal chart. needs_chart: true.
mundane_compare - Two national charts. needs_chart: false.
mundane_relocation - User planets in target country. needs_chart: true.

SMART ROUTING EXAMPLES:
What career suits me? -> TYPE 1. Systems: classical_rules + yogas + nadi_reading. NO dasha.
When will I get a job? -> TYPE 2. Systems: dasha + kp_analysis + chara_dasha + classical_rules.
What kind of person will I marry? -> TYPE 1. Systems: navamsa + upapada + classical_rules. NO dasha.
Will I get married? -> TYPE 2. Systems: dasha + kp_analysis + chara_dasha + navamsa + classical_rules.
I feel depressed -> TYPE 3. Systems: dasha + remedies.
What is my purpose? -> TYPE 4. Systems: classical_rules + yogas + nadi_reading.
What does this year look like? -> TYPE 5. Systems: dasha + life_timeline + transits.
Is today good for signing? -> TYPE 6. Systems: prashna + panchanga.
How does India situation affect me? -> TYPE 7. Systems: mundane_personal + dasha.
Give me the mantra -> TYPE 8. is_delivery: true. Systems: remedies.

OUTPUT - JSON ONLY, no explanation, no markdown:
{
  "needs_chart": true,
  "question_type": "nature|timing|emotional|soul|broad_life|daily|world|delivery",
  "calculations": ["system1", "system2"],
  "topic": "single_word_topic",
  "houses": [7, 2],
  "oracle_instruction": "data-pointing only - WHERE to look not WHAT to say",
  "max_words": 80,
  "language": "english",
  "translated": "english translation if not english",
  "emotion": "curious|worried|anxious|hopeful|confused|sad|excited|neutral|desperate",
  "is_delivery": false,
  "mundane_country": "",
  "mundane_country2": "",
  "mundane_topic": "general"
}

CONVERSATION HISTORY (last 3 messages):
{history}

USER MESSAGE:"""

CALC_TO_METHOD = {
    'classical_rules':    'get_classical_analysis',
    'dasha':              'get_vimshottari_dasha',
    'navamsa':            'get_navamsa_analysis',
    'transits':           'get_transit_deep',
    'yogas':              'get_yogas',
    'upapada':            'get_classical_analysis',
    'longevity':          'get_classical_analysis',
    'kp_analysis':        'kp_event_analysis',
    'numerology':         'get_numerology',
    'compatibility':      'get_synastry',
    'remedies':           'get_remedies',
    'chakra':             'get_chakra_analysis',
    'prashna':            'cast_prashna',
    'yogini_dasha':       'get_yogini_dasha',
    'chara_dasha':        'get_chara_dasha_analysis',
    'varshaphal':         'get_varshaphal',
    'muhurta':            'get_muhurta',
    'panchanga':          'get_panchanga',
    'weekly_forecast':    'get_weekly_forecast',
    'life_timeline':      'get_life_timeline',
    'nadi_reading':       'get_nadi_reading',
    'medical_astrology':  'get_medical_report',
    'mundane_national':   'get_mundane_national',
    'mundane_compare':    'get_mundane_compare',
    'mundane_personal':   'get_mundane_personal',
    'mundane_cycles':     'get_mundane_cycles',
    'mundane_eclipse':    'get_mundane_eclipse',
    'mundane_relocation': 'get_mundane_relocation',
    'mundane_ingress':    'get_mundane_ingress',
}

EVENT_MAP = {
    'marriage':'marriage', 'love':'love', 'career':'career',
    'wealth':'wealth', 'health':'health_issue', 'longevity':'longevity',
    'children':'childbirth', 'education':'education', 'travel':'foreign',
    'property':'property', 'legal':'legal', 'spiritual':'spiritual',
    'business':'business', 'vehicle':'property', 'promotion':'career',
    'foreign':'foreign', 'relationship':'love', 'job':'career',
    'money':'wealth', 'finance':'wealth', 'pregnancy':'childbirth',
}

TONE_MAP = {
    'worried':'empathetic', 'anxious':'reassuring', 'sad':'caring',
    'curious':'warm', 'excited':'encouraging', 'confused':'precise',
    'hopeful':'encouraging', 'neutral':'warm', 'desperate':'empathetic',
    'frustrated':'direct', 'angry':'calm', 'happy':'warm',
}


class IntentClassifier:
    def __init__(self):
        self._cache = ClassificationCache()

    def classify(self, message: str, history: List[str] = None) -> Dict:
        cached = self._cache.get(message)
        if cached:
            return cached
        result = self._call_ai(message, history) or self._fallback(message)
        self._cache.put(message, result)
        return result

    async def classify_async(self, message: str, history: List[str] = None) -> Dict:
        cached = self._cache.get(message)
        if cached:
            return cached
        result = (await self._call_ai_async(message, history)
                  or self._fallback(message))
        self._cache.put(message, result)
        return result

    def _prompt(self, history: List[str] = None) -> str:
        h = ' | '.join((history or [])[-3:])
        return AI_PROMPT.replace('{history}', h or 'none')

    def _user_content(self, message: str, history: List[str] = None) -> str:
        if history:
            return "Previous: " + " | ".join(history[-3:]) + f"\nNow: {message}"
        return message

    def _call_ai(self, message: str, history: List[str] = None) -> Optional[Dict]:
        try:
            r = httpx.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'deepseek/deepseek-chat',
                    'max_tokens': 400,
                    'temperature': 0,
                    'messages': [
                        {'role': 'system', 'content': self._prompt(history)},
                        {'role': 'user', 'content': self._user_content(message, history)},
                    ],
                },
                timeout=10.0,
            )
            if r.status_code == 200:
                raw = r.json()['choices'][0]['message']['content'].strip()
                return self._parse(raw, message)
        except Exception:
            pass
        return None

    async def _call_ai_async(self, message: str, history: List[str] = None) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': 'deepseek/deepseek-chat',
                        'max_tokens': 400,
                        'temperature': 0,
                        'messages': [
                            {'role': 'system', 'content': self._prompt(history)},
                            {'role': 'user', 'content': self._user_content(message, history)},
                        ],
                    },
                    timeout=10.0,
                )
                if r.status_code == 200:
                    raw = r.json()['choices'][0]['message']['content'].strip()
                    return self._parse(raw, message)
        except Exception:
            pass
        return None

    def _parse(self, raw: str, message: str) -> Optional[Dict]:
        try:
            clean = re.sub(r'^```json\s*|^```\s*|```$', '', raw, flags=re.MULTILINE).strip()
            return self._shape(json.loads(clean), message)
        except Exception:
            return None

    def _fallback(self, message: str) -> Dict:
        return self._shape({
            'needs_chart': True,
            'calculations': ['dasha', 'classical_rules'],
            'topic': 'general',
            'houses': [1],
            'oracle_instruction': (
                'Read current Mahadasha and Antardasha lords from dasha data. '
                'Read general chart strength from classical_rules. '
                'Report what the data shows - do not invent specifics.'
            ),
            'max_words': 80,
            'language': 'english',
            'translated': message,
            'emotion': 'neutral',
            'is_delivery': False,
            'mundane_country': '',
            'mundane_country2': '',
            'mundane_topic': 'general',
        }, message)

    def _shape(self, ai: Dict, original: str) -> Dict:
        emotion = ai.get('emotion', 'neutral')
        tone = TONE_MAP.get(emotion, 'warm')
        topic = ai.get('topic', 'general')
        calculations = ai.get('calculations', ['dasha'])

        methods = []
        for calc in calculations:
            method = CALC_TO_METHOD.get(calc)
            if not method or method in methods:
                continue
            if calc == 'classical_rules':
                event = EVENT_MAP.get(topic, 'general')
                methods.append(f'get_classical_analysis:{event}')
            elif calc == 'kp_analysis':
                event = EVENT_MAP.get(topic, topic)
                methods.append(f'kp_event_analysis:{event}')
            elif calc == 'prashna':
                methods.append(f'cast_prashna:{topic}')
            elif calc == 'chara_dasha':
                methods.append('get_chara_dasha_analysis')
            else:
                methods.append(method)

        oracle_instruction = ai.get('oracle_instruction', '')
        question_type = ai.get('question_type', 'timing')
        if not oracle_instruction or len(oracle_instruction) < 20:
            oracle_instruction = (
                f'Read {topic} indicators from the data. '
                f'Report what the data shows - strength, challenge, or timing. '
                f'Do not state outcomes not present in the data.'
            )

        return {
            'primary_intent':     topic,
            'question_type':     ai.get('question_type', 'timing'),
            'needs_chart':        ai.get('needs_chart', True),
            'relevant_houses':    ai.get('houses', []),
            'calculations':       calculations,
            'methods':            methods[:10],
            'oracle_instruction': oracle_instruction,
            'max_words':          min(ai.get('max_words', 80), 150),
            'is_delivery':        ai.get('is_delivery', False),
            'language':           ai.get('language', 'english'),
            'translated':         ai.get('translated', original),
            'emotion':            emotion,
            'emotional_tone':     tone,
            'tone':               tone,
            'is_worried':         emotion in ('worried', 'anxious', 'sad', 'desperate'),
            'about_whom':         'self',
            'entities':           {},
            'time_context':       None,
            'mundane_country':    ai.get('mundane_country', ''),
            'mundane_country2':   ai.get('mundane_country2', ''),
            'mundane_topic':      ai.get('mundane_topic', 'general'),
            'original_message':   original,
            'classifier':         'ai_v4',
            'cache_hit':          False,
            'response_style':     {'tone': tone},
        }

    def get_stats(self):
        return {'cache': self._cache.stats()}


_classifier = IntentClassifier()


def classify_intent(message: str, history: List[str] = None) -> Dict:
    return _classifier.classify(message, history)


async def classify_intent_async(message: str, history: List[str] = None) -> Dict:
    return await _classifier.classify_async(message, history)


def get_classifier_stats() -> Dict:
    return _classifier.get_stats()
