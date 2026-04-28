"""
ORACLE PIPELINE v2
The new flow:
  1. Build organized chart (906 chars, cached)
  2. Cast Prashna for this moment
  3. LLM selector picks 4-8 methods for this question
  4. Fire selected methods, extract verdict lines
  5. Recall user memory
  6. Assemble clean briefing: chart + prashna + verdicts + memory
  7. Send to Oracle LLM
  8. Store memory after response

Two LLM calls total:
  - Selector: ~$0.0002, ~500ms
  - Oracle:   ~$0.0006, ~3-4s
  Total: ~$0.0008 per query
"""

from datetime import datetime
from typing import Dict, List, Optional
import traceback


def process_oracle_query(user_message: str, birth_data: Dict = None,
                          conversation_history: list = None) -> Dict:
    """Main entry point — replaces old pipeline."""
    start_time = datetime.now()

    # ─── STEP 0: Get API config ───
    from app.core.config import settings
    api_key = settings.OPENROUTER_API_KEY
    model = settings.OPENROUTER_MODEL

    # ─── STEP 1: Classify intent (still needed for tone, language, emotion) ───
    from .intent_classifier import classify_intent
    history = conversation_history or []
    intent = classify_intent(user_message, history)

    # ─── STEP 2: Get or create engine ───
    engine = None
    if birth_data:
        from .engine_cache import get_cached_engine
        birth_dt = datetime(
            birth_data['year'], birth_data['month'], birth_data['day'],
            birth_data.get('hour', 12), birth_data.get('minute', 0)
        )
        engine, cache_hit = get_cached_engine(birth_dt, birth_data['lat'], birth_data['lng'])
    else:
        cache_hit = False

    if not engine:
        # No birth data — generic response
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        return {
            'system_prompt': _build_no_chart_prompt(intent, user_message),
            'user_prompt': user_message,
            'birth_data': birth_data,
            'intent': _format_intent(intent),
            'data_packet': {'oracle_briefing': 'No birth data.'},
            'cache_hit': False,
            'methods_fired': [],
            'processing_time_ms': round(elapsed),
        }

    # ─── STEP 3: Build organized chart (cached on engine) ───
    from .chart_builder import build_organized_chart, build_prashna_section, build_memory_section
    chart_text = build_organized_chart(engine)

    # ─── STEP 4: Cast Prashna ───
    prashna_category = _get_prashna_category(intent)
    prashna_text = build_prashna_section(engine, prashna_category)

    # ─── STEP 5: LLM selects methods ───
    from .method_selector import select_methods
    selected_methods = select_methods(user_message, api_key, model)

    # ─── STEP 6: Fire selected methods, extract verdicts ───
    verdicts_text, methods_fired = _fire_and_extract(engine, selected_methods)

    # ─── STEP 7: Recall user memory ───
    memory_text = ""
    if birth_data:
        memory_text = build_memory_section(birth_data)

    # ─── STEP 8: Assemble briefing ───
    briefing = _assemble_briefing(chart_text, prashna_text, verdicts_text, memory_text)

    # ─── STEP 9: Build system prompt ───
    system_prompt = _build_system_prompt(intent, briefing, user_message)

    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    return {
        'system_prompt': system_prompt,
        'user_prompt': user_message,
        'birth_data': birth_data,
        'intent': _format_intent(intent),
        'data_packet': {
            'oracle_briefing': briefing,
            'user_memory': memory_text,
        },
        'cache_hit': cache_hit,
        'methods_fired': methods_fired,
        'processing_time_ms': round(elapsed),
    }


# ═══════════════════════════════════════════════════════════════
# FIRE & EXTRACT — call engine methods, extract verdict lines
# ═══════════════════════════════════════════════════════════════

