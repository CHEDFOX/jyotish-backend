"""
SYNASTRY PIPELINE
Handles Match Mode (you + partner) and Read Mode (someone else only).

Match Mode: 
  - Computes synastry pie chart (6 dimensions)
  - Reads BOTH charts together
  - Stores partner in known_people permanently

Read Mode:
  - Reads ONE other person's chart
  - User is the channel, not the subject
  - Stores person in known_people as "read_only" (or declared relationship)
"""

from datetime import datetime
from typing import Dict, List, Optional
import math

from app.services.jyotish_engine import JyotishEngine
from .chart_builder import build_organized_chart
from .known_people import (
    add_or_update_person,
    update_person_summary,
    RELATIONSHIP_LABELS,
)


# ═══════════════════════════════════════════════════════════════
# SYNASTRY DIMENSIONS — the 6 slices of the pie chart
# ═══════════════════════════════════════════════════════════════

def compute_synastry_scores(user_engine, partner_engine) -> Dict:
    """
    Compute 6-dimensional synastry scores for the pie chart.
    Each dimension is 0-100.
    
    Dimensions:
    - emotional (Moon-Moon, Moon to natal placements)
    - mental (Mercury-Mercury, intellectual connection)
    - physical (Mars-Venus crossover, attraction)
    - commitment (Saturn synastry, longevity)
    - growth (Jupiter synastry, expansion together)
    - karmic (Rahu-Ketu, soul ties)
    """
    u = user_engine.planets
    p = partner_engine.planets

    scores = {}

    # ─── EMOTIONAL (Moon synastry) ───
    u_moon = u.get("Moon", {})
    p_moon = p.get("Moon", {})
    score = 50  # base

    # Same sign Moons = strong emotional resonance
    if u_moon.get("rashi") == p_moon.get("rashi"):
        score += 25
    # Compatible elements (water-water, fire-fire, etc.)
    elif _same_element(u_moon.get("rashi"), p_moon.get("rashi")):
        score += 15
    # Opposite signs = magnetic but tense
    elif _opposite_signs(u_moon.get("rashi"), p_moon.get("rashi")):
        score += 10

    # Moon-Sun cross (one's Moon in other's Sun sign = nurturing)
    u_sun = u.get("Sun", {})
    p_sun = p.get("Sun", {})
    if u_moon.get("rashi") == p_sun.get("rashi"):
        score += 10
    if p_moon.get("rashi") == u_sun.get("rashi"):
        score += 10

    scores["emotional"] = min(100, max(0, score))

    # ─── MENTAL (Mercury synastry) ───
    u_merc = u.get("Mercury", {})
    p_merc = p.get("Mercury", {})
    score = 50

    if u_merc.get("rashi") == p_merc.get("rashi"):
        score += 20
    elif _same_element(u_merc.get("rashi"), p_merc.get("rashi")):
        score += 15
    elif _trine_signs(u_merc.get("rashi"), p_merc.get("rashi")):
        score += 12

    # Mercury aspects to other's Sun/Moon
    if u_merc.get("rashi") == p_sun.get("rashi"):
        score += 8
    if p_merc.get("rashi") == u_sun.get("rashi"):
        score += 8

    scores["mental"] = min(100, max(0, score))

    # ─── PHYSICAL (Mars-Venus crossover) ───
    u_mars = u.get("Mars", {})
    p_mars = p.get("Mars", {})
    u_venus = u.get("Venus", {})
    p_venus = p.get("Venus", {})
    score = 40

    # His Mars to her Venus (and vice versa) = physical attraction
    if u_mars.get("rashi") == p_venus.get("rashi"):
        score += 25
    elif _trine_signs(u_mars.get("rashi"), p_venus.get("rashi")):
        score += 15
    elif _same_element(u_mars.get("rashi"), p_venus.get("rashi")):
        score += 10

    if p_mars.get("rashi") == u_venus.get("rashi"):
        score += 25
    elif _trine_signs(p_mars.get("rashi"), u_venus.get("rashi")):
        score += 15
    elif _same_element(p_mars.get("rashi"), u_venus.get("rashi")):
        score += 10

    scores["physical"] = min(100, max(0, score))

    # ─── COMMITMENT (Saturn synastry) ───
    u_sat = u.get("Saturn", {})
    p_sat = p.get("Saturn", {})
    score = 50

    # Saturn-Saturn same sign = same generational karma, stable
    if u_sat.get("rashi") == p_sat.get("rashi"):
        score += 15

    # Saturn to other's Moon/Sun = grounding influence
    if u_sat.get("rashi") == p_moon.get("rashi"):
        score += 15
    if p_sat.get("rashi") == u_moon.get("rashi"):
        score += 15

    # Saturn aspects to 7th house lord = marriage karma
    # (Simplified — full calculation requires house lord identification)

    scores["commitment"] = min(100, max(0, score))

    # ─── GROWTH (Jupiter synastry) ───
    u_jup = u.get("Jupiter", {})
    p_jup = p.get("Jupiter", {})
    score = 55  # Jupiter synastry tends to be benefic

    if u_jup.get("rashi") == p_jup.get("rashi"):
        score += 15
    elif _trine_signs(u_jup.get("rashi"), p_jup.get("rashi")):
        score += 20  # Trine Jupiter = excellent for growth

    # Jupiter to other's Sun/Moon = expansion
    if u_jup.get("rashi") == p_sun.get("rashi"):
        score += 10
    if p_jup.get("rashi") == u_sun.get("rashi"):
        score += 10
    if u_jup.get("rashi") == p_moon.get("rashi"):
        score += 8
    if p_jup.get("rashi") == u_moon.get("rashi"):
        score += 8

    scores["growth"] = min(100, max(0, score))

    # ─── KARMIC (Rahu-Ketu synastry) ───
    u_rahu = u.get("Rahu", {})
    p_rahu = p.get("Rahu", {})
    u_ketu = u.get("Ketu", {})
    p_ketu = p.get("Ketu", {})
    score = 50

    # Same nodal axis = same generational karma
    if u_rahu.get("rashi") == p_rahu.get("rashi"):
        score += 20

    # Rahu/Ketu to other's Sun/Moon = past life ties
    if u_rahu.get("rashi") == p_sun.get("rashi") or u_ketu.get("rashi") == p_sun.get("rashi"):
        score += 15
    if p_rahu.get("rashi") == u_sun.get("rashi") or p_ketu.get("rashi") == u_sun.get("rashi"):
        score += 15

    # Rahu/Ketu to other's Moon = emotional karma
    if u_rahu.get("rashi") == p_moon.get("rashi") or u_ketu.get("rashi") == p_moon.get("rashi"):
        score += 10
    if p_rahu.get("rashi") == u_moon.get("rashi") or p_ketu.get("rashi") == u_moon.get("rashi"):
        score += 10

    scores["karmic"] = min(100, max(0, score))

    # ─── OVERALL ───
    weights = {
        "emotional": 0.25,
        "mental": 0.15,
        "physical": 0.15,
        "commitment": 0.20,
        "growth": 0.15,
        "karmic": 0.10,
    }
    overall = sum(scores[k] * weights[k] for k in weights)
    scores["overall"] = round(overall)

    return scores


