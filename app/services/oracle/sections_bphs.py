"""
BPHS SECTION BUILDERS
Each function takes a JyotishEngine and returns clean, readable text
for one data section. The LLM reads this like a chart sheet.
"""

from datetime import datetime
from typing import Dict

RASHI_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

RASHI_LIST = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def build_base_chart(engine) -> str:
    """Base chart — always included. Positions, houses, lordships, dignity."""
    planets = engine.planets
    asc = engine.ascendant
    asc_rashi = asc.get("rashi_name", "")
    asc_idx = RASHI_LIST.index(asc_rashi) if asc_rashi in RASHI_LIST else 0

    lines = [f"Ascendant: {asc_rashi} {round(asc.get('longitude', 0) % 30, 1)}° ({asc.get('nakshatra_name', '')})"]

    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        d = planets.get(name, {})
        rashi = d.get("rashi_name", "")
        retro = " R" if d.get("retrograde") else ""

        # Lordship
        lord_of = []
        for i in range(12):
            r = RASHI_LIST[(asc_idx + i) % 12]
            if RASHI_LORDS.get(r) == name:
                lord_of.append(str(i + 1))

        lord_str = f"  L{','.join(lord_of)}" if lord_of else ""
        lines.append(f"{name:8s} {rashi:12s} H{str(d.get('house', '?')):<3s} {d.get('nakshatra_name', ''):16s} {round(d.get('longitude', 0) % 30, 1):>5.1f}°{retro}{lord_str}")

    return "\n".join(lines)


def build_dashas_full(engine) -> str:
    """Full dasha timeline with dates."""
    lines = []
    try:
        dasha = engine.get_vimshottari_dasha()
        lines.append(f"Current: {dasha.get('dasha_string', '')}")

        periods = engine.get_vimshottari_periods()
        if periods:
            now = datetime.now()
            for p in periods:
                lord = p.get("lord", p.get("planet", ""))
                start = str(p.get("start", p.get("start_date", "")))[:10]
                end = str(p.get("end", p.get("end_date", "")))[:10]
                marker = " ◀ CURRENT" if start <= now.strftime("%Y-%m-%d") <= end else ""
                lines.append(f"  {lord:8s} {start} to {end}{marker}")
    except Exception as e:
        lines.append(f"Dasha calculation error: {str(e)[:80]}")
    return "\n".join(lines)


def build_transits(engine) -> str:
    """Current transit positions and effects."""
    lines = []
    try:
        transits = engine.get_current_transits()
        overall = transits.get("overall_period", "")
        if overall:
            lines.append(f"Overall: {overall}")
        effects = transits.get("transit_effects", [])
        for e in effects[:8]:
            if isinstance(e, dict):
                lines.append(f"  {e.get('planet', '')} in H{e.get('house', '')} ({e.get('rashi', '')}): {e.get('effect', '')[:80]}")

        # Sade Sati check
        sade = engine.check_sade_sati()
        if sade.get("is_sade_sati"):
            lines.append(f"  SADE SATI ACTIVE: {sade.get('phase', '')}")
    except Exception:
        pass
    return "\n".join(lines)


def build_yogas(engine) -> str:
    """All yogas found in the chart."""
    lines = []
    try:
        yogas = engine.get_yogas()
        highlights = yogas.get("highlights", [])
        for y in highlights:
            if isinstance(y, dict):
                name = y.get("name", "")
                desc = y.get("description", y.get("effect", ""))[:100]
                lines.append(f"  {name}: {desc}")
        total = yogas.get("summary", {}).get("total_yogas", 0)
        lines.append(f"Total: {total} yogas")
    except Exception:
        pass
    return "\n".join(lines)


def build_navamsa(engine) -> str:
    """D9 Navamsa chart — marriage and spouse indicators."""
    lines = []
    try:
        nav = engine.get_navamsa_analysis()
        spouse = nav.get("spouse_description", nav.get("partner_nature", ""))
        if spouse:
            lines.append(f"Spouse nature: {spouse}")
        venus_nav = nav.get("venus_navamsa", {})
        if isinstance(venus_nav, dict):
            lines.append(f"Venus in D9: {venus_nav.get('sign', '')} — {venus_nav.get('interpretation', '')[:80]}")
        seventh = nav.get("seventh_lord_navamsa", nav.get("d9_7th_lord", {}))
        if isinstance(seventh, dict) and seventh:
            lines.append(f"7th lord in D9: {seventh.get('sign', '')} — {seventh.get('interpretation', '')[:80]}")
    except Exception:
        pass
    return "\n".join(lines)


def build_dasamsa(engine) -> str:
    """D10 Dasamsa chart — career indicators."""
    lines = []
    try:
        d10 = engine.get_career_analysis()
        field = d10.get("recommended_field", d10.get("career_type", ""))
        if field:
            lines.append(f"Career field: {field}")
        tenth_lord = d10.get("tenth_lord", {})
        if isinstance(tenth_lord, dict):
            lines.append(f"10th lord: {tenth_lord.get('planet', '')} in {tenth_lord.get('sign', '')} H{tenth_lord.get('house', '')}")
    except Exception:
        pass
    return "\n".join(lines)


def build_house_detail(engine, house_num: int) -> str:
    """Deep analysis of a specific house."""
    lines = []
    try:
        planets = engine.planets
        asc_rashi = engine.ascendant_rashi

        # Find house sign, lord, occupants
        house_rashi_idx = (asc_rashi + house_num - 1) % 12
        house_sign = RASHI_LIST[house_rashi_idx]
        house_lord = RASHI_LORDS.get(house_sign, "")
        lord_data = planets.get(house_lord, {})

        lines.append(f"Sign: {house_sign} | Lord: {house_lord} in {lord_data.get('rashi_name', '')} H{lord_data.get('house', '?')}")

        occupants = [n for n, d in planets.items() if d.get('house') == house_num]
        if occupants:
            lines.append(f"Occupants: {', '.join(occupants)}")
        else:
            lines.append("Occupants: None (untenanted)")

        # Aspects on this house
        aspects = engine.get_planetary_aspects()
        if isinstance(aspects, dict):
            house_aspects = []
            for planet, asp_data in aspects.items():
                if isinstance(asp_data, dict):
                    aspected_houses = asp_data.get("aspected_houses", [])
                    if house_num in aspected_houses:
                        house_aspects.append(planet)
            if house_aspects:
                lines.append(f"Aspected by: {', '.join(house_aspects)}")
    except Exception:
        pass
    return "\n".join(lines)


def build_jaimini(engine) -> str:
    """Jaimini karakas and arudhas."""
    lines = []
    try:
        karakas = engine.get_jaimini_karakas()
        for key in ['atmakaraka', 'amatyakaraka', 'darakaraka', 'putrakaraka']:
            k = karakas.get(key, {})
            if isinstance(k, dict) and k.get('planet'):
                label = key.replace('karaka', '').capitalize()
                lines.append(f"{label}karaka: {k['planet']} in {k.get('sign', '')} H{k.get('house', '')}")
    except Exception:
        pass
    return "\n".join(lines)


