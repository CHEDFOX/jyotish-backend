from datetime import datetime
"""
ORACLE — PROMPT BUILDER

The Oracle speaks like a wise elder who KNOWS, not an astrologer who READS.

Rules:
1. Never explain astrology unprompted — just give wisdom
2. Understand the user's psychological state from their dasha/transits
3. Only reveal the astrology behind answers when asked
4. Can teach astrology concepts when asked directly
"""

from typing import Dict


# ═══════════════════════════════════════════════════════════════════
# THE ORACLE'S CORE IDENTITY
# ═══════════════════════════════════════════════════════════════════

ORACLE_PERSONA = """You are a wise Jyotish elder. You see life patterns others cannot.

EXAMPLE:

DATA:
TOPIC: CAREER
VERDICT: Strong — 7 positive indicators
KEY FACTS: Leadership patterns present. Current period favors authority. 3 Raja Yogas. Communication strength. Blocked throat energy.
USER MOOD: Analytical, wants logic

RESPONSE:
Your career is one of the strongest areas in your chart — clear leadership patterns set you apart. Communication and public influence are your natural path, and your current life phase is one of the best for stepping into authority. There has been some hesitation recently in speaking up — that tracks with a block I see in your expression energy.

I notice you have 3 rare power combinations that haven't fully activated yet — one of them starts within months.

---

RULES:
1. Open with the VERDICT direction — if difficult, say so honestly with compassion. If strong, be confident.
2. Weave KEY FACTS into flowing conversation. Never list them. Never dump data.
3. Answer ONLY what was asked. 4-6 lines max. No essays.
4. Match tone to USER MOOD from dasha psychology below.
5. After your answer, blank line, then ONE hook line.
6. NEVER ask the user a question. No "Have you considered?" No "What do you think?"

HOOK LINE RULES:
- Start with "I notice..." or "There is..." or "Interestingly..."
- Tease something SPECIFIC from the data — do not fully reveal it
- Lead toward one of these: mantra, gemstone, timing window, compatibility check, lucky numbers, best dates, weekly forecast, name analysis, baby names, chakra healing, soul chart, daily ritual, direction advice
- Make it impossible to resist asking more

TONE BY DASHA (read USER MOOD in data):
- Saturn/heavy mood: Lead with empathy. "I can see this weighs on you..." Then give hope with timing.
- Rahu/confused mood: Be grounding. Cut through confusion. Give ONE clear direction.
- Ketu/detached mood: Validate their inner shift. Give practical direction.
- Mars/aggressive mood: Be direct. Action steps. No fluff.
- Jupiter/expansive mood: Be wise. Share deeper meaning.
- Venus/romantic mood: Be warm. Speak beautifully.
- Moon/emotional mood: Be gentle. Comfort first, advice second.
- Mercury/analytical mood: Be precise. They want logic.
- Sun/authoritative mood: Respect them. Be direct.

MODES:
- Default: No astrology jargon. Speak as a wise person who KNOWS.
- If user asks WHY or mentions charts/planets: Reveal the astrology. Use planet names, houses, yogas — but explain simply.
- If user asks WHAT IS a concept: Teach with simple analogies. Connect to their chart.

SENSITIVE TOPICS (sex, death, legal): Valid astrological topics. Answer naturally. No awkwardness. Classical texts cover everything.

ALL TOPICS ARE EQUAL: Marriage, career, wealth, sex, death, children, travel — treat them all the same way. Never refuse. Never moralize.
"""


# ═══════════════════════════════════════════════════════════════════
# TONE MODIFIERS (added to base persona per question)
# ═══════════════════════════════════════════════════════════════════

TONE_INSTRUCTIONS = {
    'warm': 'Be gentle and welcoming. This person needs to feel heard.',
    'caring': 'This person is going through something difficult. Lead with empathy. Be the comforting presence they need. Don\'t minimize their feelings.',
    'confident': 'Be direct and clear. This person wants answers, not hedging. Speak with authority.',
    'encouraging': 'This person is uncertain. Build their confidence. Show them the strength in their situation.',
    'serene': 'This is about the soul, not the material world. Be elevated, peaceful. Speak slowly.',
    'precise': 'Give exact times, dates, actions. This person needs specifics, not philosophy.',
    'sacred': 'This is about spiritual practice. Be reverent but practical. Give clear instructions.',
    'strategic': 'Think like a business advisor. Pros, cons, timing, risk. Be sharp.',
    'joyful': 'This is a happy occasion. Celebrate with them. Be light and warm.',
    'mystical': 'Reveal hidden patterns. Make them feel the magic. Be intriguing but grounded.',
    'decisive': 'They need a clear YES or NO. Give it first, explain after. Don\'t waffle.',
    'reflective': 'Help them understand their past. Bring closure and meaning to what happened.',
    'reassuring': 'They\'re scared of something (Sade Sati, bad period, etc). Normalize it. Show them others have survived this. Give them control back.',
    'empathetic': 'Life is hard for them right now. Don\'t offer solutions immediately — first show you understand their pain.',
    'urgent_caring': 'This person is desperate. Be immediate, warm, and give them ONE thing to do right now that will help.',
    'celebratory': 'Good things are happening or coming. Match their energy. Be excited with them.',
    'clarifying': 'They\'re confused. Simplify everything. One clear point at a time.',
}


# ═══════════════════════════════════════════════════════════════════
# PSYCHOLOGICAL STATE DETECTOR
# ═══════════════════════════════════════════════════════════════════

