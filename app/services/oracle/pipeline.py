"""
ORACLE PIPELINE v3
Flow:
  1. Classifier → topic, emotion, language, sections[]
  2. Base chart (system-specific, always included)
  3. Requested sections (raw data, not pre-interpreted)
  4. User memory
  5. Assemble: persona + chart + sections + memory
  6. Return for one LLM call

Two LLM calls total:
  - Classifier: ~$0.0001  (tiny prompt)
  - Oracle:     ~$0.0008  (reads real data)
"""

from datetime import datetime
from typing import Dict


def process_oracle_query(user_message: str, birth_data: Dict = None,
                          conversation_history: list = None,
                          system: str = "bphs",
                          extras: Dict = None) -> Dict:
    """Main entry point."""
    start_time = datetime.now()
    extras = extras or {}
    system = (system or "bphs").lower()

    # ─── API config ───
    from app.core.config import settings
    try:
        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL
    except Exception:
        api_key = None
        model = None

    # ─── Classify ───
    from .classifier import classify
    history = conversation_history or []
    intent = classify(user_message, api_key, model, system, history)

    # ─── Engine ───
    engine = None
    cache_hit = False
    if birth_data:
        from .engine_cache import get_cached_engine
        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0)
        )
        engine, cache_hit = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])

    if not engine:
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        return {
            'system_prompt': _build_no_chart_prompt(system),
            'user_prompt': user_message,
            'birth_data': birth_data,
            'intent': _format_intent(intent),
            'data_packet': {'oracle_briefing': 'No birth data provided.'},
            'cache_hit': False,
            'sections_built': [],
            'processing_time_ms': round(elapsed),
        }

    # ─── Base chart ───
    base_chart = _build_base_chart(engine, system)

    # ─── Sections ───
    sections = intent.get("sections", [])
    topic = intent.get("topic", "general")
    sections_text = _build_sections(engine, system, sections, topic, extras)

    # ─── Portrait (replaces old memory) ───
    portrait_text = ""
    if birth_data:
        try:
            from .portrait import build_portrait_block
            portrait_text = build_portrait_block(birth_data)
        except Exception:
            pass

    # ─── Assemble ───
    briefing = base_chart
    if sections_text:
        briefing += "\n\n" + sections_text
    if portrait_text:
        briefing += "\n\n" + portrait_text

    # ─── System prompt ───
    system_prompt = _build_system_prompt(system, intent, briefing, user_message)

    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    return {
        'system_prompt': system_prompt,
        'user_prompt': user_message,
        'birth_data': birth_data,
        'intent': _format_intent(intent),
        'data_packet': {'oracle_briefing': briefing},
        'cache_hit': cache_hit,
        'sections_built': sections,
        'processing_time_ms': round(elapsed),
        # Keep backward compatibility
        'methods_fired': sections,
    }


def _format_intent(intent: Dict) -> Dict:
    return {
        'primary': intent.get('topic', 'general'),
        'question_type': intent.get('question_type', 'general'),
        'tone': intent.get('emotional_tone', 'neutral'),
        'language': intent.get('language', 'english'),
        'confidence': 'high',
        'classifier': 'v3_sections',
        'sections_requested': intent.get('sections', []),
        # backward compat
        'follow_up_suggestions': [],
    }


# ═══════════════════════════════════════════════════════════
# BASE CHART
# ═══════════════════════════════════════════════════════════

def _build_base_chart(engine, system: str) -> str:
    if system == 'kp':
        from ..kp.sections import build_base_chart
        return build_base_chart(engine)
    elif system == 'western':
        from ..western.sections import build_base_chart
        return build_base_chart(engine)
    elif system == 'chinese':
        from ..chinese.sections import build_base_chart
        return build_base_chart(engine)
    elif system == 'mandala':
        from ..mandala.sections import build_base_chart
        return build_base_chart(engine)
    else:
        from .sections_bphs import build_base_chart
        return build_base_chart(engine)


# ═══════════════════════════════════════════════════════════
# SECTIONS
# ═══════════════════════════════════════════════════════════

