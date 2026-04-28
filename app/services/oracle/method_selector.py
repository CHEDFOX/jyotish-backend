"""
MERGED CLASSIFIER-SELECTOR
One LLM call that:
  1. Understands the question (topic, time_scope, question_type, entities)
  2. Picks the right 4-8 methods

Replaces both the old intent_classifier AND the old method_selector.
Cost: ~$0.0002 per call
"""

import json
import httpx
from typing import List, Dict


METHOD_CATALOG = """AVAILABLE METHODS (pick 4-8):

VERDICTS:
1. get_chart_promise(topic) — Lifetime YES/NO. Topics: marriage,career,wealth,children,health,spiritual,foreign,property,education,love,business
2. kp_event_analysis(topic) — KP precision verdict. Topics: marriage,career,children,wealth
3. get_classical_analysis(topic) — BPHS rules. Topics: marriage,career,wealth,health,spiritual,foreign,property,mother,father,siblings,love

TIMING:
4. predict_event(topic) — Timing windows. Topics: marriage,career,wealth,travel,property,children,business
5. get_transit_calendar(months) — Monthly scores. months: 3 or 6
6. get_pratyantar_dasha — Week-level timing
7. find_muhurta(event,days) — Best dates. Events: marriage,business,travel,education,property. days: 30 or 90
8. get_weekly_forecast — 7-day forecast
9. get_vimshottari_periods — Full lifetime dasha timeline (USE FOR PAST+FUTURE TIMING)

ANALYSIS:
10. get_navamsa_analysis — D9: marriage quality, spouse nature
11. get_career_analysis — D10: career field
12. get_jaimini_karakas — Atmakaraka, Darakaraka
13. get_kp_complete — Full KP with cusps
14. get_personality — Full personality profile
15. get_nakshatra_profile — Nakshatra detailed profile
16. get_career_aptitude — Career aptitude across 14 fields
17. get_nadi_reading — Supernaturally specific predictions

CURRENT STATUS:
18. get_current_transits — Transit effects now
19. get_transit_deep — Deep transit with sade sati, retrogrades
20. get_vedha — Vedha obstruction on transits
21. get_realtime_dashboard — Complete snapshot now
22. query_time(date) — Specific date analysis. Format: YYYY-MM-DD

HEALTH:
23. get_medical_report — Health vulnerabilities
24. get_chakra_analysis — Blocked energy centers
25. get_maraka — Death-inflicting analysis

COMPATIBILITY:
26. check_manglik — Manglik dosha
27. get_synastry — Two-chart compatibility (needs partner)

REMEDIES:
28. get_remedies — Complete remedies
29. get_gemstone_recommendations — Gemstones to wear/avoid
30. get_dynamic_remedies — Transit-aware remedies

SPIRITUAL:
31. get_sannyasa_yogas — Renunciation yogas
32. get_karakamsa — Soul purpose

ANNUAL:
33. get_varshaphal(year) — Annual horoscope
34. get_tithi_pravesh(year) — Tithi solar return

SPECIAL:
35. explain_past_event(date,type,desc) — Why past event happened
36. get_numerology(name) — Name/birth numerology
37. get_vastu — Lucky directions
38. get_lucky_numbers — Lucky numbers
39. cast_prashna_refined(category) — Prashna yes/no verdict
40. get_baby_names — Baby name suggestions"""


CLASSIFIER_SELECTOR_PROMPT = """You are an intent classifier AND method selector for a Vedic astrology system.

Given a user's question, output a JSON object with:
1. topic: primary topic (marriage, career, wealth, health, children, travel, spiritual, property, education, legal, business, expression, family, purpose, timing, gemstone, remedy, daily, investment, relocation, dreams, compatibility, general)
2. time_scope: past / present / future / past_and_future / all_time
3. question_type: yes_no / timing / how_is / why / should_i / what_kind / comparison / status_check / general
4. about_whom: self / spouse / child / parent / sibling / partner / other
5. entities: list of specific things mentioned (silver, Dubai, restaurant, mother, Tuesday, etc.)
6. emotional_tone: curious / worried / anxious / sad / desperate / confused / excited / neutral
7. language: english / hindi / hinglish
8. methods: array of 4-8 method strings from the catalog

RULES:
- If question mentions PAST events or "ever had", include get_vimshottari_periods
- If question is about a specific DATE, include query_time:YYYY-MM-DD
- If question is timing-related, include at least 2 timing methods
- If question is yes/no, include a verdict method
- If question mentions gemstones/remedies, include get_gemstone_recommendations or get_remedies
- If question is about spouse nature, include get_navamsa_analysis and get_jaimini_karakas
- If question mentions investment/commodity, include get_chart_promise:wealth
- Maximum 8 methods, minimum 3

Return ONLY valid JSON, no other text.

CATALOG:
"""


