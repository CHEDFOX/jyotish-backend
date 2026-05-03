"""CHINESE SECTION BUILDERS — raw data for each Chinese section."""

from datetime import datetime


def _get_bazi(engine):
    from .bazi import BaZiChart
    return BaZiChart(engine.birth_local)


def build_base_chart(engine) -> str:
    from .chart_builder import build_chinese_chart
    return build_chinese_chart(engine)


def build_four_pillars(engine) -> str:
    bc = _get_bazi(engine)
    pillars = bc.get_four_pillars()
    lines = []
    for p in ['year', 'month', 'day', 'hour']:
        pi = pillars[p]
        s = pi['stem']
        b = pi['branch']
        lines.append(f"{p.capitalize():6s}: {s['full']:12s} / {b['animal']:8s} ({b['full']})")
        if pi.get('hidden_stems'):
            lines.append(f"        Hidden: {', '.join(pi['hidden_stems'])}")
    return "\n".join(lines)


def build_day_master(engine) -> str:
    bc = _get_bazi(engine)
    dm = bc.get_day_master()
    return f"{dm['full_name']} ({dm['chinese']})\n{dm['description']}"


def build_elements(engine) -> str:
    bc = _get_bazi(engine)
    e = bc.get_element_balance()
    c = e['counts']
    lines = [
        f"Wood={c['Wood']} Fire={c['Fire']} Earth={c['Earth']} Metal={c['Metal']} Water={c['Water']}",
        f"Day Master: {e['day_master_element']} ({e['day_master_strength']})",
        f"Dominant: {e['dominant_element']} | Weakest: {e['weakest_element']}",
        f"Favorable: {e['favorable_element']} | Lucky color: {e['lucky_color']} | Direction: {e['lucky_direction']}",
    ]
    return "\n".join(lines)


def build_ten_gods(engine) -> str:
    bc = _get_bazi(engine)
    tg = bc.get_ten_gods()
    lines = []
    for p in ['year', 'month', 'day', 'hour']:
        lines.append(f"{p.capitalize():6s}: {tg.get(p, '')}")
    return "\n".join(lines)


def build_branch_interactions(engine) -> str:
    bc = _get_bazi(engine)
    from .interactions import BranchInteractions
    bi = BranchInteractions(bc).analyze_all()
    lines = []
    for clash in bi.get('clashes', []):
        lines.append(f"CLASH: {clash['branches']} ({clash['pillars'][0]}-{clash['pillars'][1]}) — {clash['meaning']}")
    for harm in bi.get('harmonies', []):
        lines.append(f"HARMONY: {harm['branches']} → {harm['transforms_to']} — {harm['meaning']}")
    for th in bi.get('three_harmonies', []):
        lines.append(f"THREE HARMONY: {th['branches']} → {th['element']} ({th['completeness']})")
    for pun in bi.get('punishments', []):
        lines.append(f"PUNISHMENT: {pun['branches']} — {pun['punishment']}: {pun['meaning']}")
    for h in bi.get('harms', []):
        lines.append(f"HARM: {h['branches']} — {h['meaning']}")
    if not lines:
        lines.append("No major branch interactions")
    summary = bi.get('summary', {}).get('overall', '')
    if summary:
        lines.append(f"Overall: {summary}")
    return "\n".join(lines)


def build_stem_interactions(engine) -> str:
    bc = _get_bazi(engine)
    from .interactions import StemInteractions
    si = StemInteractions(bc).analyze_all_stems()
    lines = []
    for sc in si.get('stem_clashes', []):
        lines.append(f"STEM CLASH: {sc['stems']} ({sc['pillars'][0]}-{sc['pillars'][1]}) — {sc['meaning']}")
    for combo in si.get('stem_combinations', []):
        lines.append(f"STEM COMBO: {combo['stems']} → {combo['transforms_to']} — {combo['meaning']}")
    eb = si.get('empty_branches', {})
    if eb.get('has_void'):
        for a in eb.get('affected_pillars', []):
            lines.append(f"VOID: {a['pillar']} pillar ({a['animal']}) — {a['meaning']}")
    if not lines:
        lines.append("No stem clashes or combinations")
    return "\n".join(lines)