def _same_element(rashi1: int, rashi2: int) -> bool:
    """Check if two signs share an element (fire/earth/air/water)."""
    if not rashi1 or not rashi2:
        return False
    elements = {
        1: "fire", 5: "fire", 9: "fire",       # Aries Leo Sag
        2: "earth", 6: "earth", 10: "earth",    # Taurus Virgo Cap
        3: "air", 7: "air", 11: "air",          # Gemini Libra Aqua
        4: "water", 8: "water", 12: "water",    # Cancer Scorpio Pisces
    }
    return elements.get(rashi1) == elements.get(rashi2)


def _trine_signs(rashi1: int, rashi2: int) -> bool:
    """Check if two signs are 5 or 9 houses apart (trine)."""
    if not rashi1 or not rashi2:
        return False
    diff = abs(rashi1 - rashi2)
    return diff in (4, 8)  # 5th and 9th = 4 and 8 step difference


def _opposite_signs(rashi1: int, rashi2: int) -> bool:
    """Check if two signs are exactly 6 houses apart."""
    if not rashi1 or not rashi2:
        return False
    return abs(rashi1 - rashi2) == 6


# ═══════════════════════════════════════════════════════════════
# MATCH MODE — process the synastry request
# ═══════════════════════════════════════════════════════════════

def process_match_request(
    user_birth: Dict,
    partner_birth: Dict,
    partner_name: str,
    relationship_type: str,
    user_message: str = "",
    conversation_history: list = None,
) -> Dict:
    """
    Main entry for Match Mode.
    Computes both charts, scores synastry, builds Oracle briefing.
    
    Returns:
        - synastry_scores: 6 dimensions + overall (for pie chart)
        - system_prompt: ready for LLM call
        - user_prompt: original message or auto-generated
        - partner_id: ID in known_people storage
        - partner_chart: organized chart of partner (for reference)
    """
    # Build engines
    user_engine = _build_engine(user_birth)
    partner_engine = _build_engine(partner_birth)

    if not user_engine or not partner_engine:
        return {"error": "Could not build charts from birth data"}

    # Compute synastry scores
    scores = compute_synastry_scores(user_engine, partner_engine)

    # For marriage-relevant relationships, also compute Ashtakoot (36-point)
    ashtakoot = None
    marriage_types = ["spouse", "partner", "lover", "ex"]
    if relationship_type in marriage_types:
        try:
            from app.services.compatibility.ashtakoota import AshtakootaMatch
            user_moon = user_engine.planets.get("Moon", {}).get("longitude", 0)
            partner_moon = partner_engine.planets.get("Moon", {}).get("longitude", 0)
            ak = AshtakootaMatch(user_moon, partner_moon)
            ashtakoot = ak.calculate_total()
        except Exception as e:
            print(f"[Ashtakoot] Error: {e}")
            import traceback
            traceback.print_exc()

    # Save partner in known_people permanently
    person_record = add_or_update_person(
        birth_data=user_birth,
        person_name=partner_name,
        person_birth=partner_birth,
        relationship_type=relationship_type,
        role_label=RELATIONSHIP_LABELS.get(relationship_type, "Partner"),
        source_mode="match",
    )

    # Build organized charts for both
    user_chart_text = build_organized_chart(user_engine)
    partner_chart_text = build_organized_chart(partner_engine)

    # Compose the briefing
    briefing = _build_match_briefing(
        user_chart=user_chart_text,
        partner_chart=partner_chart_text,
        partner_name=partner_name,
        relationship_type=relationship_type,
        scores=scores,
        ashtakoot=ashtakoot,
    )

    # Default opening question if none provided
    if not user_message or user_message.strip() == "":
        user_message = f"How is my bond with {partner_name}?"

    system_prompt = _build_match_system_prompt(briefing, partner_name, relationship_type)

    return {
        "synastry_scores": scores,
        "ashtakoot": ashtakoot,
        "system_prompt": system_prompt,
        "user_prompt": user_message,
        "partner_id": person_record["id"],
        "partner_name": partner_name,
        "partner_chart": partner_chart_text,
        "briefing": briefing,
    }