def build_afflictions(engine) -> str:
    """Combustion, gandanta, sade sati."""
    lines = []
    try:
        comb = engine.get_combustion()
        if comb.get("combust_planets"):
            for cp in comb["combust_planets"]:
                lines.append(f"COMBUST: {cp['planet']} — {cp['severity']} ({cp['distance_from_sun']}° from Sun)")

        gand = engine.get_gandanta()
        if gand.get("gandanta_planets"):
            for gp in gand["gandanta_planets"]:
                lines.append(f"GANDANTA: {gp['planet']} — {gp['severity']} in {gp['gandanta_zone']}")

        sade = engine.check_sade_sati()
        if sade.get("is_sade_sati"):
            lines.append(f"SADE SATI: Active — {sade.get('phase', '')}")
        else:
            lines.append("Sade Sati: Not active")
    except Exception:
        pass
    return "\n".join(lines) if lines else "No major afflictions"


def build_medical(engine) -> str:
    """Medical astrology — health vulnerabilities."""
    lines = []
    try:
        med = engine.get_medical_report()
        vulns = med.get("vulnerabilities", med.get("health_areas", []))
        if isinstance(vulns, list):
            for v in vulns[:5]:
                if isinstance(v, dict):
                    lines.append(f"  {v.get('area', '')}: {v.get('description', v.get('indication', ''))[:80]}")
        longevity = med.get("longevity", "")
        if longevity:
            lines.append(f"Longevity: {longevity}")
    except Exception:
        pass
    return "\n".join(lines)


def build_remedies(engine) -> str:
    """Gemstones, mantras, rituals."""
    lines = []
    try:
        rem = engine.get_remedies()
        gems = rem.get("gemstones", [])
        for g in gems[:3]:
            if isinstance(g, dict):
                lines.append(f"Gemstone: {g.get('gemstone', '')} for {g.get('planet', '')} — {g.get('reason', '')[:60]}")
        mantras = rem.get("mantras", [])
        for m in mantras[:3]:
            if isinstance(m, dict):
                lines.append(f"Mantra: {m.get('mantra', '')[:60]} for {m.get('planet', '')}")
    except Exception:
        pass
    return "\n".join(lines)


def build_classical_rules(engine, topic: str = None) -> str:
    """BPHS classical rules for a life event."""
    lines = []
    try:
        if topic:
            result = engine.get_classical_analysis(topic)
        else:
            result = engine.get_classical_analysis()

        if isinstance(result, dict) and 'events' not in result:
            summary = result.get("summary", "")
            supports = result.get("supports", [])
            opposes = result.get("opposes", [])
            if summary:
                lines.append(summary)
            for s in supports[:3]:
                text = s.get("text", str(s)) if isinstance(s, dict) else str(s)
                lines.append(f"  ✓ {text[:100]}")
            for o in opposes[:2]:
                text = o.get("text", str(o)) if isinstance(o, dict) else str(o)
                lines.append(f"  ✗ {text[:100]}")
    except Exception:
        pass
    return "\n".join(lines)


def build_personality(engine) -> str:
    """Full personality profile."""
    lines = []
    try:
        p = engine.get_personality()
        archetype = p.get("archetype", p.get("personality_type", ""))
        if archetype:
            lines.append(f"Archetype: {archetype}")
        moon_p = p.get("moon_personality", {})
        if isinstance(moon_p, dict):
            lines.append(f"Emotional nature: {moon_p.get('description', '')[:100]}")
        asc_p = p.get("ascendant_personality", {})
        if isinstance(asc_p, dict):
            lines.append(f"Outer self: {asc_p.get('description', '')[:100]}")
    except Exception:
        pass
    return "\n".join(lines)


def build_nadi(engine) -> str:
    """Bhrigu Nandi Nadi reading."""
    lines = []
    try:
        nadi = engine.get_nadi_reading()
        preds = nadi.get("predictions", nadi.get("readings", []))
        if isinstance(preds, list):
            for p in preds[:5]:
                if isinstance(p, dict):
                    lines.append(f"  {p.get('prediction', p.get('text', ''))[:120]}")
    except Exception:
        pass
    return "\n".join(lines)


def build_annual(engine, year: int = None) -> str:
    """Varshaphal annual prediction."""
    lines = []
    try:
        y = year or datetime.now().year
        vp = engine.get_varshaphal(y)
        overall = vp.get("overall", {})
        if isinstance(overall, dict):
            lines.append(f"Year {y}: {overall.get('rating', '')} ({overall.get('score', '')}/100)")
            lines.append(f"Summary: {overall.get('summary', '')[:120]}")
        yl = vp.get("year_lord", {})
        if isinstance(yl, dict):
            lines.append(f"Year lord: {yl.get('planet', '')} ({yl.get('strength', '')})")
    except Exception:
        pass
    return "\n".join(lines)


def build_prashna(engine) -> str:
    """Prashna for this moment."""
    lines = []
    try:
        pr = engine.cast_prashna_refined()
        refined = pr.get("refined_verdict", {})
        if isinstance(refined, dict):
            verdict = refined.get("verdict", "")
            conf = refined.get("confidence_pct", "")
            timing = refined.get("timing", "")
            lines.append(f"Verdict: {verdict} ({conf}% confidence)")
            if timing:
                lines.append(f"Timing: {timing}")
            reasons = refined.get("reasoning", [])
            for r in reasons[:3]:
                lines.append(f"  {r}")
    except Exception:
        pass
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# SECTION DISPATCHER
# ═══════════════════════════════════════════════════════════════