def build_symbolic_stars(engine) -> str:
    bc = _get_bazi(engine)
    from .stars import SymbolicStars
    ss = SymbolicStars(bc).analyze_all_stars()
    lines = []
    for name, data in ss.items():
        if data.get('present'):
            locs = ", ".join(l.get('pillar', '') for l in data.get('locations', []))
            lines.append(f"★ {data.get('star', name)}: {locs} — {data.get('interpretation', '')[:80]}")
    absent = [data.get('star', name) for name, data in ss.items() if not data.get('present')]
    if absent:
        lines.append(f"Not present: {', '.join(absent)}")
    return "\n".join(lines)


def build_luck_periods(engine, extras: dict = None) -> str:
    bc = _get_bazi(engine)
    gender = (extras or {}).get('gender', 'male')
    periods = bc.get_luck_periods(8, gender)
    lines = [f"Direction: {'forward' if gender else 'forward'} ({gender})"]
    for p in periods:
        lines.append(f"Age {p['start_age']:2d}-{p['end_age']:2d}: {p['element']:14s} {p['animal']:8s} ({p['pillar']})")
    return "\n".join(lines)


def build_annual_luck(engine, year: int = None) -> str:
    bc = _get_bazi(engine)
    from .stars import AnnualLuck
    al = AnnualLuck(bc)
    if year:
        r = al.analyze_year(year)
        lines = [f"{year}: {r['element']} {r['animal']} — {r['outlook']} (score {r['score']})"]
        lines.append(f"Relation: {r['element_relation']}")
        if r.get('clashes'):
            lines.append(f"Clashes: {', '.join(r['clashes'])}")
        if r.get('harmonies'):
            lines.append(f"Harmonies: {', '.join(r['harmonies'])}")
        return "\n".join(lines)
    else:
        forecast = al.forecast_years(5)
        lines = []
        for r in forecast:
            lines.append(f"{r['year']}: {r['element']:5s} {r['animal']:8s} — {r['outlook']:12s} (score {r['score']})")
        return "\n".join(lines)


def build_compatibility(engine) -> str:
    return "Compatibility requires partner data"


def build_empty_branches(engine) -> str:
    bc = _get_bazi(engine)
    from .interactions import StemInteractions
    si = StemInteractions(bc)
    eb = si.check_empty_branches()
    lines = [f"Empty branches: {', '.join(eb.get('empty_branches', []))}"]
    for a in eb.get('affected_pillars', []):
        lines.append(f"  {a['pillar']}: {a['meaning']}")
    lines.append(eb.get('interpretation', ''))
    return "\n".join(lines)


SECTION_MAP = {
    'four_pillars': ('FOUR PILLARS', build_four_pillars),
    'day_master': ('DAY MASTER', build_day_master),
    'elements': ('FIVE ELEMENTS', build_elements),
    'ten_gods': ('TEN GODS', build_ten_gods),
    'branch_interactions': ('BRANCH INTERACTIONS', build_branch_interactions),
    'stem_interactions': ('STEM INTERACTIONS', build_stem_interactions),
    'symbolic_stars': ('SYMBOLIC STARS', build_symbolic_stars),
    'luck_periods': ('LUCK PERIODS (DA YUN)', build_luck_periods),
    'annual_luck': ('ANNUAL LUCK', build_annual_luck),
    'compatibility': ('COMPATIBILITY', build_compatibility),
    'empty_branches': ('EMPTY BRANCHES', build_empty_branches),
    'na_yin': ('NA YIN (纳音)', lambda e: _build_na_yin(e)),
    'life_stages': ('12 LIFE STAGES (长生)', lambda e: _build_life_stages(e)),
    'yong_shen': ('YONG SHEN (用神)', lambda e: _build_yong_shen(e)),
    'extended_stars': ('EXTENDED STARS (30+)', lambda e: _build_ext_stars(e)),
    'fan_fu_yin': ('FAN YIN / FU YIN', lambda e: _build_fan_fu(e)),
}


