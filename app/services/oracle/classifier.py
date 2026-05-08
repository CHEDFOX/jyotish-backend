"""
CLASSIFIER v2 — Simplified
One LLM call: understand the question + pick relevant data sections.
No method catalog. No rules. The LLM already knows astrology.

Cost: ~$0.0001 per call (prompt is tiny now)
"""

import json
import httpx
from typing import Dict, List


# ═══════════════════════════════════════════════════════════════
# SECTION CATALOGS (per system)
# ═══════════════════════════════════════════════════════════════

BPHS_SECTIONS = """dashas_full, transits, yogas, navamsa, dasamsa,
house_detail:N, jaimini, afflictions, medical,
remedies, classical_rules, personality, nadi,
compatibility, annual, prashna,
ashtakavarga, shadbala, divisional_charts, bhava_chalit,
alt_dashas, transit_deep, career_aptitude, numerology,
vastu, chakra, muhurta, planetary_returns,
weekly_forecast, daily_snapshot, past_events, life_timeline,
relocation, baby_names, sudarshana, nakshatra_profile,
yoga_timing, lucky, bphs_advanced, spiritual,
maraka, argala, tithi_pravesh, chart_promise,
period_query, manglik, pratyantar, timing_windows,
arudha_padas, av_transits, future_transits, transit_aspects,
name_numerology, hora, panchanga, dasha_sandhi,
rashi_drishti, av_sodhana, prastara_av, shodhya_pinda,
bhava_strengths, ishta_kashta, gemstones, synastry,
composite, location, raja_yogas, dhana_yogas,
daridra_yogas, female_horoscopy, longevity,
dasha_psychology, dasha_interpretation, special_lagnas,
jaimini_complete, upapada, muhurta_rules,
d60_past_life, remaining_vargas, mrityu_bhaga,
bhrigu_bindu, pada_archetypes, pancha_pakshi, graha_shanti"""

KP_SECTIONS = """cusps, significators, event_promise, ruling_planets,
dba_timing, transit_triggers, horary, fortuna,
fruitfulness, untenanted, medical, stellar_theory, four_level,
sensitive_points, kp_profession, cuspal_interlinks,
lost_object, rp_timing"""

WESTERN_SECTIONS = """aspects, configurations, progressions, solar_return,
lunar_return, solar_arc, lilith, fortune, fixed_stars,
void_moon, element_balance, composite, synastry, retrogrades,
profections, sect, arabic_parts, zodiacal_releasing,
antiscia, midpoints, harmonics, western_horary, mutual_receptions,
full_dignities, almuten, hayz, planetary_joys,
asteroids, planetary_nodes, prenatal, decennials,
tertiary, converse, prog_lunation, electional"""

CHINESE_SECTIONS = """four_pillars, day_master, elements, ten_gods,
branch_interactions, stem_interactions, symbolic_stars,
luck_periods, annual_luck, compatibility, empty_branches,
na_yin, life_stages, yong_shen, extended_stars, fan_fu_yin,
dayun_onset, xiao_yun, pillar_overlay, hidden_strength,
gods_matrix, date_selection, feng_shui, chinese_medical, zi_wei"""


MANDALA_SECTIONS = """power_map, best_cities, here_now, compass,
relocation, travel_windows, local_space, geodetic_zodiac,
parans, sacred_sites, eclipse_geography, migration_roadmap,
time_place_score, danger_zones, relationship_geography, active_direction,
location_weather, country_year, personal_mundane, coordinate_mundane, globe_scan"""

SYSTEM_CATALOGS = {
    'bphs': BPHS_SECTIONS,
    'kp': KP_SECTIONS,
    'western': WESTERN_SECTIONS,
    'chinese': CHINESE_SECTIONS,
    'mandala': MANDALA_SECTIONS,
}


def build_classifier_prompt(system: str = "bphs") -> str:
    """Build the classifier prompt for a given system."""
    sections = SYSTEM_CATALOGS.get(system, BPHS_SECTIONS)
    return f"""You classify astrology questions. Return JSON with:
- topic: primary topic
- question_type: timing / yes_no / why / how_is / what_kind / should_i / general
- emotional_tone: curious / worried / anxious / sad / desperate / excited / neutral
- language: english / hindi / hinglish / other
- sections: pick 3-6 relevant data sections from the list

AVAILABLE SECTIONS:
{sections}

Return ONLY valid JSON."""


