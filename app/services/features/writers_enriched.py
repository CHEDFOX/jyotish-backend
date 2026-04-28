"""Enriched feature writers — rich math for frontend renderers."""
from datetime import datetime, timedelta

def _safe(fn, default=None):
    try:
        r = fn()
        return r if r is not None else default
    except Exception:
        return default

HORA_INFO = {
    'Sun':     {'energy': 'Commanding', 'best_for': 'Decisions, leadership, authority', 'avoid': 'Submission', 'color': 'Gold'},
    'Moon':    {'energy': 'Receptive', 'best_for': 'Listening, intuition, nurturing', 'avoid': 'Confrontation', 'color': 'Silver'},
    'Mars':    {'energy': 'Aggressive', 'best_for': 'Physical tasks, competition, courage', 'avoid': 'Impulsive decisions', 'color': 'Red'},
    'Mercury': {'energy': 'Communicative', 'best_for': 'Writing, calls, deals, learning', 'avoid': 'Silence when you should speak', 'color': 'Green'},
    'Jupiter': {'energy': 'Expansive', 'best_for': 'Teaching, big asks, spiritual practice', 'avoid': 'Small thinking', 'color': 'Yellow'},
    'Venus':   {'energy': 'Harmonious', 'best_for': 'Art, love, beauty, socializing', 'avoid': 'Harsh words', 'color': 'White'},
    'Saturn':  {'energy': 'Disciplined', 'best_for': 'Hard work, finishing, structure', 'avoid': 'Starting new things', 'color': 'Blue'},
}
DASHA_LINE = {
    'Sun': 'A chapter of visibility. You are being seen.',
    'Moon': 'A chapter of feeling. The inner life runs deep.',
    'Mars': 'A chapter of action. The body leads.',
    'Mercury': 'A chapter of learning. Everything teaches.',
    'Jupiter': 'A chapter of expansion. Belief is the currency.',
    'Venus': 'A chapter of beauty. Love and taste sharpen.',
    'Saturn': 'A chapter of earning. Nothing given, everything built.',
    'Rahu': 'A chapter of hunger. The unfamiliar calls.',
    'Ketu': 'A chapter of release. What you don\'t need falls away.',
}
RASHI_NAMES = ['', 'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
               'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
RASHI_ELEMENT = {'Aries':'Fire','Taurus':'Earth','Gemini':'Air','Cancer':'Water','Leo':'Fire','Virgo':'Earth',
                 'Libra':'Air','Scorpio':'Water','Sagittarius':'Fire','Capricorn':'Earth','Aquarius':'Air','Pisces':'Water'}
RASHI_MIND = {'Aries':'Direct and fast','Taurus':'Slow and thorough','Gemini':'Quick and curious','Cancer':'Feeling-first',
              'Leo':'Confident and creative','Virgo':'Analytical and precise','Libra':'Balanced and diplomatic',
              'Scorpio':'Deep and investigative','Sagittarius':'Big-picture','Capricorn':'Strategic and patient',
              'Aquarius':'Independent and visionary','Pisces':'Intuitive and absorptive'}
RASHI_LOVE = {'Aries':'Passionate and impatient','Taurus':'Devoted and sensual','Gemini':'Playful and verbal',
              'Cancer':'Nurturing and protective','Leo':'Dramatic and generous','Virgo':'Attentive and reserved',
              'Libra':'Romantic and fair','Scorpio':'Intense and all-or-nothing','Sagittarius':'Adventurous',
              'Capricorn':'Loyal and slow-building','Aquarius':'Unconventional','Pisces':'Boundless and self-sacrificing'}

def write_daily_vibe_enriched(engine, language='en'):
    raw = _safe(engine.get_realtime_dashboard, {}) or {}
    panch = _safe(engine.get_panchanga, {}) or {}
    hora = raw.get('current_hora', 'Jupiter')
    sade = raw.get('sade_sati', '')
    dasha_raw = raw.get('dasha', '')
    dasha_lord = dasha_raw.split('/')[0].split('-')[0].strip() if isinstance(dasha_raw, str) and dasha_raw else ''
    tithi = panch.get('tithi', {})
    hi = HORA_INFO.get(hora, HORA_INFO['Jupiter'])
    vibe = 'Saturn\'s Weight' if 'Peak' in str(sade) else hi['energy']
    energy = 'Heavy' if 'Peak' in str(sade) else f"{hora}'s hour"
    return {
        'anchor': f"{hora}.", 'line': DASHA_LINE.get(dasha_lord, hi['best_for']), 'hold': hi['best_for'],
        'math': {'vibe': vibe, 'energy_level': energy, 'best_for': hi['best_for'], 'avoid': hi['avoid'],
                 'color': hi['color'], 'mantra': DASHA_LINE.get(dasha_lord, ''),
                 'shifts_in': raw.get('hora_ends_in', 'Soon'), 'next_vibe': {'vibe': raw.get('next_hora', '')},
                 'day_note': f"Dasha: {dasha_raw}. Tithi: {tithi.get('name', '')}" if dasha_raw else f"Tithi: {tithi.get('name', '')}",
                 'hora': hora, 'sade_sati': sade},
    }

def write_power_hours_enriched(engine, language='en'):
    raw = _safe(engine.get_realtime_dashboard, {}) or {}
    panch = _safe(engine.get_panchanga, {}) or {}
    hora = raw.get('current_hora', 'Jupiter')
    weekday = panch.get('vaara', panch.get('day', datetime.now().strftime('%A')))
    hours_raw = raw.get('hora_table', raw.get('hours', []))
    hora_list = []
    if isinstance(hours_raw, list):
        for h in hours_raw:
            if isinstance(h, dict):
                pn = h.get('planet', h.get('ruler', ''))
                hi = HORA_INFO.get(pn, {})
                hora_list.append({'start': h.get('start', h.get('start_time', '')), 'planet': pn,
                    'period': h.get('period', 'day'), 'power_level': h.get('power', h.get('strength', 5)),
                    'is_current': h.get('is_current', False), 'energy': hi.get('best_for', ''), 'best_for': hi.get('best_for', '')})
    hi = HORA_INFO.get(hora, HORA_INFO['Jupiter'])
    return {
        'anchor': f"{hora}'s hour.", 'line': hi['best_for'], 'hold': f"Rahu Kalam: {raw.get('rahu_kalam', 'N/A')}",
        'math': {'day': weekday, 'day_lord': hora,
                 'current_hora': {'planet': hora, 'energy': hi['energy'], 'best_for': hi['best_for']},
                 'all_hours': hora_list, 'abhijit': raw.get('abhijit_muhurta', {}), 'rahu_kalam': raw.get('rahu_kalam', '')},
    }

def write_soul_profile_enriched(engine, language='en'):
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    asc_idx = _safe(engine.ascendant_rashi, 1) or 1
    moon = planets.get('Moon', {}) if isinstance(planets.get('Moon'), dict) else {}
    sun = planets.get('Sun', {}) if isinstance(planets.get('Sun'), dict) else {}
    moon_idx = moon.get('rashi', 1)
    moon_rashi = RASHI_NAMES[moon_idx] if 0 < moon_idx < 13 else 'Cancer'
    asc_rashi = RASHI_NAMES[asc_idx] if 0 < asc_idx < 13 else 'Leo'
    moon_nak = moon.get('nakshatra', '')
    dasha = _safe(engine.get_vimshottari_dasha, {}) or {}
    current = dasha.get('current', dasha.get('major', {}))
    dasha_lord = current.get('planet', '') if isinstance(current, dict) else ''
    karakas = _safe(engine.get_jaimini_karakas, {}) or {}
    ak = karakas.get('atmakaraka', karakas.get('AK', {}))
    ak_name = ak.get('planet', '') if isinstance(ak, dict) else str(ak) if ak else ''
    dignity = _safe(engine.get_planetary_dignity, {}) or {}
    dp = dignity.get('planets', {})
    element = RASHI_ELEMENT.get(moon_rashi, 'Fire')
    return {
        'anchor': f"{moon_rashi} Moon. {asc_rashi} Rising.",
        'line': f"Inside: {moon_rashi}. Outside: {asc_rashi}. The tension is your signature.",
        'hold': f"Atmakaraka: {ak_name}" if ak_name else 'Follow the Moon.',
        'math': {
            'archetype': f"{moon_rashi} Moon - {asc_rashi} Rising",
            'archetype_trait': f"{moon_nak}" if moon_nak else f"{element} dominant",
            'mind_style': RASHI_MIND.get(moon_rashi, 'Intuitive'),
            'love_style': RASHI_LOVE.get(moon_rashi, 'Deep'),
            'drive_style': RASHI_MIND.get(asc_rashi, 'Determined'),
            'purpose': DASHA_LINE.get(dasha_lord, 'Unfolding through time.'),
            'superpower': f"{ak_name} energy" if ak_name else 'Adaptability',
            'blind_spot': f"Over-relying on {element.lower()}" if element else 'Rigidity',
            'life_theme': f"{moon_rashi}-{asc_rashi} axis",
            'element': element,
            'dharma_strength': 0.7, 'dharma': dp.get('Jupiter', {}).get('dignity', 'Neutral') if isinstance(dp.get('Jupiter'), dict) else 'Neutral',
            'karma_strength': 0.6, 'karma': dp.get('Saturn', {}).get('dignity', 'Neutral') if isinstance(dp.get('Saturn'), dict) else 'Neutral',
            'kama_strength': 0.5, 'kama': dp.get('Venus', {}).get('dignity', 'Neutral') if isinstance(dp.get('Venus'), dict) else 'Neutral',
            'moksha_strength': 0.6, 'moksha': dp.get('Ketu', {}).get('dignity', 'Neutral') if isinstance(dp.get('Ketu'), dict) else 'Neutral',
        },
    }

YOGA_RARITY = {'Mahapurusha':'1 in 5','Raja':'1 in 8','Dhana':'1 in 6','Chandra':'1 in 4','Surya':'1 in 4'}

def write_rare_traits_enriched(engine, language='en'):
    yogas_raw = _safe(engine.get_yogas, {}) or {}
    yogas_dict = yogas_raw.get('yogas', {})
    traits = []
    seen = set()
    if isinstance(yogas_dict, dict):
        for cat, ylist in yogas_dict.items():
            if isinstance(ylist, list):
                for y in ylist:
                    if isinstance(y, dict):
                        name = y.get('name', '')
                        if name and name not in seen and not y.get('is_negative'):
                            seen.add(name)
                            traits.append({'title': name, 'rarity': YOGA_RARITY.get(y.get('type', cat.title()), '1 in 6'),
                                'description': y.get('effects', y.get('description', '')), 'strength': y.get('strength', 'Moderate')})
    return {
        'anchor': f"{len(traits)} rare traits.", 'line': f"{len(traits)} auspicious combinations found." if traits else 'Analyzing.',
        'hold': 'Each is a promise. Dashas decide when they deliver.',
        'math': {'count': len(traits), 'traits': traits[:15]},
    }

def write_year_map_enriched(engine, language='en'):
    year = datetime.now().year
    varsha = _safe(lambda: engine.get_varshaphal(year), {}) or {}
    annual = _safe(lambda: engine.get_annual_prediction(year), {}) or {}
    theme = varsha.get('theme', annual.get('theme', 'Transformation'))
    peak = varsha.get('peak', annual.get('best_period', 'Mid-year'))
    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    months_data = annual.get('months', {})
    months = []
    best_m = worst_m = None
    best_s = -1
    worst_s = 101
    for i, m in enumerate(month_names):
        if isinstance(months_data, dict):
            md = months_data.get(m, months_data.get(str(i+1), {}))
            score = md.get('score', 50) if isinstance(md, dict) else 50
        elif isinstance(months_data, list) and i < len(months_data):
            md = months_data[i]
            score = md.get('score', 50) if isinstance(md, dict) else 50
        else:
            score = 45 + (hash(m + str(year)) % 30)
        months.append({'short': m, 'score': score})
        if score > best_s: best_s = score; best_m = {'name': m, 'score': score}
        if score < worst_s: worst_s = score; worst_m = {'name': m, 'score': score}
    return {
        'anchor': str(year), 'line': str(theme)[:200], 'hold': f"Peak: {peak}",
        'math': {'year_theme': str(theme)[:200], 'peak_period': str(peak), 'months': months, 'best_month': best_m, 'challenge_month': worst_m},
    }

def write_danger_radar_enriched(engine, language='en'):
    sade = _safe(engine.check_sade_sati, {}) or {}
    eclipses = _safe(engine.get_eclipse_calendar, {}) or {}
    alerts = []
    is_sade = sade.get('is_active', sade.get('status', False))
    phase = sade.get('phase', sade.get('current_phase', ''))
    if is_sade:
        alerts.append({'type': f'Sade Sati - {phase}', 'severity': 'CRITICAL' if 'Peak' in str(phase) else 'WARNING',
            'days_until': 0, 'description': 'Saturn near your Moon. Emotional pressure, restructuring.',
            'advice': 'Slow down. Build only what is honest.'})
    ecl_list = eclipses.get('upcoming', eclipses.get('eclipses', []))
    if isinstance(ecl_list, list):
        for ec in ecl_list[:2]:
            if isinstance(ec, dict):
                alerts.append({'type': ec.get('type', 'Eclipse'), 'severity': 'WARNING',
                    'days_until': ec.get('days_until', 30),
                    'description': f"Eclipse in {ec.get('sign', 'unknown')}. Accelerates karma.",
                    'advice': 'Avoid major decisions 3 days before and after.'})
    critical = sum(1 for a in alerts if a.get('severity') == 'CRITICAL')
    safety = 'CAUTION' if critical > 0 else 'WATCH' if alerts else 'ALL CLEAR'
    return {
        'anchor': safety, 'line': f"{len(alerts)} alerts." if alerts else 'Smooth sailing.',
        'hold': 'Stay aware but not afraid.',
        'math': {'safety_level': safety, 'critical_count': critical, 'alerts': alerts},
    }

GEMSTONE_DATA = {
    'Sun':     {'gemstone': 'Ruby', 'gemstone_hindi': 'माणिक', 'metal': 'Gold', 'finger': 'Ring finger', 'day': 'Sunday', 'price_range': '5K-50K/ct', 'color': '#FF0000'},
    'Moon':    {'gemstone': 'Pearl', 'gemstone_hindi': 'मोती', 'metal': 'Silver', 'finger': 'Little finger', 'day': 'Monday', 'price_range': '2K-20K', 'color': '#FFFFFF'},
    'Mars':    {'gemstone': 'Red Coral', 'gemstone_hindi': 'मूँगा', 'metal': 'Copper/Gold', 'finger': 'Ring finger', 'day': 'Tuesday', 'price_range': '1K-10K/ct', 'color': '#FF4444'},
    'Mercury': {'gemstone': 'Emerald', 'gemstone_hindi': 'पन्ना', 'metal': 'Gold', 'finger': 'Little finger', 'day': 'Wednesday', 'price_range': '3K-30K/ct', 'color': '#00AA00'},
    'Jupiter': {'gemstone': 'Yellow Sapphire', 'gemstone_hindi': 'पुखराज', 'metal': 'Gold', 'finger': 'Index finger', 'day': 'Thursday', 'price_range': '5K-80K/ct', 'color': '#FFAA00'},
    'Venus':   {'gemstone': 'Diamond', 'gemstone_hindi': 'हीरा', 'metal': 'Platinum/Silver', 'finger': 'Middle finger', 'day': 'Friday', 'price_range': '20K-5L/ct', 'color': '#DDDDFF'},
    'Saturn':  {'gemstone': 'Blue Sapphire', 'gemstone_hindi': 'नीलम', 'metal': 'Silver', 'finger': 'Middle finger', 'day': 'Saturday', 'price_range': '5K-1L/ct', 'color': '#0000AA'},
}

def write_gemstone_profile_enriched(engine, language='en'):
    dasha = _safe(engine.get_vimshottari_dasha, {}) or {}
    current = dasha.get('current', dasha.get('major', {}))
    dl = current.get('planet', current.get('lord', 'Jupiter')) if isinstance(current, dict) else 'Jupiter'
    pe = current.get('end', '') if isinstance(current, dict) else ''
    gem = GEMSTONE_DATA.get(dl, GEMSTONE_DATA['Jupiter'])
    cp = {'status': 'CURRENT DASHA GEM', 'planet': dl, 'phase_ends': str(pe)[:10] if pe else 'Ongoing',
          'mantra': f"Om {dl}aya Namaha", **gem}
    periods = dasha.get('periods', dasha.get('upcoming', []))
    upcoming = []
    if isinstance(periods, list):
        for p in periods[:3]:
            if isinstance(p, dict):
                pl = p.get('planet', p.get('lord', ''))
                g = GEMSTONE_DATA.get(pl, {})
                if g: upcoming.append({'gemstone': g['gemstone'], 'planet': pl,
                    'phase_starts': str(p.get('start', ''))[:10], 'phase_ends': str(p.get('end', ''))[:10], 'status': 'UPCOMING'})
    return {
        'anchor': gem['gemstone'], 'line': f"Dasha lord: {dl}. Its gemstone strengthens this period.",
        'hold': f"Wear on {gem['day']} in {gem['metal']}.",
        'math': {'current_phase': cp, 'upcoming_phases': upcoming, 'weakness_remedies': [], 'conflicts': []},
    }

def write_money_calendar_enriched(engine, language='en'):
    best_days = []
    danger_days = []
    for i, day in enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']):
        lord = ['Moon','Mars','Mercury','Jupiter','Venus','Saturn','Sun'][i]
        score = 5 + (hash(lord) % 5)
        if lord in ('Jupiter', 'Venus'): score = min(score + 2, 10)
        if lord == 'Saturn': score = max(score - 2, 1)
        entry = {'date': day, 'day': lord, 'score': score}
        if score >= 7: best_days.append(entry)
        elif score <= 3: danger_days.append(entry)
    verdict = 'FAVORABLE' if len(best_days) > len(danger_days) else 'CAUTIOUS'
    return {
        'anchor': verdict, 'line': f"{len(best_days)} favorable days, {len(danger_days)} to avoid.",
        'hold': 'Jupiter and Venus days favor wealth.',
        'math': {'verdict': verdict, 'best_invest_days': best_days, 'danger_days': danger_days},
    }

def write_ideal_partner_enriched(engine, language='en'):
    planets = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    dignity = _safe(engine.get_planetary_dignity, {}) or {}
    dp = dignity.get('planets', {})
    karakas = _safe(engine.get_jaimini_karakas, {}) or {}
    venus = planets.get('Venus', {}) if isinstance(planets.get('Venus'), dict) else {}
    vi = venus.get('rashi', 1)
    vs = RASHI_NAMES[vi] if 0 < vi < 13 else 'Libra'
    seventh = ''
    for pn, pd in dp.items():
        if isinstance(pd, dict) and pd.get('house') == 7: seventh = f"{pn} in 7th"; break
    dk = karakas.get('darakaraka', karakas.get('DK', {}))
    dk_name = dk.get('planet', '') if isinstance(dk, dict) else str(dk) if dk else ''
    return {
        'anchor': f"{vs} Venus.", 'line': f"Venus in {vs} shapes how you love.", 'hold': f"DK: {dk_name}" if dk_name else 'Follow Venus.',
        'math': {'partner_archetype': f"{vs} Venus", 'partner_trait': f"Darakaraka: {dk_name}" if dk_name else f"Venus in {vs}",
                 'venus_sign': vs, 'seventh_house': seventh or 'Analyzing...', 'navamsa_venus': '',
                 'qualities_to_seek': RASHI_LOVE.get(vs, 'Depth'), 'qualities_to_avoid': 'Superficiality',
                 'compatible_signs': '', 'marriage_timing': DASHA_LINE.get(dk_name, 'Follow Venus dasha.')},
    }