def _build_na_yin(engine) -> str:
    result = engine.get_chinese_na_yin()
    lines = []
    for p in ['year', 'month', 'day', 'hour']:
        d = result.get(p, {})
        lines.append(f"  {p.capitalize()}: {d.get('na_yin', '')} ({d.get('element', '')})")
    return "\n".join(lines)

def _build_life_stages(engine) -> str:
    result = engine.get_chinese_life_stages()
    lines = [f"Day Stem: {result.get('day_stem', '')} ({result.get('direction', '')})"]
    for name, data in list(result.get('stages', {}).items())[:12]:
        lines.append(f"  {data.get('stage', '')}: {data.get('branch', '')} — {data.get('meaning', '')[:60]}")
    return "\n".join(lines)

def _build_yong_shen(engine) -> str:
    result = engine.get_chinese_yong_shen()
    lines = [
        f"Yong Shen (用神): {result.get('yong_shen', '')} — {result.get('yong_meaning', '')}",
        f"Xi Shen (喜神): {result.get('xi_shen', '')} — {result.get('xi_meaning', '')}",
        f"Ji Shen (忌神): {result.get('ji_shen', '')} — {result.get('ji_meaning', '')}",
    ]
    return "\n".join(lines)

def _build_ext_stars(engine) -> str:
    result = engine.get_chinese_extended_stars()
    stars = result.get('stars', {})
    lines = []
    for name, data in stars.items():
        if data.get('present'):
            lines.append(f"  ★ {data.get('name', '')}: {data.get('meaning', '')[:60]}")
    absent = [data.get('name', '') for data in stars.values() if not data.get('present')]
    if absent:
        lines.append(f"  Not present: {', '.join(absent[:5])}")
    return "\n".join(lines)

def _build_fan_fu(engine) -> str:
    result = engine.get_chinese_fan_fu_yin()
    lines = []
    for fy in result.get('fan_yin', []):
        lines.append(f"  Fan Yin: {fy.get('pillars', [])} — {fy.get('meaning', '')}")
    for fu in result.get('fu_yin', []):
        lines.append(f"  Fu Yin: {fu.get('pillars', [])} — {fu.get('meaning', '')}")
    return "\n".join(lines) if lines else "No Fan Yin or Fu Yin patterns"


def build_sections(engine, section_names: list, topic: str = None, extras: dict = None) -> str:
    extras = extras or {}
    parts = []
    for name in section_names:
        entry = SECTION_MAP.get(name)
        if not entry:
            continue
        label, builder = entry
        try:
            if name == 'luck_periods':
                text = builder(engine, extras)
            elif name == 'annual_luck':
                text = builder(engine)
            else:
                text = builder(engine)
            if text and text.strip():
                parts.append(f"{label}:\n{text}")
        except Exception:
            continue
    return "\n\n".join(parts)

# ═══ NEW CHINESE SECTIONS ═══
def _build_dayun_onset(engine) -> str:
    r = engine.get_chinese_dayun_onset()
    return f"Da Yun onset: age {r.get('onset_age','')} ({r.get('onset_years','')} years {r.get('onset_months','')} months) | Direction: {r.get('direction','')}" if isinstance(r, dict) else ""

def _build_xiao_yun(engine) -> str:
    r = engine.get_chinese_xiao_yun()
    return "\n".join(f"  Age {p.get('age','')}: {p.get('animal','')} ({p.get('element','')})" for p in (r if isinstance(r, list) else []))