def classify(question: str, api_key: str, model: str,
             system: str = "bphs", conversation_history: list = None) -> Dict:
    """
    Classify a question and pick relevant data sections.
    Returns: topic, question_type, emotional_tone, language, sections[]
    """
    if not api_key or not model:
        return _fallback(question, system)

    try:
        prompt = build_classifier_prompt(system)
        messages = [{"role": "system", "content": prompt}]

        # Add last 2 exchanges for context
        if conversation_history:
            for msg in conversation_history[-4:]:
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if content and len(content) < 300:
                    messages.append({"role": "user", "content": content})

        messages.append({"role": "user", "content": question})

        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=15.0,
        )

        if response.status_code != 200:
            return _fallback(question, system)

        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()

        result = json.loads(text)

        if not isinstance(result, dict) or "sections" not in result:
            return _fallback(question, system)

        # Ensure defaults
        result.setdefault("topic", "general")
        result.setdefault("question_type", "general")
        result.setdefault("emotional_tone", "neutral")
        result.setdefault("language", "english")

        # Validate sections are strings
        if not isinstance(result["sections"], list) or len(result["sections"]) < 1:
            return _fallback(question, system)

        return result

    except Exception as e:
        print(f"[Classifier] Error: {e}")
        return _fallback(question, system)


def _fallback(question: str, system: str = "bphs") -> Dict:
    """Keyword-based fallback when LLM classifier fails."""
    q = question.lower()
    topic = "general"
    question_type = "general"
    tone = "neutral"
    language = "english"

    # Detect language
    if any(ord(c) > 2304 and ord(c) < 2432 for c in question):
        language = "hindi"

    # Detect tone
    if any(w in q for w in ["worried", "scared", "fear", "darr", "chinta"]):
        tone = "worried"
    elif any(w in q for w in ["when", "kab", "timing"]):
        question_type = "timing"
    elif any(w in q for w in ["should i", "kya"]):
        question_type = "should_i"
    elif any(w in q for w in ["why", "kyon"]):
        question_type = "why"

    # Detect topic and assign sections per system
    if system == "bphs":
        sections = _bphs_fallback(q)
    elif system == "kp":
        sections = _kp_fallback(q)
    elif system == "western":
        sections = _western_fallback(q)
    elif system == "chinese":
        sections = _chinese_fallback(q)
    elif system == "mandala":
        sections = _mandala_fallback(q)
    else:
        sections = ["dashas_full", "transits", "personality"]

    # Detect topic from keywords
    if any(w in q for w in ["marry", "marriage", "shaadi", "spouse"]):
        topic = "marriage"
    elif any(w in q for w in ["career", "job", "work", "naukri"]):
        topic = "career"
    elif any(w in q for w in ["money", "wealth", "dhan", "invest"]):
        topic = "wealth"
    elif any(w in q for w in ["health", "disease", "sick"]):
        topic = "health"

    return {
        "topic": topic,
        "question_type": question_type,
        "emotional_tone": tone,
        "language": language,
        "sections": sections,
    }


def _bphs_fallback(q: str) -> list:
    if any(w in q for w in ["marry", "marriage", "shaadi", "spouse", "wife", "husband"]):
        return ["dashas_full", "navamsa", "jaimini", "transits", "classical_rules"]
    elif any(w in q for w in ["career", "job", "work", "naukri", "profession"]):
        return ["dashas_full", "dasamsa", "transits", "yogas"]
    elif any(w in q for w in ["money", "wealth", "rich", "dhan", "paisa", "invest"]):
        return ["dashas_full", "transits", "classical_rules", "yogas"]
    elif any(w in q for w in ["health", "disease", "sick", "tabiyat"]):
        return ["medical", "afflictions", "dashas_full", "transits"]
    elif any(w in q for w in ["remedy", "upay", "gemstone", "mantra"]):
        return ["remedies", "afflictions", "transits"]
    elif any(w in q for w in ["today", "aaj", "current", "right now"]):
        return ["transits", "dashas_full", "prashna"]
    elif any(w in q for w in ["yoga", "yogas"]):
        return ["yogas", "dashas_full", "transits"]
    elif any(w in q for w in ["dasha", "period", "phase"]):
        return ["dashas_full", "transits", "yogas"]
    return ["personality", "dashas_full", "transits", "yogas"]