SECTION_MAP = {
    'dashas_full': ('DASHA TIMELINE', build_dashas_full),
    'transits': ('CURRENT TRANSITS', build_transits),
    'yogas': ('YOGAS', build_yogas),
    'navamsa': ('NAVAMSA (D9)', build_navamsa),
    'dasamsa': ('DASAMSA (D10)', build_dasamsa),
    'jaimini': ('JAIMINI', build_jaimini),
    'afflictions': ('AFFLICTIONS', build_afflictions),
    'medical': ('MEDICAL', build_medical),
    'remedies': ('REMEDIES', build_remedies),
    'classical_rules': ('CLASSICAL RULES', build_classical_rules),
    'personality': ('PERSONALITY', build_personality),
    'nadi': ('NADI READING', build_nadi),
    'annual': ('ANNUAL FORECAST', build_annual),
    'prashna': ('PRASHNA', build_prashna),
    'ashtakavarga': ('ASHTAKAVARGA', lambda e: _build_ashtakavarga(e)),
    'shadbala': ('SHADBALA (PLANET STRENGTH)', lambda e: _build_shadbala(e)),
    'divisional_charts': ('DIVISIONAL CHARTS', lambda e: _build_divisional(e)),
    'bhava_chalit': ('BHAVA CHALIT', lambda e: _build_bhava_chalit(e)),
    'alt_dashas': ('ALTERNATIVE DASHAS', lambda e: _build_alt_dashas(e)),
    'transit_deep': ('TRANSIT DEEP ANALYSIS', lambda e: _build_transit_deep(e)),
    'career_aptitude': ('CAREER APTITUDE', lambda e: _build_career_aptitude(e)),
    'numerology': ('NUMEROLOGY', lambda e: _build_numerology(e)),
    'vastu': ('VASTU', lambda e: _build_vastu(e)),
    'chakra': ('CHAKRA ANALYSIS', lambda e: _build_chakra(e)),
    'muhurta': ('MUHURTA (AUSPICIOUS TIMING)', lambda e: _build_muhurta(e)),
    'planetary_returns': ('PLANETARY RETURNS', lambda e: _build_planetary_returns(e)),
    'weekly_forecast': ('WEEKLY FORECAST', lambda e: _build_weekly(e)),
    'daily_snapshot': ('DAILY SNAPSHOT', lambda e: _build_daily_snapshot(e)),
    'past_events': ('PAST EVENT ANALYSIS', lambda e: _build_past_events(e)),
    'life_timeline': ('LIFE TIMELINE', lambda e: _build_life_timeline(e)),
    'relocation': ('RELOCATION ANALYSIS', lambda e: _build_relocation(e)),
    'baby_names': ('BABY NAMES', lambda e: _build_baby_names(e)),
    'sudarshana': ('SUDARSHANA CHAKRA', lambda e: _build_sudarshana(e)),
    'nakshatra_profile': ('NAKSHATRA PROFILE', lambda e: _build_nakshatra(e)),
    'yoga_timing': ('YOGA ACTIVATION TIMING', lambda e: _build_yoga_timing(e)),
    'lucky': ('LUCKY NUMBERS / COLORS / MANTRAS', lambda e: _build_lucky(e)),
    'bphs_advanced': ('BPHS ADVANCED', lambda e: _build_bphs_advanced(e)),
    'spiritual': ('SPIRITUAL ANALYSIS', lambda e: _build_spiritual(e)),
    'maraka': ('MARAKA (LONGEVITY)', lambda e: _build_maraka(e)),
    'argala': ('ARGALA & SARVATOBHADRA', lambda e: _build_argala(e)),
    'tithi_pravesh': ('TITHI PRAVESH', lambda e: _build_tithi_pravesh(e)),
    'chart_promise': ('CHART PROMISE', lambda e: _build_chart_promise(e)),
    'period_query': ('PERIOD ANALYSIS', lambda e: _build_period_query(e)),
    'manglik': ('MANGLIK ANALYSIS', lambda e: _build_manglik(e)),
    'pratyantar': ('PRATYANTAR DASHA', lambda e: _build_pratyantar(e)),
    'timing_windows': ('EVENT TIMING', lambda e: _build_timing_windows(e)),
    'arudha_padas': ('ARUDHA PADAS', lambda e: _build_arudha_padas(e)),
    'av_transits': ('ASHTAKAVARGA TRANSITS', lambda e: _build_av_transits(e)),
    'future_transits': ('FUTURE TRANSITS', lambda e: _build_future_transits(e)),
    'transit_aspects': ('TRANSIT ASPECTS', lambda e: _build_transit_aspects(e)),
    'name_numerology': ('NAME NUMEROLOGY', lambda e: _build_name_numerology(e)),
    'hora': ('HORA (PLANETARY HOURS)', lambda e: _build_hora(e)),
    'panchanga': ('PANCHANGA', lambda e: _build_panchanga(e)),
    'dasha_sandhi': ('DASHA SANDHI', lambda e: _build_dasha_sandhi(e)),
    'rashi_drishti': ('RASHI DRISHTI', lambda e: _build_rashi_drishti(e)),
    'av_sodhana': ('AV SODHANA', lambda e: _build_av_sodhana(e)),
    'prastara_av': ('PRASTARA ASHTAKAVARGA', lambda e: _build_prastara(e)),
    'shodhya_pinda': ('SHODHYA PINDA', lambda e: _build_shodhya_pinda(e)),
    'bhava_strengths': ('BHAVA STRENGTHS', lambda e: _build_bhava_strengths(e)),
    'ishta_kashta': ('ISHTA KASHTA PHALA', lambda e: _build_ishta_kashta(e)),
    'gemstones': ('GEMSTONE RECOMMENDATIONS', lambda e: _build_gemstones(e)),
    'synastry': ('SYNASTRY', lambda e: _build_synastry(e)),
    'composite': ('COMPOSITE CHART', lambda e: _build_composite(e)),
    'location': ('LOCATION ANALYSIS', lambda e: _build_location(e)),
    'raja_yogas': ('RAJA YOGAS', lambda e: _build_raja_yogas(e)),
    'dhana_yogas': ('DHANA YOGAS', lambda e: _build_dhana_yogas(e)),
    'daridra_yogas': ('DARIDRA YOGAS', lambda e: _build_daridra_yogas(e)),
    'female_horoscopy': ('FEMALE HOROSCOPY', lambda e: _build_female(e)),
    'longevity': ('LONGEVITY', lambda e: _build_longevity(e)),
    'dasha_psychology': ('DASHA PSYCHOLOGY', lambda e: _build_dasha_psych(e)),
    'dasha_interpretation': ('DASHA INTERPRETATION', lambda e: _build_dasha_interp(e)),
    'special_lagnas': ('SPECIAL LAGNAS', lambda e: _build_special_lagnas(e)),
    'jaimini_complete': ('JAIMINI COMPLETE', lambda e: _build_jaimini_complete(e)),
    'upapada': ('UPAPADA LAGNA', lambda e: _build_upapada(e)),
    'muhurta_rules': ('MUHURTA RULES', lambda e: _build_muhurta_rules(e)),
}


def build_sections(engine, section_names: list, topic: str = None) -> str:
    """Build all requested sections and return combined text."""
    parts = []

    for section_name in section_names:
        if section_name.startswith("house_detail:"):
            try:
                house_num = int(section_name.split(":")[1])
                text = build_house_detail(engine, house_num)
                if text:
                    parts.append(f"HOUSE {house_num} DETAIL:\n{text}")
            except (ValueError, IndexError):
                pass
            continue

        entry = SECTION_MAP.get(section_name)
        if not entry:
            continue

        label, builder = entry
        try:
            if section_name == 'classical_rules' and topic:
                text = builder(engine, topic)
            elif section_name in ('chart_promise', 'timing_windows') and topic:
                text = builder(engine, topic)
            else:
                text = builder(engine)
            if text and text.strip():
                parts.append(f"{label}:\n{text}")
        except Exception:
            continue

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# NEW SECTION BUILDERS (covering all remaining engine methods)
# ═══════════════════════════════════════════════════════════════

def _safe(fn, fallback=""):
    try:
        return fn()
    except Exception:
        return fallback

def _fmt_dict_list(items, key="", max_items=8):
    lines = []
    for item in (items or [])[:max_items]:
        if isinstance(item, dict):
            text = item.get(key, item.get("text", item.get("description", item.get("name", str(item)[:100]))))
            lines.append(f"  {str(text)[:120]}")
        else:
            lines.append(f"  {str(item)[:120]}")
    return "\n".join(lines)