def _build_pillar_overlay(engine) -> str:
    r = engine.get_chinese_pillar_overlay()
    if isinstance(r, dict):
        lines = [f"Month: {r.get('current_month','')} — {r.get('month_outlook','')}",
                 f"Day: {r.get('current_day','')} — {r.get('day_outlook','')}"]
        if r.get('month_clashes'): lines.append(f"Month clashes: {', '.join(r['month_clashes'])}")
        if r.get('day_harmonies'): lines.append(f"Day harmonies: {', '.join(r['day_harmonies'])}")
        return "\n".join(lines)
    return ""

def _build_hidden_strength(engine) -> str:
    r = engine.get_chinese_hidden_strength()
    lines = []
    for p, stems in (r if isinstance(r, dict) else {}).items():
        if isinstance(stems, list):
            parts = [f"{s.get('stem','')}({s.get('strength_pct','')}%)" for s in stems]
            lines.append(f"  {p.capitalize()}: {', '.join(parts)}")
    return "\n".join(lines)

def _build_gods_matrix(engine) -> str:
    r = engine.get_chinese_gods_matrix()
    return "\n".join(f"  {i.get('god1','')} ↔ {i.get('god2','')}: {i.get('interaction','')}" for i in (r if isinstance(r, list) else []))

def _build_date_selection(engine) -> str:
    r = engine.get_chinese_date_selection()
    lines = []
    for d in (r if isinstance(r, list) else [])[:5]:
        if isinstance(d, dict):
            lines.append(f"  {d.get('date','')} ({d.get('day','')}) {d.get('animal','')} {d.get('element','')}: score {d.get('score','')}")
    return "\n".join(lines) if lines else "No dates analyzed"

def _build_feng_shui(engine) -> str:
    r = engine.get_chinese_feng_shui()
    if isinstance(r, dict):
        return f"Group: {r.get('group','')} | Best sleep: {r.get('best_sleeping','')} | Best work: {r.get('best_working','')} | Avoid: {r.get('avoid','')}"
    return ""

def _build_chinese_medical(engine) -> str:
    r = engine.get_chinese_medical()
    lines = []
    if isinstance(r, dict):
        for v in r.get('vulnerabilities', []):
            if isinstance(v, dict):
                lines.append(f"  {v.get('risk','')} | Remedy: {v.get('remedy','')[:60]}")
        if r.get('dietary_advice'):
            lines.append(f"Diet: {r['dietary_advice']}")
    return "\n".join(lines)

def _build_zi_wei(engine) -> str:
    r = engine.get_zi_wei_chart()
    lines = []
    if isinstance(r, dict):
        for key in ['life_palace', 'career_palace', 'wealth_palace', 'spouse_palace']:
            p = r.get(key, {})
            if isinstance(p, dict):
                stars = ', '.join(p.get('stars', []))
                lines.append(f"  {key.replace('_',' ').title()}: {stars if stars else 'empty'}")
        tf = r.get('transformations', {})
        for name, data in (tf if isinstance(tf, dict) else {}).items():
            if isinstance(data, dict):
                lines.append(f"  {name}: {data.get('star','')} in {data.get('palace','')}")
    return "\n".join(lines)

SECTION_MAP['dayun_onset'] = ('DA YUN ONSET AGE', _build_dayun_onset)
SECTION_MAP['xiao_yun'] = ('XIAO YUN (SMALL LUCK)', _build_xiao_yun)
SECTION_MAP['pillar_overlay'] = ('CURRENT PILLAR OVERLAY', _build_pillar_overlay)
SECTION_MAP['hidden_strength'] = ('HIDDEN STEMS (STRENGTH %)', _build_hidden_strength)
SECTION_MAP['gods_matrix'] = ('10 GODS INTERACTION', _build_gods_matrix)
SECTION_MAP['date_selection'] = ('DATE SELECTION', _build_date_selection)
SECTION_MAP['feng_shui'] = ('FENG SHUI DIRECTIONS', _build_feng_shui)
SECTION_MAP['chinese_medical'] = ('CHINESE MEDICAL (TCM)', _build_chinese_medical)
SECTION_MAP['zi_wei'] = ('ZI WEI DOU SHU', _build_zi_wei)