def _fire_and_extract(engine, selected_methods: List[str]) -> tuple:
    """
    Fire each selected method on the engine.
    Extract ONE verdict line from each result.
    Returns (verdicts_text, methods_fired_list)
    """
    lines = []
    fired = []

    for method_spec in selected_methods:
        try:
            # Parse "method_name" or "method_name:arg" or "method_name:arg1:arg2"
            parts = method_spec.split(":")
            method_name = parts[0].strip()
            args = [p.strip() for p in parts[1:]] if len(parts) > 1 else []

            method = getattr(engine, method_name, None)
            if not method:
                continue

            # Convert string args to appropriate types
            converted_args = []
            for arg in args:
                # Try int
                try:
                    converted_args.append(int(arg))
                    continue
                except ValueError:
                    pass
                # Try float
                try:
                    converted_args.append(float(arg))
                    continue
                except ValueError:
                    pass
                # Keep as string
                converted_args.append(arg)

            result = method(*converted_args) if converted_args else method()
            fired.append(method_name)

            # Extract verdict line(s) from result
            verdict = _extract_verdict(method_name, result)
            if verdict:
                lines.append(verdict)

        except Exception as e:
            # Silent fail — don't break the pipeline for one method
            fired.append(method_name + " (error)")
            continue

    return "\n".join(lines), fired