def _build_ashtakavarga(engine) -> str:
    av = engine.get_ashtakavarga()
    lines = []
    sav = av.get("sarvashtakavarga", av.get("sav", {}))
    if isinstance(sav, dict):
        for sign, score in list(sav.items())[:12]:
            lines.append(f"  {sign}: {score} bindus")
    total = av.get("total_bindus", sum(sav.values()) if isinstance(sav, dict) else 0)
    lines.append(f"Total: {total}")
    return "\n".join(lines)

def _build_shadbala(engine) -> str:
    sb = engine.get_shadbala_complete()
    lines = []
    for planet, data in (sb if isinstance(sb, dict) else {}).items():
        if isinstance(data, dict) and 'total' in data:
            lines.append(f"  {planet}: {data['total']:.1f} rupas")
    cs = engine.get_chart_strength()
    if isinstance(cs, dict):
        lines.append(f"Chart Strength: {cs.get('score', '')}/100")
    return "\n".join(lines)

def _build_divisional(engine) -> str:
    va = engine.get_varga_analysis()
    lines = []
    for chart_name, data in (va if isinstance(va, dict) else {}).items():
        if isinstance(data, dict):
            lines.append(f"{chart_name}: {str(data.get('summary', data.get('interpretation', '')))[:100]}")
    return "\n".join(lines)

def _build_bhava_chalit(engine) -> str:
    bc = engine.get_bhava_chalit()
    lines = []
    shifts = bc.get("shifts", bc.get("shifted_planets", []))
    if isinstance(shifts, list):
        for s in shifts:
            if isinstance(s, dict):
                lines.append(f"  {s.get('planet', '')}: rashi H{s.get('rashi_house', '')} → bhava H{s.get('bhava_house', '')}")
    if not lines:
        lines.append("No planets shift between rashi and bhava charts")
    return "\n".join(lines)

def _build_alt_dashas(engine) -> str:
    lines = []
    for name, method in [("Yogini", "get_yogini_dasha"), ("Chara", "get_chara_dasha"),
                          ("Kalachakra", "get_kalachakra_dasha"), ("Narayana", "get_narayana_dasha")]:
        try:
            d = getattr(engine, method)()
            lord = d.get("lord", d.get("planet", d.get("sign", "")))
            lines.append(f"  {name}: {lord}")
        except Exception:
            pass
    cv = _safe(lambda: engine.cross_validate_dashas())
    if isinstance(cv, dict) and cv.get("agreement"):
        lines.append(f"Cross-validation: {cv['agreement']}")
    return "\n".join(lines)

def _build_transit_deep(engine) -> str:
    lines = []
    td = _safe(lambda: engine.get_transit_deep())
    if isinstance(td, dict):
        for key in ['summary', 'sade_sati', 'retrogrades']:
            val = td.get(key, "")
            if val:
                lines.append(f"  {key}: {str(val)[:100]}")
    tc = _safe(lambda: engine.get_transit_calendar(3))
    if isinstance(tc, dict):
        for m in tc.get("months", [])[:3]:
            if isinstance(m, dict):
                lines.append(f"  {m.get('short', '')}: {m.get('score', '')}/100 — {m.get('theme', '')[:60]}")
    vedha = _safe(lambda: engine.get_vedha())
    if isinstance(vedha, dict) and vedha.get("obstructed_count"):
        lines.append(f"  Vedha: {vedha['obstructed_count']} transits obstructed")
    ecl = _safe(lambda: engine.get_eclipse_calendar())
    if isinstance(ecl, dict):
        upcoming = ecl.get("eclipses", ecl.get("upcoming", []))
        if isinstance(upcoming, list) and upcoming:
            e = upcoming[0]
            if isinstance(e, dict):
                lines.append(f"  Next eclipse: {e.get('date', '')} {e.get('type', '')} — {str(e.get('personal_impact', ''))[:60]}")
    return "\n".join(lines)

def _build_career_aptitude(engine) -> str:
    ca = engine.get_career_aptitude()
    lines = []
    for f in (ca.get("top_fields", ca.get("aptitude", [])) if isinstance(ca, dict) else [])[:6]:
        if isinstance(f, dict):
            lines.append(f"  {f.get('field', '')}: {f.get('score', '')}%")
    return "\n".join(lines)

def _build_numerology(engine) -> str:
    n = engine.get_numerology()
    lines = []
    if isinstance(n, dict):
        lines.append(f"Mulank: {n.get('mulank', n.get('life_path', ''))}")
        lines.append(f"Bhagyank: {n.get('bhagyank', n.get('destiny', ''))}")
    pd = engine.get_personal_day()
    if isinstance(pd, dict):
        lines.append(f"Personal day: {pd.get('day', '')} | month: {pd.get('month', '')} | year: {pd.get('year', '')}")
    return "\n".join(lines)

def _build_vastu(engine) -> str:
    v = engine.get_vastu()
    return f"Best direction: {v.get('best_direction', v.get('lucky_direction', ''))}" if isinstance(v, dict) else ""

def _build_chakra(engine) -> str:
    c = engine.get_chakra_analysis()
    lines = []
    for ch in (c.get("chakras", []) if isinstance(c, dict) else []):
        if isinstance(ch, dict):
            lines.append(f"  {ch.get('name', '')}: {ch.get('status', '')} — {str(ch.get('description', ''))[:60]}")
    return "\n".join(lines)

def _build_muhurta(engine) -> str:
    lines = []
    m = _safe(lambda: engine.find_muhurta("general", 30))
    if isinstance(m, dict):
        dates = m.get("dates", m.get("auspicious_dates", []))
        for d in (dates if isinstance(dates, list) else [])[:5]:
            if isinstance(d, dict):
                lines.append(f"  {d.get('date', '')}: {d.get('quality', d.get('score', ''))}")
    timing = _safe(lambda: engine.get_daily_timing())
    if isinstance(timing, dict):
        lines.append(f"Hora: {timing.get('current_hora', '')}")
    return "\n".join(lines)

def _build_planetary_returns(engine) -> str:
    pr = engine.get_planetary_returns()
    lines = []
    if isinstance(pr, dict):
        for planet, data in pr.items():
            if isinstance(data, dict):
                lines.append(f"  {planet}: {str(data.get('date', data.get('next_return', '')))[:40]} — {str(data.get('interpretation', ''))[:60]}")
    return "\n".join(lines)

def _build_weekly(engine) -> str:
    w = engine.get_weekly_forecast()
    return str(w.get("summary", w.get("week_summary", "")))[:300] if isinstance(w, dict) else ""