def classify_and_select(question: str, api_key: str, model: str = "openai/gpt-5.4-mini",
                         conversation_history: list = None) -> Dict:
    """
    One LLM call: classify intent + select methods.
    Returns dict with topic, time_scope, question_type, methods, etc.
    """
    try:
        # Add conversation context if available
        messages = [
            {"role": "system", "content": CLASSIFIER_SELECTOR_PROMPT + METHOD_CATALOG},
        ]

        # Add last 2 exchanges for context
        if conversation_history:
            for msg in conversation_history[-4:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content and len(content) < 300:
                    messages.append({"role": role, "content": content})

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
                "max_tokens": 300,
                "temperature": 0.1,
            },
            timeout=15.0,
        )

        if response.status_code != 200:
            return _fallback(question)

        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        text = text.replace("```json", "").replace("```", "").strip()

        result = json.loads(text)

        # Validate required fields
        if not isinstance(result, dict):
            return _fallback(question)
        if "methods" not in result or not isinstance(result["methods"], list):
            return _fallback(question)
        if len(result["methods"]) < 2:
            return _fallback(question)

        # Ensure defaults
        result.setdefault("topic", "general")
        result.setdefault("time_scope", "present")
        result.setdefault("question_type", "general")
        result.setdefault("about_whom", "self")
        result.setdefault("entities", [])
        result.setdefault("emotional_tone", "neutral")
        result.setdefault("language", "english")

        return result

    except Exception as e:
        print(f"[ClassifierSelector] Error: {e}")
        return _fallback(question)


def _fallback(question: str) -> Dict:
    """Rule-based fallback if LLM fails."""
    q = question.lower()
    methods = ["get_current_transits"]
    topic = "general"
    time_scope = "present"
    question_type = "general"
    tone = "neutral"
    language = "english"

    # Detect Hindi
    if any(ord(c) > 2304 and ord(c) < 2432 for c in question):
        language = "hindi"

    # Time scope detection
    if any(w in q for w in ["ever had", "past", "history", "pehle", "pahle"]):
        time_scope = "past_and_future"
        methods.append("get_vimshottari_periods")
    if any(w in q for w in ["will", "future", "when", "kab", "hoga"]):
        time_scope = "future" if time_scope == "present" else "past_and_future"

    # Question type
    if any(w in q for w in ["should i", "kya", "is it"]):
        question_type = "should_i"
    elif any(w in q for w in ["when", "kab", "timing", "window"]):
        question_type = "timing"
    elif any(w in q for w in ["why", "kyon", "reason"]):
        question_type = "why"
    elif any(w in q for w in ["how is", "kaisa", "kaise"]):
        question_type = "how_is"

    # Emotional tone
    if any(w in q for w in ["worried", "scared", "fear", "darr", "chinta"]):
        tone = "worried"
    elif any(w in q for w in ["sad", "low", "depressed", "udas"]):
        tone = "sad"

    # Topic detection
    if any(w in q for w in ["marry", "marriage", "shaadi", "spouse", "wife", "husband", "partner", "wedding", "vivah"]):
        topic = "marriage"
        methods.extend(["get_chart_promise:marriage", "kp_event_analysis:marriage",
                        "get_classical_analysis:marriage", "get_navamsa_analysis"])
    elif any(w in q for w in ["career", "job", "work", "profession", "business", "naukri", "kaam"]):
        topic = "career"
        methods.extend(["get_chart_promise:career", "kp_event_analysis:career",
                        "get_career_analysis", "get_career_aptitude"])
    elif any(w in q for w in ["money", "wealth", "rich", "financial", "income", "dhan", "paisa", "invest", "silver", "gold"]):
        topic = "wealth"
        methods.extend(["get_chart_promise:wealth", "get_classical_analysis:wealth", "predict_event:wealth"])
    elif any(w in q for w in ["health", "disease", "sick", "medical", "body", "tabiyat"]):
        topic = "health"
        methods.extend(["get_medical_report", "get_classical_analysis:health", "get_chakra_analysis"])
    elif any(w in q for w in ["child", "baby", "son", "daughter", "pregnant", "santan", "bachcha"]):
        topic = "children"
        methods.extend(["get_chart_promise:children", "kp_event_analysis:children"])
    elif any(w in q for w in ["gemstone", "stone", "ratna", "ring", "wear", "neelam", "pukhraj", "moonga"]):
        topic = "gemstone"
        methods.extend(["get_gemstone_recommendations", "get_remedies"])
    elif any(w in q for w in ["remedy", "upay", "mantra", "puja", "totka"]):
        topic = "remedy"
        methods.extend(["get_remedies", "get_dynamic_remedies", "get_dynamic_mantra"])
    elif any(w in q for w in ["today", "aaj", "this week", "current", "abhi"]):
        topic = "daily"
        methods.extend(["get_realtime_dashboard", "get_weekly_forecast"])
    elif any(w in q for w in ["spiritual", "meditation", "moksha", "adhyatmik"]):
        topic = "spiritual"
        methods.extend(["get_sannyasa_yogas", "get_karakamsa", "get_nadi_reading"])
    elif any(w in q for w in ["express", "speak", "voice", "bolna", "awaaz"]):
        topic = "expression"
        methods.extend(["get_personality", "get_nakshatra_profile"])
    else:
        methods.extend(["get_personality", "get_jaimini_karakas", "get_nadi_reading"])

    return {
        "topic": topic,
        "time_scope": time_scope,
        "question_type": question_type,
        "about_whom": "self",
        "entities": [],
        "emotional_tone": tone,
        "language": language,
        "methods": methods[:8],
    }
