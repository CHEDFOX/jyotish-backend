"""
CONSULTATION ENGINE
The brain between the intent classifier and the LLM.

Works like a real Jyotishi:
1. Read the chart's constitution first (who is this person)
2. Cast Prashna for the question moment (what does the universe say NOW)
3. Route to the right subsystems for this topic
4. Cross-validate verdicts across systems
5. Rank findings by relevance × specificity × surprise
6. Output a structured briefing where the LLM cannot miss the lead

Every subsystem serves at maximum. Nothing is wasted.
"""

from datetime import datetime
from typing import Dict, List, Tuple, Optional
import traceback


# ═══════════════════════════════════════════════════════════════
# CONSULTATION MAP — which subsystems to fire for each topic
# ═══════════════════════════════════════════════════════════════

CONSULTATION_MAP = {
    "marriage": {
        "houses": [7, 2, 11, 12],
        "karakas": ["Venus", "Jupiter"],
        "verdicts": [
            ("get_chart_promise", "marriage"),
            ("kp_event_analysis", "marriage"),
            ("get_classical_analysis", "marriage"),
        ],
        "deep": [
            "get_navamsa_analysis",
            "check_manglik",
            "get_jaimini_karakas",
        ],
        "timing": [
            ("predict_event", "marriage"),
            "get_chara_dasha",
            ("get_transit_calendar", 6),
            "get_pratyantar_dasha",
        ],
        "weather": ["get_current_transits", "get_vedha", "get_ashtakavarga_transits"],
        "planet_focus": ["Venus", "Jupiter", "Moon"],
        "prashna_category": "marriage",
    },
    "love": {
        "houses": [5, 7, 11],
        "karakas": ["Venus", "Moon"],
        "verdicts": [
            ("get_chart_promise", "love"),
            ("kp_event_analysis", "marriage"),
        ],
        "deep": [
            "get_navamsa_analysis",
            "get_jaimini_karakas",
            "get_personality",
        ],
        "timing": [
            ("predict_event", "marriage"),
            ("get_transit_calendar", 3),
        ],
        "weather": ["get_current_transits", "get_vedha"],
        "planet_focus": ["Venus", "Moon", "Rahu"],
        "prashna_category": "marriage",
    },
    "career": {
        "houses": [10, 6, 2, 11],
        "karakas": ["Saturn", "Sun", "Mercury"],
        "verdicts": [
            ("get_chart_promise", "career"),
            ("kp_event_analysis", "career"),
            ("get_classical_analysis", "career"),
        ],
        "deep": [
            "get_career_analysis",
            "get_career_aptitude",
            "get_jaimini_karakas",
        ],
        "timing": [
            ("predict_event", "career"),
            "get_chara_dasha",
            ("get_transit_calendar", 6),
        ],
        "weather": ["get_current_transits", "get_vedha", "get_ashtakavarga_transits"],
        "planet_focus": ["Saturn", "Sun", "Mercury", "Jupiter"],
        "prashna_category": "career",
    },
    "wealth": {
        "houses": [2, 11, 5, 9],
        "karakas": ["Jupiter", "Venus"],
        "verdicts": [
            ("get_chart_promise", "wealth"),
            ("kp_event_analysis", "wealth"),
            ("get_classical_analysis", "wealth"),
        ],
        "deep": [
            "get_jaimini_karakas",
            "get_nadi_reading",
        ],
        "timing": [
            ("predict_event", "wealth"),
            ("get_transit_calendar", 6),
        ],
        "weather": ["get_current_transits", "get_ashtakavarga_transits"],
        "planet_focus": ["Jupiter", "Venus", "Mercury"],
        "prashna_category": "wealth",
    },
    "health": {
        "houses": [1, 6, 8],
        "karakas": ["Sun", "Moon"],
        "verdicts": [
            ("get_chart_promise", "health"),
            ("get_classical_analysis", "health"),
        ],
        "deep": [
            "get_medical_report",
            "get_chakra_analysis",
        ],
        "timing": [
            ("get_transit_calendar", 3),
            "get_pratyantar_dasha",
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Sun", "Moon", "Mars", "Saturn"],
        "prashna_category": "health",
    },
    "children": {
        "houses": [5, 9, 2],
        "karakas": ["Jupiter"],
        "verdicts": [
            ("get_chart_promise", "children"),
            ("kp_event_analysis", "children"),
            ("get_classical_analysis", "children"),
        ],
        "deep": [
            "get_jaimini_karakas",
            ("get_divisional_chart", 7),
        ],
        "timing": [
            ("predict_event", "children"),
            ("get_transit_calendar", 6),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Jupiter", "Moon"],
        "prashna_category": "children",
    },
    "education": {
        "houses": [4, 5, 9],
        "karakas": ["Mercury", "Jupiter"],
        "verdicts": [
            ("get_chart_promise", "education"),
            ("get_classical_analysis", "education"),
        ],
        "deep": [
            ("get_divisional_chart", 24),
            "get_career_aptitude",
        ],
        "timing": [
            ("predict_event", "education"),
            ("get_transit_calendar", 3),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Mercury", "Jupiter"],
        "prashna_category": "education",
    },
    "travel": {
        "houses": [3, 9, 12],
        "karakas": ["Rahu", "Moon"],
        "verdicts": [
            ("get_chart_promise", "foreign"),
            ("get_classical_analysis", "foreign"),
        ],
        "deep": [
            "get_jaimini_karakas",
        ],
        "timing": [
            ("predict_event", "travel"),
            ("get_transit_calendar", 6),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Rahu", "Moon", "Jupiter"],
        "prashna_category": "travel",
    },
    "spiritual": {
        "houses": [5, 9, 12],
        "karakas": ["Ketu", "Jupiter"],
        "verdicts": [
            ("get_chart_promise", "spiritual"),
            ("get_classical_analysis", "spiritual"),
        ],
        "deep": [
            "get_jaimini_karakas",
            "get_nadi_reading",
            "get_sannyasa_yogas",
            "get_chakra_analysis",
        ],
        "timing": [
            ("get_transit_calendar", 3),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Ketu", "Jupiter", "Moon"],
        "prashna_category": "spirituality",
    },
    "property": {
        "houses": [4, 2, 11],
        "karakas": ["Mars", "Venus"],
        "verdicts": [
            ("get_chart_promise", "property"),
            ("get_classical_analysis", "property"),
        ],
        "deep": [],
        "timing": [
            ("predict_event", "property"),
            ("get_transit_calendar", 6),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Mars", "Venus", "Saturn"],
        "prashna_category": "property",
    },
    "legal": {
        "houses": [6, 7, 9],
        "karakas": ["Jupiter", "Saturn"],
        "verdicts": [
            ("get_classical_analysis", "legal"),
        ],
        "deep": [],
        "timing": [
            ("get_transit_calendar", 3),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Jupiter", "Saturn", "Mars"],
        "prashna_category": "legal",
    },
    "business": {
        "houses": [7, 10, 11, 2],
        "karakas": ["Mercury", "Jupiter"],
        "verdicts": [
            ("get_chart_promise", "business"),
            ("kp_event_analysis", "career"),
        ],
        "deep": [
            "get_career_analysis",
            "get_career_aptitude",
        ],
        "timing": [
            ("predict_event", "career"),
            ("get_transit_calendar", 6),
        ],
        "weather": ["get_current_transits", "get_vedha"],
        "planet_focus": ["Mercury", "Jupiter", "Venus"],
        "prashna_category": "career",
    },
    "expression": {
        "houses": [2, 3, 5],
        "karakas": ["Mercury", "Moon"],
        "verdicts": [],
        "deep": [
            "get_personality",
            "get_nakshatra_profile",
        ],
        "timing": [
            ("get_transit_calendar", 3),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Mercury", "Moon", "Venus"],
        "prashna_category": "self",
    },
    "family": {
        "houses": [4, 2, 3, 9],
        "karakas": ["Moon", "Sun"],
        "verdicts": [
            ("get_classical_analysis", "mother"),
            ("get_classical_analysis", "father"),
        ],
        "deep": [
            "get_jaimini_karakas",
        ],
        "timing": [
            ("get_transit_calendar", 3),
        ],
        "weather": ["get_current_transits"],
        "planet_focus": ["Moon", "Sun", "Jupiter"],
        "prashna_category": "home",
    },
    "purpose": {
        "houses": [1, 5, 9, 10],
        "karakas": ["Sun", "Jupiter"],
        "verdicts": [],
        "deep": [
            "get_personality",
            "get_jaimini_karakas",
            "get_nadi_reading",
            "get_career_aptitude",
            "get_nakshatra_profile",
        ],
        "timing": [],
        "weather": ["get_current_transits"],
        "planet_focus": ["Sun", "Jupiter", "Moon"],
        "prashna_category": "self",
    },
    "soul": {
        "houses": [1, 5, 9, 12],
        "karakas": ["Moon", "Ketu"],
        "verdicts": [],
        "deep": [
            "get_personality",
            "get_jaimini_karakas",
            "get_nadi_reading",
            "get_nakshatra_profile",
            "get_chakra_analysis",
            "get_sannyasa_yogas",
        ],
        "timing": [],
        "weather": [],
        "planet_focus": ["Moon", "Ketu", "Jupiter"],
        "prashna_category": "spirituality",
    },
    "timing": {
        "houses": [],
        "karakas": [],
        "verdicts": [],
        "deep": [],
        "timing": [
            "get_vimshottari_dasha",
            "get_chara_dasha",
            "get_yogini_dasha",
            ("get_transit_calendar", 6),
            "get_pratyantar_dasha",
            "get_weekly_forecast",
        ],
        "weather": ["get_current_transits", "get_vedha", "get_ashtakavarga_transits"],
        "planet_focus": [],
        "prashna_category": "general",
    },
    "difficulty": {
        "houses": [6, 8, 12],
        "karakas": ["Saturn", "Rahu"],
        "verdicts": [],
        "deep": [
            "get_medical_report",
            "get_chakra_analysis",
            "get_natal_retrogrades",
        ],
        "timing": [
            ("get_transit_calendar", 3),
            "get_pratyantar_dasha",
        ],
        "weather": ["get_current_transits", "get_vedha"],
        "planet_focus": ["Saturn", "Rahu", "Ketu", "Mars"],
        "prashna_category": "health",
    },
}

# Default for unmapped topics
DEFAULT_CONSULTATION = {
    "houses": [],
    "karakas": [],
    "verdicts": [
        ("get_chart_promise", None),
    ],
    "deep": [
        "get_jaimini_karakas",
        "get_personality",
    ],
    "timing": [
        "get_vimshottari_dasha",
        ("get_transit_calendar", 3),
    ],
    "weather": ["get_current_transits"],
    "planet_focus": [],
    "prashna_category": "general",
}


# ═══════════════════════════════════════════════════════════════
# CHART CONSTITUTION — who this person fundamentally IS
# Computed once per engine, cached
# ═══════════════════════════════════════════════════════════════

def _build_constitution(engine) -> Dict:
    """Chart-level findings that apply to EVERY question."""

    # Check if already cached
    if hasattr(engine, '_constitution') and engine._constitution:
        return engine._constitution

    constitution = {
        "combustion": [],
        "gandanta": [],
        "retrogrades": [],
        "manglik": {},
        "sade_sati": {},
        "pushkara": {},
        "graha_yuddha": {},
        "avasthas": {},
        "chart_strength": {},
        "nabhasa_yogas": {},
        "yogas_highlights": [],
        "key_yogas": [],
    }

    # Combustion
    try:
        from ..parashara.combustion import analyze_combustion
        constitution["combustion"] = analyze_combustion(engine.planets)
    except Exception:
        pass

    # Gandanta
    try:
        from ..parashara.gandanta import analyze_gandanta
        constitution["gandanta"] = analyze_gandanta(engine.planets)
    except Exception:
        pass

    # Natal retrogrades
    try:
        r = engine.get_natal_retrogrades()
        retro_planets = []
        for planet, data in r.get("retrograde_planets", {}).items():
            if data.get("is_retrograde"):
                retro_planets.append({
                    "planet": planet,
                    "karma": data.get("past_life_karma", ""),
                    "gift": data.get("hidden_gift", ""),
                })
        constitution["retrogrades"] = retro_planets
    except Exception:
        pass

    # Manglik
    try:
        constitution["manglik"] = engine.check_manglik()
    except Exception:
        pass

    # Sade Sati
    try:
        constitution["sade_sati"] = engine.check_sade_sati()
    except Exception:
        pass

    # Pushkara
    try:
        constitution["pushkara"] = engine.get_pushkara()
    except Exception:
        pass

    # Graha Yuddha
    try:
        constitution["graha_yuddha"] = engine.get_graha_yuddha()
    except Exception:
        pass

    # Chart strength
    try:
        constitution["chart_strength"] = engine.get_chart_strength()
    except Exception:
        pass

    # Key yogas
    try:
        yogas = engine.get_yogas()
        constitution["yogas_highlights"] = yogas.get("highlights", [])[:5]
        constitution["key_yogas"] = [
            y.get("name", "") for y in yogas.get("highlights", [])[:5]
        ]
    except Exception:
        pass

    # Nabhasa yogas
    try:
        constitution["nabhasa_yogas"] = engine.get_nabhasa_yogas()
    except Exception:
        pass

    # Avasthas
    try:
        constitution["avasthas"] = engine.get_avasthas()
    except Exception:
        pass

    # Cache on engine
    engine._constitution = constitution
    return constitution


# ═══════════════════════════════════════════════════════════════
# PRASHNA — cast for the question moment
# ═══════════════════════════════════════════════════════════════

def _cast_prashna(engine, category: str) -> Dict:
    """Cast a Prashna chart for this exact moment at the user's location."""
    try:
        from ..prashna.prashna_refined import PrashnaRefined
        from ..jyotish_engine import JyotishEngine

        prashna_engine = JyotishEngine(datetime.now(), engine.latitude, engine.longitude)
        refined = PrashnaRefined(prashna_engine, category)
        return refined.refine()
    except Exception as e:
        return {"verdict": "Prashna unavailable", "confidence_pct": 0, "reasoning": [str(e)]}


# ═══════════════════════════════════════════════════════════════
# METHOD EXECUTOR — safely calls engine methods
# ═══════════════════════════════════════════════════════════════

def _safe_call(engine, method_spec) -> Tuple[str, Optional[Dict]]:
    """Call an engine method safely. Returns (method_name, result_or_None)."""
    try:
        if isinstance(method_spec, tuple):
            method_name = method_spec[0]
            args = method_spec[1:]
            method = getattr(engine, method_name, None)
            if method:
                result = method(*args)
                return (method_name, result)
        elif isinstance(method_spec, str):
            method = getattr(engine, method_spec, None)
            if method:
                result = method()
                return (method_spec, result)
    except Exception:
        pass
    return (str(method_spec), None)


# ═══════════════════════════════════════════════════════════════
# FINDING EXTRACTOR — pull discrete facts from method results
# ═══════════════════════════════════════════════════════════════

def _extract_findings(method_name: str, result: Dict, topic: str, planet_focus: list) -> List[Dict]:
    """Extract discrete, scorable findings from a method result."""
    findings = []
    if not result or not isinstance(result, dict):
        return findings

    # Chart promise verdict
    if "chart_promise" in method_name or "promise" in str(result.get("type", "")):
        verdict = result.get("verdict", result.get("summary", ""))
        score = result.get("score", result.get("promise_score", 50))
        supports = result.get("supports", result.get("supporting_count", 0))
        opposes = result.get("opposes", result.get("opposing_count", 0))
        if isinstance(supports, list):
            supports = len(supports)
        if isinstance(opposes, list):
            opposes = len(opposes)
        findings.append({
            "source": "chart_promise",
            "type": "verdict",
            "text": f"Chart Promise: {verdict} (score {score}/100, {supports} supports, {opposes} opposes)",
            "relevance": 9,
            "specificity": 7,
            "surprise": 3,
        })

    # KP verdict
    if "kp" in method_name.lower():
        verdict = result.get("verdict", result.get("kp_verdict", ""))
        promised = result.get("promised", result.get("is_promised", None))
        if promised is not None:
            word = "PROMISED" if promised else "NOT PROMISED"
            findings.append({
                "source": "kp_system",
                "type": "verdict",
                "text": f"KP System: {word}. {verdict}",
                "relevance": 9,
                "specificity": 8,
                "surprise": 4,
            })

    # Classical rules
    if "classical" in method_name:
        summary = result.get("summary", "")
        supports = result.get("supports", [])
        opposes = result.get("opposes", [])
        rules_fired = result.get("rules_fired", 0)
        if summary:
            findings.append({
                "source": "classical_texts",
                "type": "verdict",
                "text": f"Classical texts ({rules_fired} rules): {summary}",
                "relevance": 8,
                "specificity": 9,
                "surprise": 5,
            })
        # Individual rules as findings
        for rule in (supports[:3] if isinstance(supports, list) else []):
            text = rule.get("text", rule) if isinstance(rule, dict) else str(rule)
            findings.append({
                "source": "classical_rule",
                "type": "evidence",
                "text": text,
                "relevance": 7,
                "specificity": 9,
                "surprise": 6,
            })

    # Timing predictions
    if "predict_event" in method_name or "timing" in method_name:
        window = result.get("window", result.get("best_window", {}))
        if isinstance(window, dict) and window:
            start = window.get("start", window.get("from", ""))
            end = window.get("end", window.get("to", ""))
            if start:
                findings.append({
                    "source": "timing_engine",
                    "type": "timing",
                    "text": f"Primary timing window: {start} to {end}",
                    "relevance": 8,
                    "specificity": 7,
                    "surprise": 4,
                })
        # Additional windows
        windows = result.get("all_windows", result.get("windows", []))
        if isinstance(windows, list):
            for i, w in enumerate(windows[:3]):
                if isinstance(w, dict):
                    findings.append({
                        "source": "timing_engine",
                        "type": "timing",
                        "text": f"Window {i+1}: {w.get('start', w.get('period', ''))}" +
                                f" ({w.get('strength', w.get('quality', ''))})",
                        "relevance": 7 - i,
                        "specificity": 6,
                        "surprise": 3,
                    })

    # Dasha info
    if "dasha" in method_name.lower():
        maha = result.get("mahadasha", {})
        lord = maha.get("lord", "") if isinstance(maha, dict) else str(maha)
        antar = result.get("antardasha", {})
        sub = antar.get("lord", "") if isinstance(antar, dict) else str(antar)
        dasha_str = result.get("dasha_string", "")
        if dasha_str:
            findings.append({
                "source": method_name,
                "type": "timing",
                "text": f"Current dasha: {dasha_str}",
                "relevance": 7,
                "specificity": 5,
                "surprise": 2,
            })

    # Navamsa / D9 analysis
    if "navamsa" in method_name.lower():
        spouse_desc = result.get("spouse_description", result.get("partner_nature", ""))
        if spouse_desc:
            findings.append({
                "source": "navamsa_d9",
                "type": "evidence",
                "text": f"D9 Navamsa spouse indication: {spouse_desc}",
                "relevance": 8,
                "specificity": 8,
                "surprise": 6,
            })
        venus_nav = result.get("venus_navamsa", {})
        if venus_nav:
            findings.append({
                "source": "navamsa_d9",
                "type": "evidence",
                "text": f"Venus in Navamsa: {venus_nav.get('rashi', '')} — {venus_nav.get('interpretation', '')}",
                "relevance": 7,
                "specificity": 7,
                "surprise": 5,
            })

    # Career aptitude
    if "aptitude" in method_name:
        top_fields = result.get("top_fields", result.get("aptitude", []))
        if isinstance(top_fields, list) and top_fields:
            fields_str = ", ".join(
                f.get("field", str(f)) + " (" + str(f.get("score", "")) + "%)"
                if isinstance(f, dict) else str(f)
                for f in top_fields[:3]
            )
            findings.append({
                "source": "career_aptitude",
                "type": "evidence",
                "text": f"Career aptitude: {fields_str}",
                "relevance": 8 if topic == "career" else 4,
                "specificity": 8,
                "surprise": 5,
            })

    # Jaimini karakas
    if "karaka" in method_name.lower():
        atmakaraka = result.get("atmakaraka", {})
        if isinstance(atmakaraka, dict) and atmakaraka:
            ak_planet = atmakaraka.get("planet", "")
            findings.append({
                "source": "jaimini",
                "type": "evidence",
                "text": f"Atmakaraka (soul planet): {ak_planet} — defines your deepest purpose",
                "relevance": 7 if topic in ("soul", "purpose", "spiritual") else 4,
                "specificity": 8,
                "surprise": 6,
            })
        darakaraka = result.get("darakaraka", {})
        if isinstance(darakaraka, dict) and darakaraka:
            dk_planet = darakaraka.get("planet", "")
            findings.append({
                "source": "jaimini",
                "type": "evidence",
                "text": f"Darakaraka (spouse planet): {dk_planet} — defines partner nature",
                "relevance": 9 if topic in ("marriage", "love") else 3,
                "specificity": 9,
                "surprise": 7,
            })

    # Manglik
    if "manglik" in method_name.lower():
        is_manglik = result.get("is_manglik", False)
        cancelled = result.get("is_cancelled", False)
        findings.append({
            "source": "manglik",
            "type": "evidence",
            "text": f"Manglik: {'Yes' if is_manglik else 'No'}" +
                    (f" (CANCELLED — {result.get('cancellation_reason', 'natural cancellation')})" if cancelled else ""),
            "relevance": 9 if topic == "marriage" else 2,
            "specificity": 6,
            "surprise": 3 if not is_manglik else 5,
        })

    # Nadi reading
    if "nadi" in method_name.lower():
        predictions = result.get("predictions", result.get("readings", []))
        if isinstance(predictions, list):
            for pred in predictions[:2]:
                text = pred.get("prediction", pred.get("text", str(pred))) if isinstance(pred, dict) else str(pred)
                if len(text) > 20:
                    findings.append({
                        "source": "nadi",
                        "type": "evidence",
                        "text": f"Nadi: {text[:150]}",
                        "relevance": 6,
                        "specificity": 9,
                        "surprise": 8,
                    })

    # Personality
    if "personality" in method_name.lower():
        archetype = result.get("archetype", result.get("personality_type", ""))
        if archetype:
            findings.append({
                "source": "personality",
                "type": "evidence",
                "text": f"Personality archetype: {archetype}",
                "relevance": 5 if topic in ("soul", "purpose") else 3,
                "specificity": 6,
                "surprise": 4,
            })

    # Transit calendar
    if "transit_calendar" in method_name or "calendar" in method_name:
        months = result.get("months", [])
        for m in months[:3]:
            if isinstance(m, dict):
                findings.append({
                    "source": "transit_calendar",
                    "type": "timing",
                    "text": f"{m.get('short', '')}: score {m.get('score', '?')}/100 — {m.get('theme', '')}. Best: {m.get('best_for', '')}",
                    "relevance": 6,
                    "specificity": 7,
                    "surprise": 3,
                })
        key_dates = result.get("key_dates", [])
        for kd in key_dates[:3]:
            if isinstance(kd, dict):
                fav = "favorable" if kd.get("favorable") else "challenging"
                findings.append({
                    "source": "transit_calendar",
                    "type": "timing",
                    "text": f"Key date {kd.get('date', '')}: {kd.get('event', '')} (H{kd.get('house', '')} {kd.get('house_keyword', '')}, {fav})",
                    "relevance": 7,
                    "specificity": 8,
                    "surprise": 5,
                })

    # Vedha
    if "vedha" in method_name.lower():
        obstructed = result.get("obstructed_count", 0)
        if obstructed > 0:
            blocked = [r for r in result.get("vedha_results", []) if r.get("is_obstructed")]
            for b in blocked:
                findings.append({
                    "source": "vedha",
                    "type": "weather",
                    "text": f"Vedha: {b['planet']} favorable transit in H{b['transit_house']} BLOCKED by {b['obstructing_planet']}",
                    "relevance": 6,
                    "specificity": 8,
                    "surprise": 7,
                })

    # Medical
    if "medical" in method_name.lower():
        vulnerabilities = result.get("vulnerabilities", result.get("health_areas", []))
        if isinstance(vulnerabilities, list):
            for v in vulnerabilities[:2]:
                text = v.get("area", v.get("description", str(v))) if isinstance(v, dict) else str(v)
                findings.append({
                    "source": "medical_astrology",
                    "type": "evidence",
                    "text": f"Health: {text[:120]}",
                    "relevance": 8 if topic == "health" else 3,
                    "specificity": 7,
                    "surprise": 5,
                })

    # Chakra
    if "chakra" in method_name.lower():
        blocked = result.get("blocked_chakras", result.get("chakras", []))
        if isinstance(blocked, list):
            for ch in blocked[:2]:
                name = ch.get("name", str(ch)) if isinstance(ch, dict) else str(ch)
                status = ch.get("status", "") if isinstance(ch, dict) else ""
                if "blocked" in str(status).lower() or "weak" in str(status).lower():
                    findings.append({
                        "source": "chakra",
                        "type": "evidence",
                        "text": f"Chakra: {name} is {status}",
                        "relevance": 5,
                        "specificity": 6,
                        "surprise": 6,
                    })

    # Sannyasa yogas
    if "sannyasa" in method_name.lower():
        yogas_found = result.get("yogas", [])
        if yogas_found:
            findings.append({
                "source": "sannyasa",
                "type": "evidence",
                "text": f"Sannyasa (renunciation) yogas present: {len(yogas_found)} found",
                "relevance": 8 if topic == "spiritual" else 3,
                "specificity": 9,
                "surprise": 8,
            })

    # Current transits
    if "current_transit" in method_name.lower() or "transit_analysis" in method_name.lower():
        overall = result.get("overall_period", result.get("summary", ""))
        if isinstance(overall, dict):
            overall = overall.get("description", str(overall))
        if overall:
            findings.append({
                "source": "transits",
                "type": "weather",
                "text": f"Current transit period: {str(overall)[:120]}",
                "relevance": 6,
                "specificity": 5,
                "surprise": 2,
            })
        # Sade sati from transit result
        sade = result.get("sade_sati", {})
        if isinstance(sade, dict) and sade.get("is_sade_sati"):
            findings.append({
                "source": "transits",
                "type": "weather",
                "text": f"SADE SATI ACTIVE: {sade.get('phase', 'ongoing')}",
                "relevance": 8,
                "specificity": 7,
                "surprise": 4,
            })

    # Generic fallback for unhandled results
    if not findings and isinstance(result, dict):
        summary = result.get("summary", result.get("description", result.get("verdict", "")))
        if summary and isinstance(summary, str) and len(summary) > 15:
            findings.append({
                "source": method_name,
                "type": "evidence",
                "text": str(summary)[:150],
                "relevance": 4,
                "specificity": 4,
                "surprise": 3,
            })

    return findings


# ═══════════════════════════════════════════════════════════════
# CONSTITUTION FINDINGS — extract chart anomalies relevant to topic
# ═══════════════════════════════════════════════════════════════

def _constitution_findings(constitution: Dict, topic: str, planet_focus: list) -> List[Dict]:
    """Extract constitution-level findings relevant to the question."""
    findings = []

    # Combustion
    comb = constitution.get("combustion", {})
    if isinstance(comb, dict):
        for p in comb.get("combust_planets", []):
            planet = p.get("planet", "")
            # Relevance depends on whether this planet matters for this topic
            rel = 10 if planet in planet_focus else 5
            if planet == "Mercury":
                rel = max(rel, 7)  # Mercury combustion always matters somewhat
            findings.append({
                "source": "combustion",
                "type": "anomaly",
                "text": f"{planet} COMBUST ({p['severity']}, {p['distance_from_sun']}° from Sun): {p.get('effect', '')}",
                "relevance": rel,
                "specificity": 9,
                "surprise": 7,
            })

    # Gandanta
    gand = constitution.get("gandanta", {})
    if isinstance(gand, dict):
        for p in gand.get("gandanta_planets", []):
            planet = p.get("planet", "")
            rel = 9 if planet in planet_focus else 4
            if planet in ("Moon", "Ascendant"):
                rel = max(rel, 7)
            findings.append({
                "source": "gandanta",
                "type": "anomaly",
                "text": f"{planet} in GANDANTA ({p['gandanta_zone']}, {p['severity']}): {p.get('karmic_effect', '')[:100]}",
                "relevance": rel,
                "specificity": 9,
                "surprise": 8,
            })

    # Retrogrades
    for r in constitution.get("retrogrades", []):
        planet = r.get("planet", "")
        rel = 7 if planet in planet_focus else 3
        findings.append({
            "source": "natal_retrograde",
            "type": "anomaly",
            "text": f"{planet} RETROGRADE (natal): {r.get('karma', '')}",
            "relevance": rel,
            "specificity": 7,
            "surprise": 5,
        })

    # Sade Sati
    sade = constitution.get("sade_sati", {})
    if isinstance(sade, dict) and sade.get("is_sade_sati"):
        findings.append({
            "source": "sade_sati",
            "type": "anomaly",
            "text": f"SADE SATI active: {sade.get('phase', '')}. Saturn's 7.5 year test is running.",
            "relevance": 7,
            "specificity": 6,
            "surprise": 4,
        })

    # Key yogas (always mention top yoga)
    for yoga in constitution.get("yogas_highlights", [])[:2]:
        name = yoga.get("name", "") if isinstance(yoga, dict) else str(yoga)
        desc = yoga.get("description", "") if isinstance(yoga, dict) else ""
        if name:
            findings.append({
                "source": "yoga",
                "type": "evidence",
                "text": f"Yoga: {name}" + (f" — {desc[:80]}" if desc else ""),
                "relevance": 5,
                "specificity": 7,
                "surprise": 6,
            })

    # Chart strength
    cs = constitution.get("chart_strength", {})
    if isinstance(cs, dict):
        score = cs.get("score", cs.get("overall", 0))
        if score:
            findings.append({
                "source": "chart_strength",
                "type": "evidence",
                "text": f"Overall chart strength: {score}/100",
                "relevance": 3,
                "specificity": 4,
                "surprise": 2,
            })

    return findings


# ═══════════════════════════════════════════════════════════════
# FINDING RANKER — scores and sorts all findings
# ═══════════════════════════════════════════════════════════════

def _rank_findings(findings: List[Dict], user_memory_text: str = "") -> List[Dict]:
    """Score and rank findings. Memory penalty for already-told facts."""

    memory_lower = user_memory_text.lower() if user_memory_text else ""

    for f in findings:
        # Base score
        score = f["relevance"] * 2 + f["specificity"] * 1.5 + f["surprise"] * 1

        # Memory penalty — if this fact was already told
        if memory_lower:
            text_lower = f["text"].lower()
            # Check for key phrases that indicate repetition
            words = text_lower.split()
            overlap = sum(1 for w in words if len(w) > 4 and w in memory_lower)
            if overlap > 3:
                score -= 10  # Heavy penalty for repetition

        # Boost verdicts
        if f["type"] == "verdict":
            score += 5

        # Boost anomalies (unique to this chart)
        if f["type"] == "anomaly":
            score += 3

        f["final_score"] = round(score, 1)

    # Sort by final score descending
    findings.sort(key=lambda x: x["final_score"], reverse=True)
    return findings


# ═══════════════════════════════════════════════════════════════
# STRUCTURED BRIEFING BUILDER
# ═══════════════════════════════════════════════════════════════

def _build_structured_briefing(
    topic: str,
    ranked_findings: List[Dict],
    prashna_result: Dict,
    constitution: Dict,
    user_memory_text: str,
    engine=None,
) -> str:
    """Build the hierarchical briefing for the LLM."""

    lines = []

    # ─── LEAD FINDING ───
    if ranked_findings:
        lead = ranked_findings[0]
        lines.append("═══ LEAD WITH THIS (most important finding for this question) ═══")
        lines.append(lead["text"])
        lines.append(f"[Source: {lead['source']}, Score: {lead['final_score']}]")
        lines.append("")

    # ─── PRASHNA VERDICT (real-time) ───
    lines.append("═══ PRASHNA (universe's answer at this moment) ═══")
    lines.append(f"Verdict: {prashna_result.get('verdict', 'unavailable')}")
    lines.append(f"Confidence: {prashna_result.get('confidence_pct', 0)}%")
    lines.append(f"Timing indication: {prashna_result.get('timing', 'unclear')}")
    key_reasons = prashna_result.get("reasoning", [])[:3]
    if key_reasons:
        lines.append("Key factors: " + "; ".join(key_reasons))
    lines.append("")

    # ─── CROSS-SYSTEM VERDICTS ───
    verdicts = [f for f in ranked_findings if f["type"] == "verdict"]
    if verdicts:
        lines.append("═══ VERDICTS (what multiple systems say) ═══")
        for v in verdicts[:4]:
            lines.append(f"• {v['text']}")
        # Agreement check
        yes_count = sum(1 for v in verdicts if any(w in v["text"].upper() for w in ["PROMISED", "YES", "STRONG", "FAVORABLE"]))
        no_count = sum(1 for v in verdicts if any(w in v["text"].upper() for w in ["NOT PROMISED", "NO", "WEAK", "DENIED"]))
        if yes_count > no_count:
            lines.append(f"CONVERGENCE: {yes_count} systems support, {no_count} oppose — HIGH confidence")
        elif no_count > yes_count:
            lines.append(f"CONVERGENCE: {no_count} systems oppose, {yes_count} support — challenging")
        elif verdicts:
            lines.append("CONVERGENCE: Systems split — nuanced answer needed")
        lines.append("")

    # ─── KEY EVIDENCE (ranked) ───
    evidence = [f for f in ranked_findings if f["type"] == "evidence"][:6]
    if evidence:
        lines.append("═══ EVIDENCE (ranked by importance) ═══")
        for i, e in enumerate(evidence):
            lines.append(f"{i+1}. {e['text']}")
        lines.append("")

    # ─── TIMING (converged from multiple clocks) ───
    timing = [f for f in ranked_findings if f["type"] == "timing"]
    if timing:
        lines.append("═══ TIMING (from multiple systems) ═══")
        for t in timing[:5]:
            lines.append(f"• {t['text']}")
        lines.append("")

    # ─── CHART ANOMALIES (unique to this person) ───
    anomalies = [f for f in ranked_findings if f["type"] == "anomaly"]
    if anomalies:
        lines.append("═══ CHART ANOMALIES (unique to this person) ═══")
        for a in anomalies[:4]:
            lines.append(f"• {a['text']}")
        lines.append("")

    # ─── CURRENT WEATHER ───
    weather = [f for f in ranked_findings if f["type"] == "weather"]
    if weather:
        lines.append("═══ CURRENT PLANETARY WEATHER ═══")
        for w in weather[:3]:
            lines.append(f"• {w['text']}")
        lines.append("")

    # ─── REMEDY HINTS (for the LLM to expand on) ───
    # Identify the most blocked/afflicted planet relevant to the topic
    blocked_planets = []
    for a in anomalies:
        for planet in ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Moon", "Sun"]:
            if planet in a["text"] and ("combust" in a["text"].lower() or "gandanta" in a["text"].lower() or "retrograde" in a["text"].lower()):
                blocked_planets.append(planet)

    if blocked_planets:
        planet = blocked_planets[0]
        remedy_map = {
            "Sun": "Sunday, copper, wheat donation, Aditya Hridayam, ruby",
            "Moon": "Monday, white, water ritual, Chandra mantra, pearl, silver",
            "Mars": "Tuesday, red, Hanuman Chalisa, red coral, donate lentils",
            "Mercury": "Wednesday, green, Vishnu Sahasranama, emerald, green donation",
            "Jupiter": "Thursday, yellow, guru prayers, yellow sapphire, turmeric",
            "Venus": "Friday, white, Lakshmi prayers, diamond/white sapphire, ghee lamp",
            "Saturn": "Saturday, dark blue/black, Shani mantra, blue sapphire, sesame oil lamp",
        }
        remedy = remedy_map.get(planet, "")
        if remedy:
            lines.append(f"═══ REMEDY TARGET ═══")
            lines.append(f"Blocked energy: {planet}")
            lines.append(f"Remedy elements: {remedy}")
            lines.append("")

    # ─── DO NOT REPEAT ───
    if user_memory_text:
        lines.append("═══ DO NOT REPEAT (already told in previous sessions) ═══")
        lines.append(user_memory_text)
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — replaces assemble_data for chat
# ═══════════════════════════════════════════════════════════════

def consult(engine, intent: Dict, user_memory_text: str = "") -> Dict:
    """
    The Consultation Engine.
    Fires the right subsystems, cross-validates, ranks findings,
    and produces a structured briefing.
    """
    topic = intent.get("primary_intent", intent.get("primary", "general"))
    consultation = CONSULTATION_MAP.get(topic, DEFAULT_CONSULTATION)
    planet_focus = consultation.get("planet_focus", [])

    # ─── STAGE 1: Chart Constitution ───
    constitution = _build_constitution(engine)

    # ─── STAGE 2: Cast Prashna ───
    prashna_category = consultation.get("prashna_category", "general")
    prashna_result = _cast_prashna(engine, prashna_category)

    # ─── STAGE 3: Fire topic-specific methods ───
    all_findings = []
    methods_fired = []

    # Verdicts
    for spec in consultation.get("verdicts", []):
        name, result = _safe_call(engine, spec)
        methods_fired.append(name)
        if result:
            all_findings.extend(_extract_findings(name, result, topic, planet_focus))

    # Deep analysis
    for spec in consultation.get("deep", []):
        name, result = _safe_call(engine, spec)
        methods_fired.append(name)
        if result:
            all_findings.extend(_extract_findings(name, result, topic, planet_focus))

    # Timing
    for spec in consultation.get("timing", []):
        name, result = _safe_call(engine, spec)
        methods_fired.append(name)
        if result:
            all_findings.extend(_extract_findings(name, result, topic, planet_focus))

    # Current weather
    for spec in consultation.get("weather", []):
        name, result = _safe_call(engine, spec)
        methods_fired.append(name)
        if result:
            all_findings.extend(_extract_findings(name, result, topic, planet_focus))

    # ─── STAGE 4: Constitution findings ───
    const_findings = _constitution_findings(constitution, topic, planet_focus)
    all_findings.extend(const_findings)

    # ─── STAGE 5: Rank everything ───
    ranked = _rank_findings(all_findings, user_memory_text)

    # ─── STAGE 6: Build structured briefing ───
    briefing = _build_structured_briefing(
        topic, ranked, prashna_result, constitution, user_memory_text, engine
    )

    return {
        "oracle_briefing": briefing,
        "sections": [],  # legacy compatibility
        "intent": topic,
        "tone": intent.get("emotional_tone", "warm"),
        "methods_fired": methods_fired,
        "findings_count": len(ranked),
        "prashna_verdict": prashna_result.get("verdict", ""),
        "prashna_confidence": prashna_result.get("confidence_pct", 0),
        "constitution_cached": hasattr(engine, '_constitution'),
    }