def _build_sections(engine, system: str, sections: list, topic: str, extras: dict) -> str:
    if not sections:
        return ""
    if system == 'kp':
        from ..kp.sections import build_sections
        return build_sections(engine, sections, topic, extras)
    elif system == 'western':
        from ..western.sections import build_sections
        return build_sections(engine, sections, topic, extras)
    elif system == 'chinese':
        from ..chinese.sections import build_sections
        return build_sections(engine, sections, topic, extras)
    elif system == 'mandala':
        from ..mandala.sections import build_sections
        return build_sections(engine, sections, topic)
    else:
        from .sections_bphs import build_sections
        return build_sections(engine, sections, topic)


# ═══════════════════════════════════════════════════════════
# PERSONAS
# ═══════════════════════════════════════════════════════════

PERSONAS = {
    'bphs': """You are the voice of the stars — ancient, warm, mystical, true.
You speak to the human like an old friend who has been watching them from the beginning.
When they ask WHAT, speak in feeling and image. When they ask HOW, become the teacher with names and mechanics.
Your words are few, your knowing is deep. End with something that stays.
4 to 7 flowing sentences. No headers, no lists, no bullet points. Just voice.""",

    'kp': """You are a KP astrologer — precise, scientific, evidence-based.
You speak in significators, sub-lords, cuspal sub-lords, and house groupings.
When you say YES or NO, cite the cuspal sub-lord and its signified houses.
When you give timing, reference DBA periods and transit triggers.
4 to 6 precise sentences. No poetry. No headers. Just analysis.""",

    'western': """You are a Western astrologer — psychologically insightful, empowering, growth-oriented.
You speak in aspects, configurations, elements, and houses. Warm but modern.
You focus on self-awareness, potential, and choice — not fate.
Reference the Big Three, major aspects, and current transits.
4 to 6 insightful sentences. No bullet points. Flowing psychological insight.""",


    'mandala': """You are a geodetic astrologer — the cartographer of destiny.
You read the earth as a mirror of the sky. You know where on this planet each person's power lives.
When they ask about locations, you see planetary lines crossing continents.
When they ask about direction, you feel the pull of the compass.
Your language is grounded yet vast — like looking at the earth from space.
4 to 6 sentences. Practical, specific, empowering. No bullet points.""",
    'chinese': """You are a Chinese astrology master — philosophical, balanced, elemental.
You speak in Heavenly Stems, Earthly Branches, Five Elements, and Qi flow.
You see life as cycles within cycles. Your language is calm and wise.
When giving advice, focus on what element to add or reduce.
4 to 6 wise sentences. No bullet points. Flowing insight like a river.""",
}


def _build_system_prompt(system: str, intent: Dict, briefing: str, user_message: str) -> str:
    persona = PERSONAS.get(system, PERSONAS['bphs'])
    language = intent.get("language", "english")
    emotion = intent.get("emotional_tone", "neutral")

    lang_note = ""
    if language and language.lower() not in ("english", "en"):
        lang_note = f"\nRespond in {language}."

    emotion_notes = {
        "worried": "\nAcknowledge their worry first, then read.",
        "anxious": "\nCut through anxiety. One clear direction.",
        "sad": "\nAcknowledge. Then show the path through.",
        "desperate": "\nImmediate warmth. One practical step.",
    }
    emotion_note = emotion_notes.get(emotion, "")
    today = datetime.now().strftime("%B %d, %Y")

    return f"""{persona}

TODAY: {today}{lang_note}{emotion_note}

{briefing}

Maximum 120 words. One flowing response. End with something that stays."""


def _build_no_chart_prompt(system: str) -> str:
    persona = PERSONAS.get(system, PERSONAS['bphs'])
    return f"""{persona}

No birth chart available. Respond based on general principles.
If the question requires a birth chart, gently ask for birth details.
Maximum 80 words."""


# ═══════════════════════════════════════════════════════════
# MEMORY
# ═══════════════════════════════════════════════════════════

def store_oracle_memory(birth_data: Dict, user_message: str,
                         oracle_response: str, hook: str, intent: Dict):
    try:
        from .user_memory import store_user_memory
        store_user_memory(birth_data, user_message, oracle_response, hook, intent)
    except Exception:
        pass


def get_oracle_stats() -> Dict:
    from .engine_cache import get_cache_stats
    return {'cache': get_cache_stats()}
