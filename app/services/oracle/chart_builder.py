"""
CHART BUILDER
Generates a clean, organized chart representation from JyotishEngine.
~900 characters. Contains everything an astrologer needs to read the chart.

This is the BASE that goes with every single query.
"""

from typing import Dict

RASHI_LIST = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

RASHI_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

OWN_SIGNS = {
    "Sun": ["Leo"], "Moon": ["Cancer"], "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"], "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"], "Saturn": ["Capricorn", "Aquarius"],
}

EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra",
}

DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries",
}


def build_organized_chart(engine) -> str:
    """
    Build a clean, organized chart string from a JyotishEngine instance.
    Returns ~900 characters containing everything needed.
    """
    # Check cache
    if hasattr(engine, '_organized_chart') and engine._organized_chart:
        return engine._organized_chart

    planets = engine.planets
    asc = engine.ascendant
    asc_rashi = asc.get("rashi_name", "Leo")
    asc_idx = RASHI_LIST.index(asc_rashi) if asc_rashi in RASHI_LIST else 0

    lines = []
    lines.append("COMPLETE CHART:")
    lines.append(f"Ascendant: {asc_rashi} ({asc.get('nakshatra_name', '')})")

    # Each planet with house, sign, nakshatra, lordship, dignity
    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        d = planets.get(name, {})
        rashi = d.get("rashi_name", "")
        house = d.get("house", 0)
        nak = d.get("nakshatra_name", "")
        retro = " RETROGRADE" if d.get("retrograde") else ""

        lines.append(f"{name}: {rashi} H{house} {nak}{retro}")

        # Lordship (which houses does this planet rule)
        lord_of = []
        for i in range(12):
            r = RASHI_LIST[(asc_idx + i) % 12]
            if RASHI_LORDS.get(r) == name:
                lord_of.append(f"H{i + 1}")
        if lord_of:
            lines.append(f"  Rules: {' '.join(lord_of)}")

        # Dignity
        if name in OWN_SIGNS:
            if rashi in OWN_SIGNS[name]:
                lines.append("  Dignity: OWN SIGN")
            elif EXALTATION.get(name) == rashi:
                lines.append("  Dignity: EXALTED")
            elif DEBILITATION.get(name) == rashi:
                lines.append("  Dignity: DEBILITATED")

    # Combustion
    try:
        comb = engine.get_combustion()
        if comb.get("combust_planets"):
            lines.append("")
            lines.append("COMBUSTION:")
            for cp in comb["combust_planets"]:
                lines.append(f"  {cp['planet']}: {cp['severity']} ({cp['distance_from_sun']} deg from Sun)")
    except Exception:
        pass

    # Gandanta
    try:
        gand = engine.get_gandanta()
        if gand.get("gandanta_planets"):
            lines.append("")
            lines.append("GANDANTA:")
            for gp in gand["gandanta_planets"]:
                lines.append(f"  {gp['planet']}: {gp['severity']} in {gp['gandanta_zone']}")
    except Exception:
        pass

    # Key yogas (top 3 only)
    try:
        yogas = engine.get_yogas()
        highlights = yogas.get("highlights", [])[:3]
        if highlights:
            lines.append("")
            lines.append("KEY YOGAS:")
            for y in highlights:
                if isinstance(y, dict):
                    lines.append(f"  {y.get('name', '')}")
    except Exception:
        pass

    # Dasha timeline
    try:
        dasha = engine.get_vimshottari_dasha()
        dasha_str = dasha.get("dasha_string", "")
        if dasha_str:
            lines.append("")
            lines.append(f"CURRENT DASHA: {dasha_str}")
        periods = engine.get_vimshottari_periods()
        if periods:
            from datetime import datetime as _dt
            now = _dt.now()
            lines.append("DASHA TIMELINE:")
            for p in periods:
                if isinstance(p, dict):
                    lord = p.get("lord", p.get("planet", ""))
                    start = str(p.get("start", p.get("start_date", "")))[:10]
                    end = str(p.get("end", p.get("end_date", "")))[:10]
                    try:
                        s_dt = _dt.fromisoformat(start)
                        e_dt = _dt.fromisoformat(end)
                        if s_dt <= now <= e_dt:
                            lines.append(f"  {lord}: {start} to {end}")
                        elif e_dt < now:
                            lines.append(f"  {lord}: {start} to {end}")
                        else:
                            lines.append(f"  {lord}: {start} to {end}")
                    except Exception:
                        lines.append(f"  {lord}: {start} to {end}")
    except Exception:
        pass

    result = "\n".join(lines)

    # Cache
    engine._organized_chart = result
    return result


def build_prashna_section(engine, category: str = "general") -> str:
    """Cast prashna for this moment and return a compact verdict."""
    try:
        from .consultation_engine import _cast_prashna
        pr = _cast_prashna(engine, category)
        verdict = pr.get("verdict", "unavailable")
        conf = pr.get("confidence_pct", 0)
        timing = pr.get("timing", "unclear")
        reasons = pr.get("reasoning", [])[:3]
        lines = [
            f"PRASHNA (this moment): {verdict} ({conf}% confidence)",
            f"  Timing: {timing}",
        ]
        if reasons:
            lines.append("  Factors: " + "; ".join(reasons))
        return "\n".join(lines)
    except Exception:
        return ""


def build_memory_section(birth_data: dict) -> str:
    """Recall user memory for the briefing."""
    try:
        from .user_memory import recall_user_memory
        mem = recall_user_memory(birth_data)
        if mem:
            return "PREVIOUS SESSIONS (do NOT repeat these):\n" + mem
        return ""
    except Exception:
        return ""