def _build_daily_snapshot(engine) -> str:
    lines = []
    rd = _safe(lambda: engine.get_realtime_dashboard())
    if isinstance(rd, dict):
        lines.append(f"Hora: {rd.get('current_hora', '')}")
        lines.append(f"Advice: {str(rd.get('quick_advice', ''))[:80]}")
    dr = _safe(lambda: engine.get_daily_ritual())
    if isinstance(dr, dict):
        lines.append(f"Ritual: {str(dr.get('ritual', dr.get('suggestion', '')))[:80]}")
    br = _safe(lambda: engine.get_biorhythm())
    if isinstance(br, dict):
        lines.append(f"Biorhythm: P={br.get('physical', '')} E={br.get('emotional', '')} I={br.get('intellectual', '')}")
    cmf = _safe(lambda: engine.get_color_metal_food())
    if isinstance(cmf, dict):
        lines.append(f"Today: color={cmf.get('color', '')} metal={cmf.get('metal', '')} food={cmf.get('food', '')}")
    return "\n".join(lines)

def _build_past_events(engine, event_date=None, event_type=None) -> str:
    if not event_date:
        return "Provide event date and type for past event analysis"
    result = engine.explain_past_event(event_date, event_type or "general")
    return str(result.get("explanation", result.get("summary", "")))[:300] if isinstance(result, dict) else ""

def _build_life_timeline(engine) -> str:
    lt = engine.get_life_timeline(5)
    lines = []
    if isinstance(lt, dict):
        for year_data in lt.get("timeline", lt.get("years", []))[:5]:
            if isinstance(year_data, dict):
                lines.append(f"  {year_data.get('period', year_data.get('year', ''))}: {str(year_data.get('theme', year_data.get('prediction', '')))[:80]}")
    return "\n".join(lines)

def _build_relocation(engine) -> str:
    return "Provide city name for relocation analysis"

def _build_baby_names(engine) -> str:
    bn = engine.get_baby_names()
    if isinstance(bn, dict):
        names = bn.get("names", bn.get("suggestions", []))
        if isinstance(names, list):
            return f"Suggested letters/names: {', '.join(str(n)[:20] for n in names[:10])}"
    return ""

def _build_sudarshana(engine) -> str:
    sc = engine.get_sudarshana()
    lines = []
    if isinstance(sc, dict):
        for ring, data in sc.items():
            if isinstance(data, dict):
                lines.append(f"  {ring}: {str(data.get('description', data.get('theme', '')))[:80]}")
            elif isinstance(data, list):
                lines.append(f"  {ring}: {len(data)} entries")
    return "\n".join(lines[:8])

def _build_nakshatra(engine) -> str:
    np = engine.get_nakshatra_profile()
    mp = np.get("moon_profile", {}) if isinstance(np, dict) else {}
    lines = []
    if isinstance(mp, dict):
        lines.append(f"Moon Nakshatra: {mp.get('nakshatra', '')} Pada {mp.get('pada', '')}")
        for key in ['personality', 'career', 'health', 'relationship']:
            val = mp.get(key, "")
            if val:
                lines.append(f"  {key}: {str(val)[:100]}")
    return "\n".join(lines)

def _build_yoga_timing(engine) -> str:
    yt = engine.get_yoga_timing()
    lines = []
    if isinstance(yt, list):
        for y in yt[:8]:
            if isinstance(y, dict):
                lines.append(f"  {y.get('yoga', y.get('name', ''))}: {y.get('activation', y.get('timing', y.get('period', '')))}")
    return "\n".join(lines)

def _build_lucky(engine) -> str:
    lines = []
    ln = _safe(lambda: engine.get_lucky_numbers())
    if isinstance(ln, dict):
        lines.append(f"Lucky numbers: {ln.get('lucky_numbers', ln.get('numbers', ''))}")
    dm = _safe(lambda: engine.get_dynamic_mantra())
    if isinstance(dm, dict):
        lines.append(f"Mantra now: {str(dm.get('mantra', ''))[:80]}")
    dr = _safe(lambda: engine.get_dynamic_remedies())
    if isinstance(dr, dict):
        lines.append(f"Current remedy: {str(dr.get('primary_remedy', dr.get('suggestion', '')))[:80]}")
    return "\n".join(lines)

def _build_bphs_advanced(engine) -> str:
    lines = []
    av = _safe(lambda: engine.get_avasthas())
    if isinstance(av, dict):
        lines.append(f"Avasthas: {len(av)} planets analyzed")
    vm = _safe(lambda: engine.get_vimshopaka())
    if isinstance(vm, dict):
        for p, data in list(vm.items())[:5]:
            if isinstance(data, dict):
                lines.append(f"  {p} vimshopaka: {data.get('score', data.get('total', ''))}")
    gy = _safe(lambda: engine.get_graha_yuddha())
    if isinstance(gy, dict) and gy.get("wars"):
        for w in gy["wars"][:3]:
            if isinstance(w, dict):
                lines.append(f"  War: {w.get('planet1', '')} vs {w.get('planet2', '')} — winner: {w.get('winner', '')}")
    ny = _safe(lambda: engine.get_nabhasa_yogas())
    if isinstance(ny, dict):
        found = ny.get("yogas", [])
        if isinstance(found, list) and found:
            names = [y.get("name", "") for y in found[:5] if isinstance(y, dict)]
            lines.append(f"  Nabhasa: {', '.join(names)}")
    pk = _safe(lambda: engine.get_pushkara())
    if isinstance(pk, dict) and pk.get("pushkara_planets"):
        lines.append(f"  Pushkara: {', '.join(str(p) for p in pk['pushkara_planets'][:5])}")
    nr = _safe(lambda: engine.get_natal_retrogrades())
    if isinstance(nr, dict):
        lines.append(f"  Natal retrogrades: {str(nr.get('summary', nr.get('retrogrades', '')))[:80]}")
    return "\n".join(lines)

def _build_spiritual(engine) -> str:
    lines = []
    sy = _safe(lambda: engine.get_sannyasa_yogas())
    if isinstance(sy, dict):
        yogas = sy.get("yogas", [])
        lines.append(f"Sannyasa yogas: {len(yogas)} found")
        for y in (yogas if isinstance(yogas, list) else [])[:3]:
            if isinstance(y, dict):
                lines.append(f"  {y.get('name', '')}: {str(y.get('description', ''))[:80]}")
    km = _safe(lambda: engine.get_karakamsa())
    if isinstance(km, dict):
        lines.append(f"Karakamsa: {km.get('purpose', km.get('indication', ''))}")
    return "\n".join(lines)

def _build_maraka(engine) -> str:
    m = engine.get_maraka()
    if isinstance(m, dict):
        planets = m.get("maraka_planets", [])
        return f"Maraka planets: {', '.join(str(p) for p in planets)}" if planets else "No strong maraka influence"
    return ""

def _build_argala(engine) -> str:
    lines = []
    ar = _safe(lambda: engine.get_argala())
    if isinstance(ar, dict):
        for house, data in list(ar.items())[:6]:
            if isinstance(data, dict):
                lines.append(f"  H{house}: {str(data.get('summary', data.get('argala', '')))[:80]}")
    sb = _safe(lambda: engine.get_sarvatobhadra())
    if isinstance(sb, dict):
        vedhas = sb.get("vedhas", [])
        if isinstance(vedhas, list) and vedhas:
            lines.append(f"Sarvatobhadra vedhas: {len(vedhas)} active")
    return "\n".join(lines)