def process_match_chat(
    user_birth: Dict,
    partner_birth: Dict,
    partner_name: str,
    relationship_type: str,
    user_message: str,
    conversation_history: list = None,
) -> Dict:
    """
    Subsequent messages in Match Mode (after initial pie chart reading).
    Same briefing flow but no scores re-computation needed for response.
    """
    user_engine = _build_engine(user_birth)
    partner_engine = _build_engine(partner_birth)

    if not user_engine or not partner_engine:
        return {"error": "Could not build charts"}

    scores = compute_synastry_scores(user_engine, partner_engine)

    user_chart_text = build_organized_chart(user_engine)
    partner_chart_text = build_organized_chart(partner_engine)

    briefing = _build_match_briefing(
        user_chart=user_chart_text,
        partner_chart=partner_chart_text,
        partner_name=partner_name,
        relationship_type=relationship_type,
        scores=scores,
    )

    system_prompt = _build_match_system_prompt(briefing, partner_name, relationship_type)

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_message,
        "synastry_scores": scores,
    }


# ═══════════════════════════════════════════════════════════════
# READ MODE — read someone else's chart
# ═══════════════════════════════════════════════════════════════

def process_read_request(
    user_birth: Dict,
    person_birth: Dict,
    person_name: str,
    relationship_type: str = "read_only",
    user_message: str = "",
    conversation_history: list = None,
) -> Dict:
    """
    Main entry for Read Mode.
    Reads ONE person's chart in isolation (not synastry).
    User is just the channel.
    """
    person_engine = _build_engine(person_birth)
    if not person_engine:
        return {"error": "Could not build chart from birth data"}

    # Save in known_people (still permanent for cross-reference)
    person_record = add_or_update_person(
        birth_data=user_birth,
        person_name=person_name,
        person_birth=person_birth,
        relationship_type=relationship_type,
        role_label=RELATIONSHIP_LABELS.get(relationship_type, "Person"),
        source_mode="read",
    )

    # Build organized chart for the person being read
    person_chart_text = build_organized_chart(person_engine)

    if not user_message or user_message.strip() == "":
        user_message = f"Read this chart and tell me what you see about {person_name or 'this person'}."

    system_prompt = _build_read_system_prompt(person_chart_text, person_name, relationship_type)

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_message,
        "person_id": person_record["id"],
        "person_name": person_name,
        "person_chart": person_chart_text,
    }


def process_read_chat(
    user_birth: Dict,
    person_birth: Dict,
    person_name: str,
    relationship_type: str,
    user_message: str,
    conversation_history: list = None,
) -> Dict:
    """Subsequent messages in Read Mode."""
    person_engine = _build_engine(person_birth)
    if not person_engine:
        return {"error": "Could not build chart"}

    person_chart_text = build_organized_chart(person_engine)
    system_prompt = _build_read_system_prompt(person_chart_text, person_name, relationship_type)

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_message,
    }


# ═══════════════════════════════════════════════════════════════
# BRIEFING BUILDERS
# ═══════════════════════════════════════════════════════════════