def _kp_fallback(q: str) -> list:
    if any(w in q for w in ["marry", "marriage"]):
        return ["event_promise", "dba_timing", "transit_triggers", "cusps"]
    elif any(w in q for w in ["career", "job"]):
        return ["event_promise", "dba_timing", "significators", "transit_triggers"]
    return ["cusps", "significators", "ruling_planets", "dba_timing"]


def _western_fallback(q: str) -> list:
    if any(w in q for w in ["marry", "relationship", "partner", "love"]):
        return ["aspects", "synastry", "progressions", "solar_return"]
    elif any(w in q for w in ["career", "job", "work"]):
        return ["aspects", "configurations", "progressions", "solar_return"]
    return ["aspects", "element_balance", "configurations", "progressions"]




def _mandala_fallback(q: str) -> list:
    if any(w in q for w in ["love", "partner", "marriage", "relationship", "soulmate"]):
        return ["relationship_geography", "best_cities", "parans"]
    elif any(w in q for w in ["danger", "avoid", "risky", "unsafe"]):
        return ["danger_zones", "best_cities", "relocation"]
    elif any(w in q for w in ["temple", "pray", "pilgrimage", "spiritual", "sacred", "tirth"]):
        return ["sacred_sites", "compass", "geodetic_zodiac"]

    elif any(w in q for w in ["migrate", "migration", "life plan", "when to move", "dasha", "phase"]):
        return ["migration_roadmap", "best_cities", "travel_windows"]
    elif any(w in q for w in ["state", "rajasthan", "maharashtra", "gujarat", "karnataka", "tamil", "kerala", "punjab", "bengal", "bihar"]):
        return ["country_year", "location_weather", "coordinate_mundane"]
    elif any(w in q for w in ["country", "nation", "india", "usa", "america", "uk", "china", "japan", "how will", "forecast", "2025", "2026", "2027"]):
        return ["country_year", "location_weather", "personal_mundane"]
    elif any(w in q for w in ["best city", "best", "city", "where should", "move", "relocate", "settle"]):
        return ["best_cities", "relocation", "compass", "travel_windows"]
    elif any(w in q for w in ["travel", "trip", "yatra", "journey"]):
        return ["travel_windows", "compass", "best_cities"]
    elif any(w in q for w in ["direction", "facing", "vastu", "compass"]):
        return ["compass", "here_now", "local_space"]
    elif any(w in q for w in ["here", "current", "this place", "location"]):
        return ["here_now", "coordinate_mundane", "compass"]


    elif any(w in q for w in ["eclipse", "grahan"]):
        return ["eclipse_geography", "power_map"]

    elif any(w in q for w in ["paran", "latitude", "band"]):
        return ["parans", "power_map"]
    elif any(w in q for w in ["map", "globe", "world", "scan", "planet"]):
        return ["globe_scan", "power_map", "geodetic_zodiac"]
    elif any(w in q for w in ["stock", "market", "bse", "nse", "nyse", "exchange", "bitcoin", "crypto"]):
        return ["country_year", "location_weather"]
    elif any(w in q for w in ["nato", "un", "united nations", "brics", "opec", "who", "imf"]):
        return ["country_year", "location_weather"]

    return ["power_map", "best_cities", "compass", "local_space", "geodetic_zodiac"]

def _chinese_fallback(q: str) -> list:
    if any(w in q for w in ["marry", "relationship", "partner"]):
        return ["four_pillars", "day_master", "branch_interactions", "compatibility", "symbolic_stars"]
    elif any(w in q for w in ["career", "job", "work"]):
        return ["four_pillars", "ten_gods", "luck_periods", "annual_luck"]
    return ["four_pillars", "day_master", "elements", "symbolic_stars", "branch_interactions"]