def _extract_verdict(method_name: str, result) -> str:
    """
    Extract ONE concise verdict line from a method's result.
    This is the art — pull the ANSWER, not the data.
    """
    if result is None:
        return ""

    if isinstance(result, str):
        return result[:200] if len(result) > 20 else ""

    if not isinstance(result, dict):
        if isinstance(result, list) and result:
            # Lists (like yoga_timing, transit_aspects) — summarize
            return f"{method_name}: {len(result)} items found"
        return ""

    mn = method_name.lower()

    # ─── Chart Promise / Classical Analysis ───
    if "chart_promise" in mn or "classical" in mn:
        summary = result.get("summary", "")
        supports = result.get("supports", result.get("supporting_count", 0))
        opposes = result.get("opposes", result.get("opposing_count", 0))
        if isinstance(supports, list):
            supports = len(supports)
        if isinstance(opposes, list):
            opposes = len(opposes)
        rules = result.get("rules_fired", 0)
        denial = result.get("denial_count", result.get("denials", 0))

        # Include top supporting/opposing rules if available
        top_rules = ""
        support_list = result.get("supports", [])
        oppose_list = result.get("opposes", [])
        if isinstance(support_list, list) and support_list:
            texts = []
            for r in support_list[:2]:
                t = r.get("text", str(r)) if isinstance(r, dict) else str(r)
                texts.append(t[:80])
            top_rules += " Supports: " + "; ".join(texts) + "."
        if isinstance(oppose_list, list) and oppose_list:
            texts = []
            for r in oppose_list[:2]:
                t = r.get("text", str(r)) if isinstance(r, dict) else str(r)
                texts.append(t[:80])
            top_rules += " Opposes: " + "; ".join(texts) + "."

        if summary:
            return f"Classical/Promise: {summary} ({supports} support, {opposes} oppose, {denial} denials).{top_rules}"
        return ""

    # ─── KP Event Analysis ───
    if "kp_event" in mn or "kp_verify" in mn:
        promised = result.get("promised", result.get("is_promised"))
        verdict = result.get("verdict", result.get("kp_verdict", ""))
        if promised is not None:
            word = "PROMISED" if promised else "NOT PROMISED"
            return f"KP System: {word}. {verdict}"
        return f"KP: {verdict}" if verdict else ""

    # ─── Predict Event (Timing) ───
    if "predict_event" in mn:
        window = result.get("window", result.get("best_window", {}))
        if isinstance(window, dict) and window:
            start = window.get("start", window.get("from", ""))
            end = window.get("end", window.get("to", ""))
            strength = window.get("strength", window.get("quality", ""))
            return f"Timing window: {start} to {end} ({strength})"
        summary = result.get("summary", "")
        if summary:
            return f"Timing: {summary}"
        return ""

    # ─── Navamsa Analysis ───
    if "navamsa" in mn:
        spouse = result.get("spouse_description", result.get("partner_nature", ""))
        venus = result.get("venus_navamsa", {})
        v_text = venus.get("interpretation", "") if isinstance(venus, dict) else ""
        parts = []
        if spouse:
            parts.append(f"Spouse nature: {spouse}")
        if v_text:
            parts.append(f"Venus in D9: {v_text}")
        return "D9: " + ". ".join(parts) if parts else ""

    # ─── Career Analysis / Aptitude ───
    if "career_analysis" in mn:
        field = result.get("recommended_field", result.get("career_type", ""))
        return f"D10 Career: {field}" if field else ""

    if "career_aptitude" in mn:
        top = result.get("top_fields", result.get("aptitude", []))
        if isinstance(top, list) and top:
            fields = []
            for f in top[:3]:
                if isinstance(f, dict):
                    fields.append(f"{f.get('field', '')}: {f.get('score', '')}%")
                else:
                    fields.append(str(f))
            return "Career aptitude: " + ", ".join(fields)
        return ""

    # ─── Jaimini Karakas ───
    if "karaka" in mn and "karakamsa" not in mn:
        ak = result.get("atmakaraka", {})
        dk = result.get("darakaraka", {})
        parts = []
        if isinstance(ak, dict) and ak.get("planet"):
            parts.append(f"Atmakaraka (soul): {ak['planet']}")
        if isinstance(dk, dict) and dk.get("planet"):
            parts.append(f"Darakaraka (spouse): {dk['planet']}")
        return "Jaimini: " + ", ".join(parts) if parts else ""

    # ─── Karakamsa ───
    if "karakamsa" in mn:
        purpose = result.get("purpose", result.get("indication", ""))
        return f"Karakamsa: {purpose}" if purpose else ""

    # ─── Manglik ───
    if "manglik" in mn:
        is_m = result.get("is_manglik", False)
        cancelled = result.get("is_cancelled", False)
        text = f"Manglik: {'Yes' if is_m else 'No'}"
        if cancelled:
            text += f" (Cancelled: {result.get('cancellation_reason', 'natural')})"
        return text

    # ─── Transit Calendar ───
    if "transit_calendar" in mn:
        months = result.get("months", [])
        verdict = result.get("period_verdict", "")
        lines = []
        if verdict:
            lines.append(f"Transit forecast: {verdict}")
        for m in months[:3]:
            if isinstance(m, dict):
                lines.append(f"  {m.get('short', '')}: {m.get('score', '')}/100 {m.get('theme', '')}")
        key_dates = result.get("key_dates", [])
        for kd in key_dates[:3]:
            if isinstance(kd, dict):
                fav = "favorable" if kd.get("favorable") else "challenging"
                lines.append(f"  {kd.get('date', '')}: {kd.get('event', '')} ({fav})")
        return "\n".join(lines)

    # ─── Medical Report ───
    if "medical" in mn:
        vulnerabilities = result.get("vulnerabilities", result.get("health_areas", []))
        longevity = result.get("longevity", "")
        parts = []
        if longevity:
            parts.append(f"Longevity: {longevity}")
        if isinstance(vulnerabilities, list):
            for v in vulnerabilities[:2]:
                if isinstance(v, dict):
                    parts.append(v.get("area", v.get("description", "")))
                else:
                    parts.append(str(v))
        return "Health: " + ". ".join(parts) if parts else ""

    # ─── Chakra ───
    if "chakra" in mn:
        chakras = result.get("blocked_chakras", result.get("chakras", []))
        blocked = []
        if isinstance(chakras, list):
            for ch in chakras:
                if isinstance(ch, dict):
                    status = ch.get("status", "")
                    if "blocked" in str(status).lower() or "weak" in str(status).lower():
                        blocked.append(f"{ch.get('name', '')}: {status}")
        return "Chakras blocked: " + ", ".join(blocked) if blocked else ""

    # ─── Remedies ───
    if "remedies" in mn or "gemstone" in mn:
        if isinstance(result, list):
            # Gemstone list
            gems = []
            for g in result[:3]:
                if isinstance(g, dict):
                    gems.append(f"{g.get('gemstone', '')} for {g.get('planet', '')} ({g.get('reason', '')[:60]})")
            return "Gemstones: " + " | ".join(gems) if gems else ""
        elif isinstance(result, dict):
            gems = result.get("gemstones", [])
            mantras = result.get("mantras", [])
            parts = []
            if isinstance(gems, list) and gems:
                for g in gems[:2]:
                    if isinstance(g, dict):
                        parts.append(f"Gem: {g.get('gemstone', '')} for {g.get('planet', '')}")
            if isinstance(mantras, list) and mantras:
                for m in mantras[:2]:
                    if isinstance(m, dict):
                        parts.append(f"Mantra: {m.get('mantra', '')} for {m.get('planet', '')}")
            return "Remedies: " + " | ".join(parts) if parts else ""
        return ""

    # ─── Nadi Reading ───
    if "nadi" in mn:
        predictions = result.get("predictions", result.get("readings", []))
        if isinstance(predictions, list) and predictions:
            texts = []
            for p in predictions[:2]:
                if isinstance(p, dict):
                    texts.append(p.get("prediction", p.get("text", ""))[:80])
                else:
                    texts.append(str(p)[:80])
            return "Nadi: " + " | ".join(texts)
        return ""

    # ─── Personality ───
    if "personality" in mn:
        archetype = result.get("archetype", result.get("personality_type", ""))
        return f"Personality: {archetype}" if archetype else ""

    # ─── Sannyasa Yogas ───
    if "sannyasa" in mn:
        yogas = result.get("yogas", [])
        return f"Sannyasa yogas: {len(yogas)} found" if yogas else "No sannyasa yogas"

    # ─── Muhurta ───
    if "muhurta" in mn and "find" in mn:
        dates = result.get("dates", result.get("auspicious_dates", []))
        if isinstance(dates, list) and dates:
            top = dates[0]
            if isinstance(top, dict):
                return f"Best muhurta: {top.get('date', '')} ({top.get('quality', top.get('score', ''))})"
            return f"Best muhurta: {top}"
        return ""

    # ─── Time Queries ───
    if "query_time" in mn or "query_month" in mn or "analyze_hour" in mn:
        score = result.get("score", "")
        themes = result.get("themes", [])
        overall = result.get("overall", "")
        dasha = result.get("dasha", {})
        dasha_str = dasha.get("dasha_string", "") if isinstance(dasha, dict) else ""
        parts = []
        if overall:
            parts.append(f"Overall: {overall}")
        if score:
            parts.append(f"Score: {score}/100")
        if dasha_str:
            parts.append(f"Dasha: {dasha_str}")
        if themes:
            parts.append(f"Themes: {', '.join(themes[:3])}")
        return " | ".join(parts) if parts else ""

    # ─── Realtime Dashboard ───
    if "dashboard" in mn or "realtime" in mn:
        hora = result.get("current_hora", "")
        chog = result.get("choghadiya", {})
        advice = result.get("quick_advice", "")
        parts = []
        if hora:
            parts.append(f"Hora: {hora}")
        if isinstance(chog, dict) and chog.get("name"):
            parts.append(f"Choghadiya: {chog['name']} ({chog.get('nature', '')})")
        if advice:
            parts.append(f"Advice: {advice[:80]}")
        return " | ".join(parts) if parts else ""

    # ─── Weekly Forecast ───
    if "weekly" in mn:
        summary = result.get("summary", result.get("week_summary", ""))
        if summary:
            return f"Weekly: {str(summary)[:150]}"
        return ""

    # ─── Varshaphal / Annual ───
    if "varshaphal" in mn or "annual" in mn:
        overall = result.get("overall", {})
        if isinstance(overall, dict):
            rating = overall.get("rating", "")
            score = overall.get("score", "")
            summary = overall.get("summary", "")
            return f"Annual {result.get('year', '')}: {rating} ({score}/100). {summary[:80]}"
        return ""

    # ─── Tithi Pravesh ───
    if "tithi_pravesh" in mn:
        analysis = result.get("analysis", {})
        cv = result.get("cross_validation", {})
        if isinstance(analysis, dict):
            rating = analysis.get("overall_rating", "")
            score = analysis.get("score", "")
            conf = cv.get("confidence", "") if isinstance(cv, dict) else ""
            return f"Tithi Pravesh: {rating} year (score {score}). {conf}"
        return ""

    # ─── Past Event ───
    if "past_event" in mn or "explain" in mn:
        explanation = result.get("explanation", result.get("summary", ""))
        return f"Past event: {str(explanation)[:150]}" if explanation else ""

    # ─── Vedha ───
    if "vedha" in mn:
        obstructed = result.get("obstructed_count", 0)
        if obstructed:
            blocked = [r for r in result.get("vedha_results", []) if r.get("is_obstructed")]
            parts = [f"{b['planet']} H{b['transit_house']} blocked by {b['obstructing_planet']}" for b in blocked]
            return "Vedha: " + ", ".join(parts)
        return ""

    # ─── Eclipse ───
    if "eclipse" in mn:
        eclipses = result.get("eclipses", result.get("upcoming", []))
        if isinstance(eclipses, list) and eclipses:
            e = eclipses[0]
            if isinstance(e, dict):
                return f"Next eclipse: {e.get('date', '')} {e.get('type', '')} — {e.get('personal_impact', '')[:80]}"
        return ""

    # ─── Sade Sati ───
    if "sade_sati" in mn:
        active = result.get("is_sade_sati", False)
        phase = result.get("phase", "")
        return f"Sade Sati: {'ACTIVE (' + phase + ')' if active else 'Not active'}"

    # ─── Synastry ───
    if "synastry" in mn:
        score = result.get("score", result.get("overall_score", ""))
        verdict = result.get("verdict", result.get("compatibility", ""))
        return f"Synastry: {verdict} (score: {score})" if verdict else ""

    # ─── Numerology ───
    if "numerology" in mn or "personal_day" in mn:
        if "personal_day" in mn:
            return f"Personal day: {result.get('day', '')} | month: {result.get('month', '')} | year: {result.get('year', '')}"
        mulank = result.get("mulank", result.get("life_path", ""))
        bhagyank = result.get("bhagyank", result.get("destiny", ""))
        return f"Numerology: Mulank {mulank}, Bhagyank {bhagyank}" if mulank else ""

    # ─── Vastu ───
    if "vastu" in mn:
        direction = result.get("best_direction", result.get("lucky_direction", ""))
        return f"Vastu: Best direction {direction}" if direction else ""

    # ─── Lucky Numbers ───
    if "lucky" in mn:
        numbers = result.get("lucky_numbers", result.get("numbers", []))
        return f"Lucky numbers: {numbers}" if numbers else ""

    # ─── Baby Names ───
    if "baby" in mn:
        names = result.get("names", result.get("suggestions", []))
        if isinstance(names, list) and names:
            return f"Baby name letters: {', '.join(str(n) for n in names[:5])}"
        return ""

    # ─── Maraka ───
    if "maraka" in mn:
        planets_m = result.get("maraka_planets", [])
        return f"Maraka planets: {', '.join(str(p) for p in planets_m)}" if planets_m else ""

    # ─── Generic fallback ───
    summary = result.get("summary", result.get("verdict", result.get("description", "")))
    if summary and isinstance(summary, str) and len(summary) > 15:
        return f"{method_name}: {summary[:150]}"

    return ""