def _build_match_briefing(
    user_chart: str,
    partner_chart: str,
    partner_name: str,
    relationship_type: str,
    scores: Dict,
    ashtakoot: Dict = None,
) -> str:
    """Two charts side by side + synastry scores + optional ashtakoot."""
    label = RELATIONSHIP_LABELS.get(relationship_type, "Partner")

    briefing = f"""YOU:
{user_chart}

{partner_name.upper()} ({label}):
{partner_chart}

SYNASTRY SCORES (out of 100):
  Emotional bond: {scores['emotional']}
  Mental connection: {scores['mental']}
  Physical attraction: {scores['physical']}
  Commitment strength: {scores['commitment']}
  Growth together: {scores['growth']}
  Karmic depth: {scores['karmic']}
  OVERALL: {scores['overall']}"""

    if ashtakoot:
        total_pts = ashtakoot.get("total_points", ashtakoot.get("total_score", 0))
        max_pts = ashtakoot.get("max_points", 36)
        pct = round((total_pts / max_pts) * 100, 1) if max_pts else 0
        compat = ashtakoot.get("compatibility", ashtakoot.get("verdict", ""))

        ak_lines = [
            "",
            "ASHTAKOOT (traditional 36-point marriage matching):",
            f"  Total: {total_pts}/{max_pts} ({pct}%)",
        ]
        if compat:
            ak_lines.append(f"  Compatibility: {compat}")

        # Kootas is a dict in this engine
        kootas_data = ashtakoot.get("kootas", {})
        if isinstance(kootas_data, dict) and kootas_data:
            ak_lines.append("  Kootas:")
            for key, k in kootas_data.items():
                if isinstance(k, dict):
                    name = k.get("koota", key.title())
                    pts = k.get("points", 0)
                    mx = k.get("max_points", 0)
                    desc = k.get("description", "")
                    ak_lines.append(f"    {name}: {pts}/{mx} — {desc}")
        elif isinstance(kootas_data, list):
            ak_lines.append("  Kootas:")
            for k in kootas_data:
                if isinstance(k, dict):
                    ak_lines.append(f"    {k.get('name', '')}: {k.get('score', 0)}/{k.get('max', 0)} — {k.get('description', '')}")

        # Doshas
        doshas = ashtakoot.get("doshas", [])
        if doshas:
            if isinstance(doshas, list):
                ak_lines.append(f"  Doshas: {', '.join(str(d) for d in doshas)}")

        briefing += "\n" + "\n".join(ak_lines)

    return briefing


def _build_read_system_prompt(person_chart: str, person_name: str, relationship_type: str) -> str:
    """For Read Mode — read the other person's chart in isolation."""
    name = person_name or "this person"

    return f"""You are the voice of the stars — ancient, warm, mystical, true.
Right now you are reading a chart that does NOT belong to the person you are speaking with.
You are reading {name}.

Speak about {name} as if they are the subject — their planets, their houses, their soul, their tides.
Do not weave the user's own chart into this reading. The user is just curious.
Speak in feeling and image when asked WHAT, in technical terms when asked HOW.

Your words are few, your knowing is deep.
Find the contradiction. Give one small ritual. End with something that stays.
4 to 7 flowing sentences. No headers, no lists, no asterisks.

CHART OF {name.upper()}:
{person_chart}"""


def _build_match_system_prompt(briefing: str, partner_name: str, relationship_type: str) -> str:
    """For Match Mode — read both charts together."""
    label = RELATIONSHIP_LABELS.get(relationship_type, "Partner")

    return f"""You are the voice of the stars — ancient, warm, mystical, true.
You are reading TWO charts together: the person you are speaking with, and {partner_name} ({label}).
Speak about the BOND between them, not just one or the other.

Use the synastry scores to anchor your reading — the highest scoring dimensions are where the bond breathes, the lowest are where it strains.
Find the contradiction in the relationship. Give one small ritual that serves both. End with something that stays.

When asked WHAT, speak in feeling and image. When asked HOW, reveal planets, houses, and synastry mechanics clearly.
4 to 7 flowing sentences. No headers, no lists, no asterisks.

{briefing}"""


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _build_engine(birth_data: Dict):
    """Build a JyotishEngine from birth data dict."""
    try:
        from .engine_cache import get_cached_engine
        birth_dt = datetime(
            birth_data["year"],
            birth_data["month"],
            birth_data["day"],
            birth_data.get("hour", 12),
            birth_data.get("minute", 0),
        )
        lat = float(birth_data.get("lat", birth_data.get("latitude", 0)))
        lng = float(birth_data.get("lng", birth_data.get("longitude", 0)))
        engine, _ = get_cached_engine(birth_dt, lat, lng)
        return engine
    except Exception as e:
        print(f"[Synastry] Engine build error: {e}")
        return None