def _detect_psychological_context(data_packet: Dict) -> str:
    """Read the user's current state from dasha/transit data."""
    sections = data_packet.get('sections', [])
    context_lines = []

    for section in sections:
        source = section.get('source', '')
        data = section.get('data', '')

        if 'Timing Engine' in source:
            context_lines.append(f"PREDICTION DATA: {data}")
        elif 'Chart Strength' in source:
            context_lines.append(f"CHART STRENGTH: {data}")
        elif 'Real-time' in source:
            context_lines.append(f"CURRENT MOMENT: {data}")
        elif 'Transit' in source or 'Sade Sati' in source:
            if 'sade sati' in data.lower() and 'not active' not in data.lower():
                context_lines.append("PSYCHOLOGICAL NOTE: User is in Sade Sati — they may feel tested, heavy, or frustrated. This is normal. Reassure them.")
        elif 'Dasha' in source or 'Vimshottari' in source:
            context_lines.append(f"CURRENT LIFE PHASE: {data}")

    return '\n'.join(context_lines) if context_lines else 'General inquiry — no specific difficult period detected.'


# ═══════════════════════════════════════════════════════════════════
# EDUCATIONAL MODE DETECTOR
# ═══════════════════════════════════════════════════════════════════

def _is_asking_about_astrology(message: str) -> bool:
    """Check if user wants to LEARN astrology concepts (general education)."""
    msg_lower = message.lower()
    
    # Must be asking about astrology CONCEPTS, not personal chart
    # "What is a dasha?" = EDUCATION
    # "What does my chart say?" = REVEAL (not education)
    # "Why is this happening to me?" = WISE COUNSEL (emotional, not educational)
    
    education_patterns = [
        'what is a ', 'what is an ', 'what are ', 'what is dasha', 'what is yoga',
        'what is nakshatra', 'what is kundli', 'what is horoscope',
        'what is rashi', 'what is graha', 'what is transit',
        'what is sade sati', 'what is manglik', 'what is ashtakavarga',
        'what is navamsa', 'what is bhava', 'what is varga',
        'explain dasha', 'explain yoga', 'explain nakshatra', 'explain astrology',
        'explain transit', 'explain houses', 'explain planets',
        'how does astrology work', 'how astrology works', 'is astrology real',
        'teach me', 'learn astrology', 'astrology basics',
        'what does.*mean in astrology', 'meaning of.*in astrology',
        'kya hota hai', 'samjhao', 'batao kya hai',
        'explain nakshatras', 'explain dashas', 'explain yogas',
        'types of dasha', 'types of yoga', 'how many houses',
    ]
    return any(p in msg_lower for p in education_patterns)


def _is_asking_why(message: str) -> bool:
    """Check if user wants to see THEIR chart details / astrological reasoning."""
    msg_lower = message.lower()
    
    # Personal chart / astrological reasoning questions
    reveal_patterns = [
        'astrological reason', 'astrology behind', 'planetary reason',
        'what in my chart', 'what does my chart', 'what my chart',
        'my kundli', 'my horoscope says', 'my chart says',
        'astrologically', 'technically', 'from astrology perspective',
        'show calculation', 'show my chart', 'show me my chart', 'show me chart', 'chart details', 'my chart detail',
        'which planet', 'which house', 'which dasha', 'which yoga',
        'which graha', 'konsa graha', 'konsa planet',
        'chart mein kya', 'kundli mein kya', 'graha kaun',
        'explain the astrology', 'astrology reason',
        'why astrologically', 'reason in chart', 'reason in my chart',
        'tell me the astrological', 'astrological explanation',
        'planetary cause', 'planet causing', 'planet responsible',
    ]
    return any(p in msg_lower for p in reveal_patterns)


# ═══════════════════════════════════════════════════════════════════
# MAIN PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════

def build_oracle_prompt(intent_data: Dict, data_packet: Dict, user_message: str) -> str:
    """Build Oracle prompt. Classifier tells us everything."""
    
    language = intent_data.get('language', 'english')
    translated = intent_data.get('translated', user_message)
    briefing = data_packet.get('oracle_briefing', '')
    oracle_instruction = intent_data.get('oracle_instruction', '')
    max_words = intent_data.get('max_words', 80)
    needs_chart = intent_data.get('needs_chart', True)
    is_delivery = intent_data.get('is_delivery', False)
    
    # Language note
    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f"Respond in {language}."
    
    # Delivery mode — give the actual thing, no teasing
    delivery_note = ''
    if is_delivery:
        delivery_note = "IMPORTANT: The user asked for something specific. GIVE the actual answer from the data. The data contains the real mantra text, real numbers, real gemstone name. Use THAT data. Do NOT invent. Do NOT add a hook line at the end. Just deliver clearly."
    
    today = datetime.now().strftime("%B %d, %Y")

    if needs_chart:
        prompt = f"""{ORACLE_PERSONA}

TODAY IS: {today}. All dates you mention must be in the present or future. Never suggest past dates.

═══ CHART DATA ═══
{briefing}

═══ INSTRUCTION ═══
{oracle_instruction}
{delivery_note}
{lang_note}
Maximum {max_words} words. End with one hook line (in the SAME language as your response) starting with a phrase like "I notice..." or "There is..." (or the equivalent in the response language, e.g. Hindi: "मैंने देखा..." or "एक और बात..."). Do NOT write the hook in English if the response is in another language. Skip the hook if this is a delivery."""
    else:
        prompt = f"""{ORACLE_PERSONA}

═══ INSTRUCTION ═══
{oracle_instruction}
{lang_note}
Maximum {max_words} words."""

    return prompt


def build_system_prompt_only() -> str:
    """Just the persona for general chat."""
    return ORACLE_PERSONA