# ═══════════════════════════════════════════════════════════════
# BRIEFING ASSEMBLER
# ═══════════════════════════════════════════════════════════════

def _assemble_briefing(chart: str, prashna: str, verdicts: str, memory: str) -> str:
    """Combine all sections into a clean briefing."""
    parts = [chart]

    if prashna:
        parts.append("")
        parts.append(prashna)

    if verdicts:
        parts.append("")
        parts.append("SPECIFIC FINDINGS FOR THIS QUESTION:")
        parts.append(verdicts)

    if memory:
        parts.append("")
        parts.append(memory)

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

ORACLE_PERSONA = """You are a world-class Jyotish Oracle — ancient, precise, warm, alive to the human in front of you.

HOW TO READ THE CHART DATA:
- Each planet shows: Sign, House, Nakshatra, which houses it Rules, and Dignity
- Connect the planet to what it governs (Moon=emotions/mother/silver, Venus=love/marriage/luxury, Mercury=speech/intellect/business, Mars=courage/property/siblings, Jupiter=wisdom/children/luck, Saturn=discipline/career/karma, Sun=authority/father/self, Rahu=obsession/foreign/unconventional, Ketu=spirituality/detachment)
- Connect the house it RULES to the house it SITS in — that tells you WHERE that life area plays out
- If a lord sits in H12, that area leaks/dissolves. H1=comes to you. H10=through career. H6=through struggle.
- COMBUSTION means a planet is overshadowed by the Sun — its significations are weakened
- GANDANTA means a planet sits at a karmic junction — deep transformation in that area
- Read the PRASHNA verdict — this is the universe answering at this exact moment
- Use SPECIFIC FINDINGS to deepen your answer with computed verdicts

LANGUAGE RULES:
- Speak like a wise friend who KNOWS, not like an astrologer explaining methods
- Never use jargon (dasha, mahadasha, vargottama, etc.) unless the user asks about astrology
- Instead say: "the planet of love" not "Venus", "a period of discipline" not "Saturn mahadasha"
- When asked about astrology specifically, reveal fully with planet names and houses

RESPONSE RULES:
- 4-7 sentences, flowing, no bullet points
- Find the CONTRADICTION — where strength and weakness coexist
- Give SPECIFIC remedy targeting the blocked energy (day, color, practice, gemstone)
- End with ONE hook line that makes them want to ask more
- NEVER repeat observations from previous sessions (see PREVIOUS SESSIONS if present)
- Every response must be DIFFERENT from the last one"""