def _build_tithi_pravesh(engine) -> str:
    tp = engine.get_tithi_pravesh()
    lines = []
    if isinstance(tp, dict):
        analysis = tp.get("analysis", {})
        if isinstance(analysis, dict):
            lines.append(f"Rating: {analysis.get('overall_rating', '')} (score {analysis.get('score', '')})")
        cv = tp.get("cross_validation", {})
        if isinstance(cv, dict):
            lines.append(f"Confidence: {cv.get('confidence', '')}")
    return "\n".join(lines)

def _build_chart_promise(engine, topic=None) -> str:
    if topic:
        cp = engine.get_chart_promise(topic)
    else:
        cp = engine.get_chart_promise()
    lines = []
    if isinstance(cp, dict):
        if 'events' in cp:
            for event, data in cp['events'].items():
                if isinstance(data, dict):
                    lines.append(f"  {event}: {data.get('summary', '')[:80]}")
        else:
            lines.append(f"  {cp.get('summary', '')}")
            supports = cp.get('supports', [])
            for s in (supports if isinstance(supports, list) else [])[:3]:
                text = s.get('text', str(s)) if isinstance(s, dict) else str(s)
                lines.append(f"    ✓ {text[:80]}")
    return "\n".join(lines)

def _build_period_query(engine) -> str:
    now = datetime.now()
    result = _safe(lambda: engine.get_period_analysis(3))
    lines = []
    if isinstance(result, dict):
        lines.append(f"Next 3 months: {str(result.get('summary', result.get('themes', '')))[:150]}")
    return "\n".join(lines)

def _build_manglik(engine) -> str:
    m = engine.check_manglik()
    if isinstance(m, dict):
        is_m = m.get("is_manglik", False)
        cancelled = m.get("is_cancelled", False)
        text = f"Manglik: {'Yes' if is_m else 'No'}"
        if cancelled:
            text += f" (Cancelled: {m.get('cancellation_reason', '')})"
        text += f"\nSeverity: {m.get('severity', m.get('type', ''))}"
        return text
    return ""

def _build_pratyantar(engine) -> str:
    pd = engine.get_pratyantar_dasha()
    lines = []
    if isinstance(pd, dict):
        current = pd.get("current", pd.get("pratyantar", ""))
        lines.append(f"Current: {current}")
        upcoming = pd.get("upcoming", pd.get("next", []))
        for u in (upcoming if isinstance(upcoming, list) else [])[:5]:
            if isinstance(u, dict):
                lines.append(f"  {u.get('lord', u.get('planet', ''))}: {str(u.get('start', ''))[:10]} to {str(u.get('end', ''))[:10]}")
    return "\n".join(lines)

def _build_timing_windows(engine, topic=None) -> str:
    if not topic:
        scan = _safe(lambda: engine.scan_all_predictions())
        if isinstance(scan, dict):
            events = scan.get("events", scan.get("predictions", []))
            lines = []
            for e in (events if isinstance(events, list) else [])[:6]:
                if isinstance(e, dict):
                    lines.append(f"  {e.get('event', '')}: {e.get('probability', '')}% — {str(e.get('window', ''))[:60]}")
            return "\n".join(lines)
        return ""
    result = engine.predict_event(topic)
    if isinstance(result, dict):
        window = result.get("window", result.get("best_window", {}))
        if isinstance(window, dict):
            return f"Best window: {window.get('start', '')} to {window.get('end', '')} ({window.get('strength', '')})"
        return str(result.get("summary", ""))[:150]
    return ""

def _build_arudha_padas(engine) -> str:
    result = _safe(lambda: engine.get_arudha_padas())
    lines = []
    if isinstance(result, dict):
        for pada, data in result.items():
            if isinstance(data, dict):
                lines.append(f"  {pada}: {data.get('sign', '')} H{data.get('house', '')} — {str(data.get('interpretation', ''))[:80]}")
            elif isinstance(data, str):
                lines.append(f"  {pada}: {data}")
    return "\n".join(lines[:12])

def _build_av_transits(engine) -> str:
    result = _safe(lambda: engine.get_ashtakavarga_transits())
    lines = []
    if isinstance(result, dict):
        for planet, data in list(result.items())[:9]:
            if isinstance(data, dict):
                bindus = data.get('bindus', data.get('score', ''))
                lines.append(f"  {planet} transit: {bindus} bindus — {'favorable' if isinstance(bindus, (int,float)) and bindus >= 4 else 'weak'}")
    return "\n".join(lines)

def _build_future_transits(engine) -> str:
    result = _safe(lambda: engine.get_future_transits())
    lines = []
    events = result.get("events", result.get("transits", [])) if isinstance(result, dict) else []
    for e in (events if isinstance(events, list) else [])[:8]:
        if isinstance(e, dict):
            lines.append(f"  {e.get('date', '')}: {e.get('planet', '')} {e.get('event', e.get('description', '')[:80])}")
    return "\n".join(lines)

def _build_transit_aspects(engine) -> str:
    result = _safe(lambda: engine.get_transit_aspects())
    lines = []
    aspects = result.get("aspects", result) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    for a in (aspects if isinstance(aspects, list) else [])[:8]:
        if isinstance(a, dict):
            lines.append(f"  {a.get('transit_planet', '')} {a.get('aspect', '')} natal {a.get('natal_planet', '')} — {str(a.get('effect', ''))[:60]}")
    return "\n".join(lines)

def _build_name_numerology(engine) -> str:
    result = _safe(lambda: engine.get_name_numerology())
    if isinstance(result, dict):
        return f"Name number: {result.get('name_number', '')}\nCompatible: {result.get('compatible', result.get('favorable', ''))}"
    return ""

def _build_hora(engine) -> str:
    lines = []
    h = _safe(lambda: engine.get_current_hora_info())
    if isinstance(h, dict):
        lines.append(f"Current hora: {h.get('hora_lord', h.get('planet', ''))}")
        lines.append(f"Best for: {h.get('activities', h.get('best_for', ''))}")
    nh = _safe(lambda: engine.get_next_hora())
    if isinstance(nh, dict):
        lines.append(f"Next hora: {nh.get('hora_lord', nh.get('planet', ''))} at {nh.get('start_time', '')}")
    hn = _safe(lambda: engine.get_hora_notification())
    if isinstance(hn, dict):
        lines.append(f"Notification: {str(hn.get('message', hn.get('notification', '')))[:80]}")
    return "\n".join(lines)

def _build_panchanga(engine) -> str:
    p = _safe(lambda: engine.get_panchanga())
    lines = []
    if isinstance(p, dict):
        for key in ['tithi', 'nakshatra', 'yoga', 'karana', 'vara']:
            val = p.get(key, {})
            if isinstance(val, dict):
                lines.append(f"  {key.capitalize()}: {val.get('name', val.get('value', ''))}")
            elif val:
                lines.append(f"  {key.capitalize()}: {val}")
    return "\n".join(lines)

