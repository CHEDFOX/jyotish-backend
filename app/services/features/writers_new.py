"""
New feature writers + fixed planet-strength.
Imported by writers.py — keeps existing code untouched.
"""
from .education import (PLANET_EDUCATION, HOUSE_ED, PLANET_IN_HOUSE_ED, DIGNITY_ED,
    get_planet_edu, get_house_ed, get_planet_in_house, get_dignity_ed)


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════
# FIXED: Planet Strength (was crashing — 'str' has no 'get')
# ═══════════════════════════════════════════════════════════════

PLANET_DOMINANCE = {
    'Sun': 'Your identity leads. Authority comes naturally.',
    'Moon': 'Your emotions lead. Intuition is your sharpest tool.',
    'Mars': 'Your body leads. Action before thought, and usually right.',
    'Mercury': 'Your mind leads. Words are your weapon and your gift.',
    'Jupiter': 'Your wisdom leads. You expand whatever you touch.',
    'Venus': 'Your taste leads. Beauty and harmony are non-negotiable.',
    'Saturn': 'Your discipline leads. You build what lasts.',
    'Rahu': 'Your ambition leads. The unconventional path is yours.',
    'Ketu': 'Your intuition leads. You know without being taught.',
}

def write_planet_strength(engine, language='en'):
    """Planet Power — educational, expandable, multi-engine."""
    sb_complete = _safe(engine.get_shadbala_complete, {}) or {}
    sb_planets = sb_complete.get('planets', {})

    dignity_data = _safe(engine.get_planetary_dignity, {}) or {}
    dignity_planets = dignity_data.get('planets', {})

    planet_dict = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}

    planet_order = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
    planets_out = []
    strongest_name = sb_complete.get('strongest', '')

    for name in planet_order:
        sb = sb_planets.get(name, {})
        dg = dignity_planets.get(name, {})
        pl = planet_dict.get(name, {})
        edu = get_planet_edu(name, language)

        pct = sb.get('percentage', 50)
        grade = sb.get('grade', 'Average')
        house = dg.get('house', pl.get('house', 0)) if isinstance(dg, dict) else 0
        dignity_type = dg.get('dignity_type', 'neutral_sign') if isinstance(dg, dict) else 'neutral_sign'
        comb = dg.get('combustion', {}) if isinstance(dg, dict) else {}
        is_combust = comb.get('is_combust', False) if isinstance(comb, dict) else False

        if is_combust:
            status = 'COMBUST'
        elif grade == 'Strong':
            status = 'STRONG'
        elif grade == 'Weak':
            status = 'WEAK'
        else:
            status = grade.upper() if isinstance(grade, str) else 'AVERAGE'

        mods = []
        if is_combust:
            mods.append('Combust')
        if isinstance(pl, dict) and (pl.get('is_retrograde') or pl.get('retrograde')):
            mods.append('Retrograde')

        house_key = f"{name}_{house}"
        house_text = get_planet_in_house(name, house, language)
        house_info = get_house_ed(house, language)

        dignity_ed = get_dignity_ed(dignity_type, language)
        if is_combust:
            dignity_ed = ('Combust', 'Too close to the Sun — its light is absorbed. Significations become hidden. The effect is temporary.')

        strength_text = edu.get('strong', '') if pct > 55 else edu.get('weak', '')

        planets_out.append({
            'name': name,
            'current_strength': pct,
            'status': status,
            'house': house,
            'house_name': house_info[1] if house_info else '',
            'dignity_label': dignity_ed[0] if dignity_ed else '',
            'dignity_text': dignity_ed[1] if dignity_ed else '',
            'significance': edu.get('significance', ''),
            'nature': edu.get('nature', ''),
            'house_text': house_text,
            'strength_text': strength_text,
            'day': edu.get('day', ''),
            'gem': edu.get('gem', ''),
            'color': edu.get('color', ''),
            'modifiers': mods,
            'domain': edu.get('significance', ''),
        })

    if strongest_name:
        anchor = f'{strongest_name}.'
        line = PLANET_DOMINANCE.get(strongest_name, f'{strongest_name} leads your chart.')
        hold = f'Lean into {strongest_name} energy this period.'
    else:
        anchor = 'Balanced.'
        line = 'No single planet dominates. Your chart distributes power evenly.'
        hold = 'Trust the whole, not the parts.'

    return {
        'anchor': anchor, 'line': line, 'hold': hold,
        'math': {
            'planets': planets_out,
            'overall_energy': sb_complete.get('summary', ''),
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Active Yogas
# ═══════════════════════════════════════════════════════════════

def write_active_yogas(engine, language='en'):
    yogas_raw = _safe(engine.get_yogas, {}) or {}
    yogas_dict = yogas_raw.get('yogas', {})

    # Flatten nested categories: {mahapurusha: [...], raja: [...], ...}
    combined = []
    seen = set()
    if isinstance(yogas_dict, dict):
        for category, yoga_list in yogas_dict.items():
            if isinstance(yoga_list, list):
                for y in yoga_list:
                    if isinstance(y, dict):
                        name = y.get('name', '')
                        if name and name not in seen:
                            seen.add(name)
                            combined.append({
                                'name': name,
                                'type': y.get('type', category.title()),
                                'description': y.get('description', ''),
                                'effects': y.get('effects', ''),
                                'planets': y.get('planets', [y.get('planet', '')] if y.get('planet') else []),
                                'strength': y.get('strength', 'Moderate'),
                                'is_negative': y.get('is_negative', False),
                                'house': y.get('house', ''),
                            })
    elif isinstance(yogas_dict, list):
        for y in yogas_dict:
            if isinstance(y, dict):
                name = y.get('name', '')
                if name and name not in seen:
                    seen.add(name)
                    combined.append(y)

    # Separate positive and negative
    positive = [c for c in combined if not c.get('is_negative')]
    negative = [c for c in combined if c.get('is_negative')]
    total = len(combined)

    anchor = f'{total} yogas found.'
    line = f'{len(positive)} auspicious, {len(negative)} challenging.' if total else 'Analyzing your yoga combinations.'
    hold = 'Each yoga is a promise written in planetary geometry. Dashas decide when they deliver.'

    return {
        'anchor': anchor, 'line': line, 'hold': hold,
        'math': {
            'yogas': combined[:30],
            'positive_count': len(positive),
            'negative_count': len(negative),
            'total': total,
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Health Map
# ═══════════════════════════════════════════════════════════════

def write_health_map(engine, language='en'):
    ik = _safe(engine.get_ishta_kashta, {}) or {}
    dignity = _safe(engine.get_planetary_dignity, {}) or {}
    planets = dignity.get('planets', {})

    health_planets = []
    for name in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']:
        p = ik.get(name, ik.get('planets', {}).get(name, {}))
        if isinstance(p, dict):
            health_planets.append({
                'planet': name,
                'ishta': p.get('ishta_phala', p.get('ishta', 0)),
                'kashta': p.get('kashta_phala', p.get('kashta', 0)),
                'net': p.get('net', p.get('ishta_phala', 0) - p.get('kashta_phala', 0)),
            })

    # 6th lord health indicator
    sixth_lord_house = 0
    for pname, pdata in planets.items():
        if isinstance(pdata, dict) and pdata.get('house') == 6:
            sixth_lord_house = 6

    anchor = 'Health.'
    line = 'Your body speaks the language of your planets. Some protect, some test.'
    hold = 'Ishta Phala shows benefit. Kashta Phala shows challenge.'

    return {
        'anchor': anchor, 'line': line, 'hold': hold,
        'math': {
            'planets': health_planets,
            'ishta_kashta': ik,
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Career Path
# ═══════════════════════════════════════════════════════════════

def write_career_path(engine, language='en'):
    career = _safe(engine.get_career_aptitude, {}) or {}
    rankings = career.get('rankings', [])

    # Sort by score descending
    if isinstance(rankings, list) and rankings:
        rankings_sorted = sorted(rankings, key=lambda x: x.get('score', 0), reverse=True)
        top = rankings_sorted[0]
        top_field = top.get('field', 'unknown').replace('_', ' ').title()
        top_reasons = top.get('reasons', [])
        reason_text = '. '.join(top_reasons[:2]) if top_reasons else ''
    else:
        rankings_sorted = []
        top_field = 'Career'
        reason_text = ''

    anchor = f'{top_field}.' if top_field != 'Career' else 'Career.'
    line = reason_text if reason_text else 'Your chart points toward a specific professional path.'
    hold = f'Top fields: {", ".join(r.get("field","").replace("_"," ").title() for r in rankings_sorted[:3])}' if len(rankings_sorted) >= 3 else 'Follow the 10th house.'

    return {
        'anchor': str(anchor),
        'line': str(line)[:200],
        'hold': str(hold)[:100],
        'math': {
            'rankings': rankings_sorted,
            'full_data': career,
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Eclipse Impact
# ═══════════════════════════════════════════════════════════════

def write_eclipse_impact(engine, language='en'):
    eclipses = _safe(engine.get_eclipse_calendar, {}) or {}
    upcoming = eclipses.get('upcoming', eclipses.get('eclipses', []))
    if isinstance(upcoming, dict):
        upcoming = upcoming.get('eclipses', [])

    events = []
    for ec in (upcoming or [])[:6]:
        if isinstance(ec, dict):
            events.append({
                'type': ec.get('type', 'Eclipse'),
                'date': str(ec.get('date', '')),
                'sign': ec.get('sign', ec.get('rashi', '')),
                'impact': ec.get('personal_impact', ec.get('impact', '')),
                'house': ec.get('house', ''),
            })

    anchor = f'{len(events)} eclipses ahead.' if events else 'No eclipses soon.'
    line = 'Eclipses accelerate karma. They reveal what was hidden and close what was open.'
    hold = 'The houses they touch in your chart show where change arrives.'

    return {
        'anchor': anchor, 'line': line, 'hold': hold,
        'math': {
            'eclipses': events,
            'total': len(events),
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Nadi Reading
# ═══════════════════════════════════════════════════════════════

def write_nadi_reading(engine, language='en'):
    nadi = _safe(engine.get_nadi_reading, {}) or {}

    readings = nadi.get('planet_readings', [])
    system = nadi.get('system', 'Bhrigu Nandi Nadi')

    # Find most significant reading
    first = readings[0] if readings else {}
    first_text = first.get('nadi_reading', '') if isinstance(first, dict) else ''

    anchor = system + '.'
    line = first_text[:200] if first_text else 'The Nadi reveals patterns from a different tradition — Bhrigu speaks through planetary pairs.'
    hold = 'Nadi astrology reads planet-to-planet relationships, not houses.'

    return {
        'anchor': anchor, 'line': line, 'hold': hold,
        'math': {
            'system': system,
            'readings': readings,
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Weekly Forecast
# ═══════════════════════════════════════════════════════════════

def write_weekly_forecast(engine, language='en'):
    weekly = _safe(engine.get_weekly_forecast, {}) or {}

    days = weekly.get('days', weekly.get('forecast', []))
    if isinstance(days, dict):
        days = [{'day': k, **v} if isinstance(v, dict) else {'day': k, 'summary': str(v)} for k, v in days.items()]

    theme = weekly.get('theme', weekly.get('weekly_theme', ''))

    anchor = 'This week.'
    line = str(theme)[:200] if theme else 'Seven days, seven planetary rulers, seven different energies.'
    hold = 'Each day carries the imprint of its ruling planet.'

    return {
        'anchor': anchor, 'line': line, 'hold': hold,
        'math': {
            'days': days[:7] if isinstance(days, list) else [],
            'theme': theme,
            'weekly_data': weekly,
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Numerology
# ═══════════════════════════════════════════════════════════════

def write_numerology(engine, language='en'):
    numdata = _safe(engine.get_numerology, {}) or {}
    personal = _safe(engine.get_personal_day, {}) or {}

    mulank = numdata.get('mulank', {})
    mul_num = mulank.get('number', '')
    mul_name = mulank.get('name', '')
    mul_planet = mulank.get('planet', '')
    mul_traits = mulank.get('traits', '')
    mul_strengths = mulank.get('strengths', '')
    mul_weaknesses = mulank.get('weaknesses', '')
    mul_career = mulank.get('career', '')

    personal_day = personal.get('number', personal.get('personal_day', ''))

    anchor = f'{mul_name}.' if mul_name else 'Numbers.'
    line = f'Birth number {mul_num}, ruled by {mul_planet}. {mul_traits}' if mul_num else 'Your birth date encodes a numerical vibration.'
    hold = f'Strengths: {mul_strengths}' if mul_strengths else 'Numbers reveal patterns the stars confirm.'

    return {
        'anchor': str(anchor),
        'line': str(line)[:200],
        'hold': str(hold)[:100],
        'math': {
            'mulank': mulank,
            'personal_day': personal_day,
            'full_data': numdata,
        },
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Vastu
# ═══════════════════════════════════════════════════════════════

def write_vastu(engine, language='en'):
    vastu = _safe(engine.get_vastu, {}) or {}

    favorable = vastu.get('favorable_directions', vastu.get('best_directions', []))
    unfavorable = vastu.get('unfavorable_directions', vastu.get('avoid_directions', []))

    anchor = 'Vastu.'
    line = vastu.get('summary', 'Your chart maps to physical space. Certain directions strengthen you, others drain.')
    hold = vastu.get('primary_advice', 'Align your workspace with your strongest planetary direction.')

    return {
        'anchor': anchor,
        'line': str(line)[:200],
        'hold': str(hold)[:100],
        'math': vastu,
    }


# ═══════════════════════════════════════════════════════════════
# NEW: Nakshatra Profile
# ═══════════════════════════════════════════════════════════════

def write_nakshatra_profile(engine, language='en'):
    nak = _safe(engine.get_nakshatra_profile, {}) or {}
    moon = nak.get('moon_profile', {})

    name = moon.get('nakshatra', '')
    pada = moon.get('pada', '')
    ruler = moon.get('ruler', '')
    deity = moon.get('deity', '')
    symbol = moon.get('symbol', '')
    gana = moon.get('gana', '')
    animal = moon.get('animal', '')

    anchor = f'{name}.' if name else 'Nakshatra.'
    line = f'Pada {pada}, ruled by {ruler}. Symbol: {symbol}. Gana: {gana}.' if name else 'Your nakshatra reveals your deepest emotional nature.'
    hold = f'Deity: {deity}. Animal: {animal}.' if deity else 'The nakshatra speaks to your soul.'

    return {
        'anchor': str(anchor),
        'line': str(line)[:200],
        'hold': str(hold)[:100],
        'math': {
            'moon_profile': moon,
            'all_planets': nak.get('all_planets', {}),
        },
    }