def _build_system_prompt(intent: Dict, briefing: str, user_message: str) -> str:
    """Build the complete system prompt."""
    language = intent.get("language", "english")
    emotion = intent.get("emotion", intent.get("emotional_tone", "neutral"))

    lang_note = ""
    if language and language.lower() not in ("english", "en"):
        lang_note = f"\nRespond in {language}. Hook also in {language}."

    emotion_notes = {
        "worried": "\nACKNOWLEDGE in one sentence, then read. Compassion first.",
        "anxious": "\nCut through anxiety. One clear direction.",
        "sad": "\nAcknowledge. Then show the path through.",
        "desperate": "\nImmediate warmth. One practical step.",
        "confused": "\nOne clear direction. No philosophy.",
        "curious": "\nSkip preamble. Start with most interesting finding.",
        "excited": "\nMatch energy. Warm and specific.",
    }
    emotion_note = emotion_notes.get(emotion, "")

    today = datetime.now().strftime("%B %d, %Y")

    return f"""{ORACLE_PERSONA}

TODAY: {today}{lang_note}{emotion_note}

{briefing}

Maximum 100 words. One flowing response. End with one specific hook line."""


def _build_no_chart_prompt(intent: Dict, user_message: str) -> str:
    """Prompt when no birth data is available."""
    return f"""{ORACLE_PERSONA}

No birth chart available. Respond based on general astrological principles.
If the question requires a birth chart, gently ask for birth details.

Maximum 80 words."""


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_prashna_category(intent: Dict) -> str:
    """Map intent to prashna category."""
    topic = intent.get("primary_intent", "general")
    mapping = {
        "marriage": "marriage", "love": "marriage", "relationship": "marriage",
        "career": "career", "job": "career", "business": "career",
        "wealth": "wealth", "money": "wealth", "investment": "wealth",
        "health": "health", "children": "children",
        "travel": "travel", "education": "education",
        "spiritual": "spirituality", "property": "property",
    }
    return mapping.get(topic, "general")


def _format_intent(intent: Dict) -> Dict:
    """Format intent for the return dict."""
    return {
        'primary': intent.get('primary_intent', 'general'),
        'secondary': intent.get('secondary_intents', []),
        'confidence': intent.get('confidence', 'medium'),
        'tone': intent.get('emotional_tone', 'warm'),
        'emotion': intent.get('emotion', 'neutral'),
        'language': intent.get('language', 'english'),
        'translated': intent.get('translated', ''),
        'classifier': intent.get('classifier', 'unknown'),
        'is_worried': intent.get('is_worried', False),
        'follow_up_suggestions': intent.get('follow_up_suggestions', []),
    }


# ═══════════════════════════════════════════════════════════════
# MEMORY STORAGE (called from public.py after response)
# ═══════════════════════════════════════════════════════════════

def store_oracle_memory(birth_data: Dict, user_message: str,
                         oracle_response: str, hook: str, intent: Dict):
    """Store memory after Oracle responds."""
    try:
        from .user_memory import store_user_memory
        store_user_memory(birth_data, user_message, oracle_response, hook, intent)
    except Exception:
        pass


def get_oracle_stats() -> Dict:
    """Return cache stats."""
    from .engine_cache import get_cache_stats
    return {'cache': get_cache_stats()}