def _build_dasha_sandhi(engine) -> str:
    result = _safe(lambda: engine.get_dasha_sandhi())
    if isinstance(result, dict):
        sandhi = result.get("sandhi_periods", result.get("transitions", []))
        lines = []
        for s in (sandhi if isinstance(sandhi, list) else [])[:5]:
            if isinstance(s, dict):
                lines.append(f"  {s.get('from', '')} → {s.get('to', '')}: {str(s.get('date', ''))[:10]} — {str(s.get('effect', ''))[:60]}")
        if not lines:
            lines.append("No critical dasha transitions upcoming")
        return "\n".join(lines)
    return ""

def _build_rashi_drishti(engine) -> str:
    result = _safe(lambda: engine.get_rashi_drishti())
    lines = []
    if isinstance(result, dict):
        for sign, data in list(result.items())[:12]:
            if isinstance(data, dict):
                aspected_by = data.get('aspected_by', [])
                if aspected_by:
                    lines.append(f"  {sign}: aspected by {', '.join(str(a) for a in aspected_by[:4])}")
    return "\n".join(lines)

def _build_av_sodhana(engine) -> str:
    result = _safe(lambda: engine.get_av_sodhana())
    if isinstance(result, dict):
        lines = []
        for planet, data in list(result.items())[:9]:
            if isinstance(data, dict):
                lines.append(f"  {planet}: {data.get('sodhana_score', data.get('score', ''))}")
        return "\n".join(lines)
    return ""

def _build_prastara(engine) -> str:
    result = _safe(lambda: engine.get_prastara_av())
    if isinstance(result, dict):
        lines = [f"Total rows: {len(result)}"]
        for planet, grid in list(result.items())[:3]:
            if isinstance(grid, (list, dict)):
                lines.append(f"  {planet}: {str(grid)[:100]}")
        return "\n".join(lines)
    return ""

def _build_shodhya_pinda(engine) -> str:
    result = _safe(lambda: engine.get_shodhya_pinda())
    lines = []
    if isinstance(result, dict):
        for planet, data in result.items():
            if isinstance(data, dict):
                lines.append(f"  {planet}: rashi={data.get('rashi_pinda', '')} graha={data.get('graha_pinda', '')} shodhya={data.get('shodhya_pinda', '')}")
    return "\n".join(lines[:9])

def _build_bhava_strengths(engine) -> str:
    result = _safe(lambda: engine.get_bhava_strengths())
    lines = []
    if isinstance(result, dict):
        for house, data in sorted(result.items(), key=lambda x: str(x[0])):
            if isinstance(data, dict):
                lines.append(f"  H{house}: {data.get('strength', data.get('score', ''))}")
    return "\n".join(lines[:12])

def _build_ishta_kashta(engine) -> str:
    result = _safe(lambda: engine.get_ishta_kashta())
    lines = []
    if isinstance(result, dict):
        for planet, data in result.items():
            if isinstance(data, dict):
                ishta = data.get('ishta', 0)
                kashta = data.get('kashta', 0)
                net = ishta - kashta if isinstance(ishta, (int,float)) and isinstance(kashta, (int,float)) else 0
                lines.append(f"  {planet}: ishta={ishta} kashta={kashta} net={'positive' if net > 0 else 'negative'}")
    return "\n".join(lines[:9])

def _build_gemstones(engine) -> str:
    result = _safe(lambda: engine.get_gemstone_recommendations())
    lines = []
    if isinstance(result, dict):
        gems = result.get("recommendations", result.get("gemstones", []))
        for g in (gems if isinstance(gems, list) else [])[:5]:
            if isinstance(g, dict):
                lines.append(f"  {g.get('gemstone', '')}: for {g.get('planet', '')} — {g.get('finger', '')} finger, {g.get('day', '')} — {str(g.get('reason', ''))[:60]}")
    return "\n".join(lines)

def _build_synastry(engine) -> str:
    return "Synastry requires partner birth data"

def _build_composite(engine) -> str:
    return "Composite chart requires partner birth data"

def _build_location(engine) -> str:
    result = _safe(lambda: engine.analyze_location())
    if isinstance(result, dict):
        return f"Current location analysis: {str(result.get('summary', result.get('analysis', '')))[:200]}"
    return "Provide target city for location analysis"

def _build_raja_yogas(engine) -> str:
    result = _safe(lambda: engine.get_raja_yogas())
    lines = []
    yogas = result.get("yogas", result) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    for y in (yogas if isinstance(yogas, list) else [])[:8]:
        if isinstance(y, dict):
            lines.append(f"  {y.get('name', '')}: {str(y.get('description', y.get('effect', '')))[:80]}")
    return "\n".join(lines) if lines else "No raja yogas identified"

def _build_dhana_yogas(engine) -> str:
    result = _safe(lambda: engine.get_dhana_yogas())
    lines = []
    yogas = result.get("yogas", result) if isinstance(result, dict) else (result if isinstance(result, list) else [])
    for y in (yogas if isinstance(yogas, list) else [])[:8]:
        if isinstance(y, dict):
            lines.append(f"  {y.get('name', '')}: {str(y.get('description', y.get('effect', '')))[:80]}")
    return "\n".join(lines) if lines else "No dhana yogas identified"

def _build_daridra_yogas(engine) -> str:
    result = _safe(lambda: engine.get_daridra_yogas())
    lines = []
    for y in (result if isinstance(result, list) else [])[:8]:
        if isinstance(y, dict):
            lines.append(f"  {y.get('name', y.get('yoga', ''))}: {str(y.get('description', y.get('effect', '')))[:80]}")
    return "\n".join(lines) if lines else "No daridra yogas found"

def _build_female(engine) -> str:
    result = _safe(lambda: engine.get_female_horoscopy())
    lines = []
    for r in (result if isinstance(result, list) else [])[:6]:
        if isinstance(r, dict):
            lines.append(f"  {r.get('rule', r.get('name', ''))}: {str(r.get('description', r.get('effect', '')))[:80]}")
    return "\n".join(lines) if lines else "No female-specific rules triggered"

def _build_longevity(engine) -> str:
    result = _safe(lambda: engine.get_longevity())
    if isinstance(result, dict):
        category = result.get('longevity_category', result.get('category', ''))
        years = result.get('estimated_years', result.get('years', ''))
        method = result.get('method', '3-pair')
        lines = [f"Category: {category}"]
        if years:
            lines.append(f"Estimate: {years}")
        lines.append(f"Method: {method}")
        pairs = result.get('pairs', [])
        for p in (pairs if isinstance(pairs, list) else [])[:3]:
            if isinstance(p, dict):
                lines.append(f"  Pair: {p.get('planet1', '')} + {p.get('planet2', '')} = {p.get('result', '')}")
        return "\n".join(lines)
    return ""

