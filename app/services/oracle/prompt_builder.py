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
    """Build the Oracle prompt. DATA FIRST, rules after. Short."""
    
    language = intent_data.get('language', 'english')
    translated = intent_data.get('translated', user_message)
    briefing = data_packet.get('oracle_briefing', '')
    is_worried = intent_data.get('is_worried', False)
    
    msg_lower = user_message.lower()
    
    # Detect MODE from user's message
    # MODE 1: REVEAL — user asks WHY or wants to see astrology behind the answer
    reveal_words = ['why', 'reason', 'kyu', 'kyon', 'explain astrology', 'show chart', 
                    'which planet', 'which house', 'what yoga', 'kundli', 'my chart']
    wants_reveal = any(w in msg_lower for w in reveal_words)
    
    # MODE 2: EDUCATION — user wants to LEARN about astrology concepts
    edu_words = ['what is', 'what are', 'meaning of', 'tell me about', 'explain', 'how does',
                 'teach', 'learn', 'what does', 'kya hota hai', 'samjhao',
                 'dasha', 'yoga', 'transit', 'nakshatra', 'rashi', 'graha', 'bhava',
                 'ashtakavarga', 'shadbala', 'navamsa', 'mahadasha', 'antardasha']
    wants_education = any(w in msg_lower for w in edu_words) and not wants_reveal
    
    # MODE 3: WISE COUNSEL — default for life questions
    
    if wants_reveal:
        mode = """MODE: REVEAL ASTROLOGY
The user wants to see the astrology behind your answer. NOW you can and SHOULD:
- Name specific planets and their positions
- Mention house numbers and what they mean
- Reference specific BPHS rules from the data
- Explain yogas and dashas by name
- Cite sources like "BPHS 24.84 says..."
BUT still explain everything in simple language. Like teaching a curious friend.
Keep it 6-10 lines. Show the classical rules that fired."""
    elif wants_education:
        mode = """MODE: EDUCATION
The user wants to learn about an astrology concept. Teach them:
- Use simple everyday analogies. "Dasha is like seasons of life — each planet gets its turn to drive."
- Give real examples from their chart when possible
- Keep it 4-6 lines per concept
- Make them feel smart, not overwhelmed
- End with a hook connecting the concept to their life
- If they ask about a specific term, define it simply then show how it appears in their chart"""
    else:
        mode = """MODE: WISE COUNSEL
No astrology jargon. No planet names. No house numbers. No yoga names.
Speak as a wise person who KNOWS but doesn't show calculations.
Convert all chart data into natural human language.
Example: Your partner likely comes from a different background -- NOT -- 7th lord in 12th house"""
    
    # Language note
    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f"User wrote in {language}: \"{translated}\". Respond in their language naturally. Use warm {language} terms where appropriate."
    
    # Worried note
    worried_note = ''
    if is_worried:
        worried_note = "⚠️ USER IS WORRIED/ANXIOUS. First line MUST acknowledge their feeling with empathy. Never start with predictions when someone is scared."
    
    prompt = f"""{ORACLE_PERSONA}

═══ THIS USER'S CHART DATA ═══
{briefing}

═══ MODE ═══
{mode}

{worried_note}
{lang_note}

Respond now. Use the chart data above. Be specific. Hook at the end."""

    return prompt


def build_system_prompt_only() -> str:
    """Just the persona for general chat."""
    return ORACLE_PERSONA