def _build_dasha_psych(engine) -> str:
    result = _safe(lambda: engine.get_dasha_psychology())
    if isinstance(result, dict):
        state = result.get('psychological_state', result.get('state', ''))
        lord = result.get('dasha_lord', result.get('planet', ''))
        tone = result.get('emotional_tone', '')
        lines = [f"Current dasha lord: {lord}"]
        if state:
            lines.append(f"Psychological state: {str(state)[:120]}")
        if tone:
            lines.append(f"Emotional tone: {tone}")
        return "\n".join(lines)
    return ""

def _build_dasha_interp(engine) -> str:
    result = _safe(lambda: engine.get_dasha_interpretation())
    if isinstance(result, dict):
        interp = result.get('interpretation', result.get('effect', ''))
        lord = result.get('dasha_lord', result.get('planet', ''))
        houses = result.get('houses_ruled', result.get('houses', []))
        themes = result.get('themes', [])
        lines = [f"Dasha lord: {lord}"]
        if houses:
            lines.append(f"Rules: H{', H'.join(str(h) for h in houses if isinstance(h, int))}")
        if themes:
            lines.append(f"Themes: {', '.join(str(t) for t in themes[:5])}")
        if interp:
            lines.append(f"Effect: {str(interp)[:150]}")
        return "\n".join(lines)
    return ""

def _build_special_lagnas(engine) -> str:
    result = _safe(lambda: engine.get_special_lagnas())
    lines = []
    if isinstance(result, dict):
        for lagna_name in ['hora_lagna', 'ghati_lagna']:
            d = result.get(lagna_name, {})
            if isinstance(d, dict):
                lines.append(f"  {lagna_name.replace('_', ' ').title()}: {d.get('sign', '')} — {str(d.get('effect', d.get('interpretation', '')))[:80]}")
    return "\n".join(lines)

def _build_jaimini_complete(engine) -> str:
    result = _safe(lambda: engine.get_complete_jaimini())
    lines = []
    if isinstance(result, dict):
        # Arudha Padas
        padas = result.get('arudha_padas', {})
        for key in ['A1', 'A7', 'A10', 'A12']:
            p = padas.get(key, {})
            if isinstance(p, dict):
                lines.append(f"  {p.get('name', key)}: {p.get('rashi', '')} H{p.get('house', '')}")
        # Swamsa
        sw = result.get('swamsa', {})
        if isinstance(sw, dict) and sw.get('swamsa_sign'):
            lines.append(f"  Swamsa: {sw['swamsa_sign']} — {sw.get('soul_purpose', '')}")
        # Jaimini yogas
        jy = result.get('jaimini_yogas', [])
        for y in (jy if isinstance(jy, list) else [])[:3]:
            if isinstance(y, dict):
                lines.append(f"  {y.get('name', '')}: {str(y.get('description', ''))[:60]}")
    return "\n".join(lines)

def _build_upapada(engine) -> str:
    result = _safe(lambda: engine.get_upapada())
    if isinstance(result, dict):
        lines = [
            f"Upapada: {result.get('upapada_sign', '')} H{result.get('upapada_house', '')}",
            f"UL Lord: {result.get('upapada_lord', '')} in H{result.get('upapada_lord_house', '')}",
            f"Spouse: {result.get('spouse_indication', '')}",
            f"Marriage: {result.get('marriage_longevity', '')}",
        ]
        return "\n".join(lines)
    return ""

def _build_muhurta_rules(engine) -> str:
    lines = []
    for event in ['marriage', 'business_start', 'travel', 'education_start']:
        result = _safe(lambda e=event: engine.get_muhurta_rules(e))
        if isinstance(result, dict):
            rules = result.get('rules', {})
            special = rules.get('special', '') if isinstance(rules, dict) else ''
            lines.append(f"  {event}: {special[:80]}")
    return "\n".join(lines)

# ═══ NEW BPHS SECTIONS ═══
def _build_d60(engine) -> str:
    r = _safe(lambda: engine.get_d60_interpretation())
    return "\n".join(f"  {p}: {d.get('name','')} — {d.get('past_life','')[:80]}" for p, d in (r if isinstance(r, dict) else {}).items())

def _build_remaining_vargas(engine) -> str:
    r = _safe(lambda: engine.get_remaining_vargas())
    lines = []
    for div, data in (r if isinstance(r, dict) else {}).items():
        if isinstance(data, dict):
            lines.append(f"  {div} ({data.get('name','')}): {data.get('theme','')} | {', '.join(data.get('key_planets', []))}")
    return "\n".join(lines)

def _build_mrityu_bhaga_sec(engine) -> str:
    r = _safe(lambda: engine.get_mrityu_bhaga())
    if isinstance(r, list) and r:
        return "\n".join(f"  {m.get('planet','')}: {m.get('degree','')}° (MB={m.get('mrityu_bhaga','')}) — {m.get('severity','')}" for m in r)
    return "No planets at Mrityu Bhaga"

def _build_bhrigu_bindu_sec(engine) -> str:
    r = _safe(lambda: engine.get_bhrigu_bindu())
    return r.get('interpretation', '') if isinstance(r, dict) else ""

def _build_pada_archetypes(engine) -> str:
    r = _safe(lambda: engine.get_pada_archetypes())
    lines = []
    for p, d in (r if isinstance(r, dict) else {}).items():
        if isinstance(d, dict):
            lines.append(f"  {p}: {d.get('nakshatra','')} P{d.get('pada','')} → {d.get('navamsa_sign','')} ({d.get('nature','')})")
    return "\n".join(lines)

def _build_pancha_pakshi_sec(engine) -> str:
    r = _safe(lambda: engine.get_pancha_pakshi())
    if isinstance(r, dict):
        return f"Bird: {r.get('birth_bird','')} | Activity: {r.get('current_activity','')} | {r.get('advice','')}"
    return ""

def _build_graha_shanti_sec(engine) -> str:
    r = _safe(lambda: engine.get_graha_shanti())
    lines = []
    for planet, data in (r if isinstance(r, dict) else {}).items():
        if isinstance(data, dict):
            lines.append(f"  {planet}: {data.get('gemstone','')} ({data.get('weight_min_ct','')}ct {data.get('metal','')}) | {data.get('day','')} | {data.get('mantra','')[:40]}... ×{data.get('count','')}")
    return "\n".join(lines)

SECTION_MAP['d60_past_life'] = ('D60 PAST LIFE', _build_d60)
SECTION_MAP['remaining_vargas'] = ('REMAINING DIVISIONAL CHARTS', _build_remaining_vargas)
SECTION_MAP['mrityu_bhaga'] = ('MRITYU BHAGA', _build_mrityu_bhaga_sec)
SECTION_MAP['bhrigu_bindu'] = ('BHRIGU BINDU', _build_bhrigu_bindu_sec)
SECTION_MAP['pada_archetypes'] = ('108 PADA ARCHETYPES', _build_pada_archetypes)
SECTION_MAP['pancha_pakshi'] = ('PANCHA PAKSHI', _build_pancha_pakshi_sec)
SECTION_MAP['graha_shanti'] = ('GRAHA SHANTI (COMPLETE)', _build_graha_shanti_sec)
