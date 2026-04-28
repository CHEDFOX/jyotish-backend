"""
FEATURE WRITERS v2 — interpretive, not echoic.

Every writer produces:
  anchor:  1 fact (time, name, number) — big type
  line:    1 sentence — what it means for YOU
  hold:    1 sentence — what to DO (or not do)
  math:    raw data receipts

Philosophy: the user should read these 3 lines and feel SEEN.
Not informed. Seen. 15-30 words. Every word earns its place.
"""

from datetime import datetime
from .writers_enriched import (write_daily_vibe_enriched, write_power_hours_enriched,
    write_soul_profile_enriched, write_rare_traits_enriched, write_year_map_enriched,
    write_danger_radar_enriched, write_gemstone_profile_enriched, write_money_calendar_enriched,
    write_ideal_partner_enriched)

from .writers_new import (write_planet_strength as _new_planet_strength,
    write_active_yogas, write_health_map, write_career_path,
    write_eclipse_impact, write_nadi_reading, write_weekly_forecast,
    write_numerology, write_vastu, write_nakshatra_profile)



# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def _article(word):
    """Return 'an' or 'a' based on first letter."""
    if not word:
        return 'a'
    return 'an' if word[0].lower() in 'aeiou' else 'a'


def _format_date(raw):
    """Convert '2026-08-12' to 'August 12'."""
    if not raw or not isinstance(raw, str):
        return str(raw) if raw else ''
    try:
        dt = datetime.strptime(raw[:10], '%Y-%m-%d')
        return dt.strftime('%B %d').replace(' 0', ' ')
    except Exception:
        return raw


RASHI_NAMES = ['', 'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
               'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']


# ═══════════════════════════════════════════════════════════════
# PLANET INTERPRETATION MAPS
# ═══════════════════════════════════════════════════════════════

HORA_MEANING = {
    'Sun':     ('The Sun\'s hour.', 'Your authority is louder now than usual.', 'Decide something you\'ve been avoiding.'),
    'Moon':    ('The Moon\'s hour.', 'Your feelings are closer to the surface.', 'Listen before you speak.'),
    'Mars':    ('Mars\'s hour.', 'Your body knows before your mind does.', 'Move first. Think after.'),
    'Mercury': ('Mercury\'s hour.', 'Words land precisely right now.', 'Write the message. Make the call.'),
    'Jupiter': ('Jupiter\'s hour.', 'The sky is generous for the next sixty minutes.', 'Ask for something bigger than usual.'),
    'Venus':   ('Venus\'s hour.', 'Beauty and warmth are amplified.', 'Create something. Reach out to someone.'),
    'Saturn':  ('Saturn\'s hour.', 'This hour rewards discipline, not desire.', 'Finish what\'s already started.'),
}

DASHA_MEANING = {
    'Sun':     'A chapter of visibility. You are being seen.',
    'Moon':    'A chapter of feeling. The inner life runs deep.',
    'Mars':    'A chapter of action. The body leads.',
    'Mercury': 'A chapter of learning. Everything teaches.',
    'Jupiter': 'A chapter of expansion. Belief is the currency.',
    'Venus':   'A chapter of beauty. Love and taste sharpen.',
    'Saturn':  'A chapter of earning. Nothing is given; everything is built.',
    'Rahu':    'A chapter of hunger. The unfamiliar calls.',
    'Ketu':    'A chapter of release. What you don\'t need falls away.',
}

DASHA_HOLD = {
    'Sun':     'Stand where you can be seen.',
    'Moon':    'Protect your quiet.',
    'Mars':    'Build through sweat, not strategy.',
    'Mercury': 'Stay curious. Stay moving.',
    'Jupiter': 'Teach what you know. Learn what you don\'t.',
    'Venus':   'Make something beautiful today.',
    'Saturn':  'Do the hard thing. The reward is slow.',
    'Rahu':    'Chase what scares you a little.',
    'Ketu':    'Let go of one thing you\'re holding too tight.',
}

RASHI_SOUL = {
    'Aries':       'Fire starter. You begin things the world needs.',
    'Taurus':      'Earth keeper. You hold what others let go.',
    'Gemini':      'Air weaver. You connect what others can\'t see.',
    'Cancer':      'Water bearer. You carry others\' feelings as your own.',
    'Leo':         'Sun child. You were born to be witnessed.',
    'Virgo':       'Earth healer. You fix what the world breaks.',
    'Libra':       'Air mirror. You show people their own beauty.',
    'Scorpio':     'Water diver. You see what everyone pretends isn\'t there.',
    'Sagittarius': 'Fire seeker. You chase truth over comfort.',
    'Capricorn':   'Earth builder. You make things that outlast you.',
    'Aquarius':    'Air storm. You break patterns others worship.',
    'Pisces':      'Water dreamer. You dissolve the walls between worlds.',
}

GEMSTONE_MEANING = {
    'Sun':     {'stone': 'Ruby', 'metal': 'gold', 'finger': 'ring finger', 'day': 'Sunday',
                'why': 'It concentrates the Sun\'s heat into your bloodstream.'},
    'Moon':    {'stone': 'Pearl', 'metal': 'silver', 'finger': 'little finger', 'day': 'Monday',
                'why': 'It steadies the Moon\'s pull on your emotions.'},
    'Mars':    {'stone': 'Red coral', 'metal': 'copper or gold', 'finger': 'ring finger', 'day': 'Tuesday',
                'why': 'It grounds Mars\'s raw force into endurance.'},
    'Mercury': {'stone': 'Emerald', 'metal': 'gold', 'finger': 'little finger', 'day': 'Wednesday',
                'why': 'It sharpens Mercury\'s edge without the anxiety.'},
    'Jupiter': {'stone': 'Yellow sapphire', 'metal': 'gold', 'finger': 'index finger', 'day': 'Thursday',
                'why': 'It amplifies Jupiter\'s generosity toward you.'},
    'Venus':   {'stone': 'Diamond', 'metal': 'platinum or silver', 'finger': 'middle finger', 'day': 'Friday',
                'why': 'It opens Venus\'s gate to beauty and ease.'},
    'Saturn':  {'stone': 'Blue sapphire', 'metal': 'silver', 'finger': 'middle finger', 'day': 'Saturday',
                'why': 'It converts Saturn\'s pressure into patience. Handle with care.'},
}

DEITY_MEANING = {
    'Sun':     ('Rama', 'The king who walked through fire for love. Your soul learns through duty and sacrifice.'),
    'Moon':    ('Krishna', 'The one who played while the world burned. Your soul learns through love and paradox.'),
    'Mars':    ('Hanuman', 'The warrior who forgot his own power. Your soul learns through devotion and action.'),
    'Mercury': ('Vishnu', 'The preserver who dreams the universe. Your soul learns through balance and intelligence.'),
    'Jupiter': ('Brihaspati', 'The guru of the gods. Your soul learns through wisdom and generosity.'),
    'Venus':   ('Lakshmi', 'Abundance in form. Your soul learns through beauty, pleasure, and giving.'),
    'Saturn':  ('Shani Dev', 'The judge who teaches through weight. Your soul learns through patience and truth.'),
    'Rahu':    ('Durga', 'The one who destroys what imprisons you. Your soul learns through breaking limits.'),
    'Ketu':    ('Ganesha', 'The remover of obstacles — including yourself. Your soul learns through letting go.'),
}

DK_MEANING = {
    'Sun':     ('Someone with quiet authority.', 'They lead without asking permission.'),
    'Moon':    ('Someone deeply feeling.', 'They carry others\' emotions willingly.'),
    'Mars':    ('Someone direct and physical.', 'They move first, explain later.'),
    'Mercury': ('Someone sharp and restless.', 'They talk fast and think faster.'),
    'Jupiter': ('Someone wise beyond their years.', 'They teach you without trying.'),
    'Venus':   ('Someone beautiful in how they live.', 'They make ordinary things feel like art.'),
    'Saturn':  ('Someone older in soul.', 'They are patient where you are not.'),
    'Rahu':    ('Someone unconventional.', 'They break your assumptions about what love looks like.'),
    'Ketu':    ('Someone spiritual or detached.', 'They teach you through what they don\'t need.'),
}

YOGA_MEANING = {
    'Gaja Kesari':    ('Gaja Kesari.', 'Jupiter and Moon see each other in your chart. Wisdom and emotional depth, combined. This is remembered long after you leave a room.'),
    'Raja':           ('Raja yoga.', 'The kings\' combination. Authority doesn\'t need to be claimed — it\'s already written.'),
    'Dhana':          ('Dhana yoga.', 'Wealth is not luck for you. It\'s structural. The question is when, not if.'),
    'Chandra Mangal': ('Chandra Mangal.', 'Moon meets Mars. Your emotions and your will are the same force. When you feel, you act.'),
    'Budh Aditya':    ('Budhaditya.', 'Mercury sits with Sun. Intelligence that burns clean. You see through things others accept.'),
    'Neech Bhanga':   ('Neech Bhanga.', 'A fallen planet in your chart has been caught. Your deepest weakness becomes your signature strength.'),
    'Pushkara':       ('Pushkara degree.', 'One of your planets sits in a nourishing degree. Something in your chart is protected by the cosmos itself.'),
    'Hamsa':          ('Hamsa yoga.', 'Jupiter in its own sign or exaltation in a kendra. You carry natural wisdom that others seek.'),
    'Malavya':        ('Malavya yoga.', 'Venus in its own sign or exaltation in a kendra. Beauty, art, and comfort come naturally.'),
    'Ruchaka':        ('Ruchaka yoga.', 'Mars in its own sign or exaltation in a kendra. Physical courage and command are innate.'),
    'Bhadra':         ('Bhadra yoga.', 'Mercury in its own sign or exaltation in a kendra. Communication and intelligence are your native tools.'),
    'Shasha':         ('Shasha yoga.', 'Saturn in its own sign or exaltation in a kendra. Discipline and endurance define you.'),
}

# ─── Festival rules: (name, sun_rashi, paksha, tithi_in_paksha, meaning) ───
# sun_rashi: 1=Aries..12=Pisces (sidereal)
# tithi_in_paksha: 1-15
# paksha: 'Shukla' (waxing) or 'Krishna' (waning)
FESTIVAL_RULES = [
    ('Maha Shivaratri',  11, 'Krishna', 14, 'The great night of Shiva. Silence holds power tonight.'),
    ('Holi',             11, 'Shukla',  15, 'Full moon of colors. Let something old burn away.'),
    ('Ram Navami',       12, 'Shukla',   9, 'Birth of Rama. Duty and love are the same today.'),
    ('Akshaya Tritiya',   1, 'Shukla',   3, 'Day of imperishable merit. What you begin today doesn\'t decay.'),
    ('Buddha Purnima',    1, 'Shukla',  15, 'Full moon of awakening. Watch without acting.'),
    ('Guru Purnima',      3, 'Shukla',  15, 'The teacher\'s moon. Honor whoever shaped you most.'),
    ('Raksha Bandhan',    4, 'Shukla',  15, 'The thread of protection. Guard what you love.'),
    ('Janmashtami',       4, 'Krishna',  8, 'Birth of Krishna. The divine arrives at midnight.'),
    ('Ganesh Chaturthi',  5, 'Shukla',   4, 'The remover arrives. Name one obstacle honestly.'),
    ('Navratri',          6, 'Shukla',   1, 'Nine nights of Shakti. Power rises if you let it.'),
    ('Dussehra',          6, 'Shukla',  10, 'Victory of good over what pretends to be.'),
    ('Diwali',            7, 'Krishna', 15, 'The return of light. What was dark becomes doorway.'),
    ('Gita Jayanti',      8, 'Shukla',  11, 'Song of the battlefield. Act without clinging to the fruit.'),
    ('Makar Sankranti',  10, None,    None, 'Sun enters Capricorn. The northward journey begins.'),
]


def _scan_festivals(engine, days_ahead=60):
    """Scan the next N days using real panchanga to find upcoming festivals."""
    from datetime import timedelta
    today = datetime.now()
    upcoming = []

    for d in range(days_ahead):
        check_date = today + timedelta(days=d)
        try:
            panch = engine.get_panchanga(check_date)
            tithi = panch.get('tithi', {})
            tithi_in_paksha = tithi.get('tithi_in_paksha', 0)
            paksha = tithi.get('paksha', '')

            # Get Sun rashi from the engine's transit data
            transits = engine.ephemeris.get_transits_for_date(check_date)
            sun_long = transits.get('Sun', {}).get('longitude', 0)
            sun_rashi = int(sun_long / 30) % 12 + 1  # 1-12

            for name, rule_rashi, rule_paksha, rule_tithi, meaning in FESTIVAL_RULES:
                # Makar Sankranti — special: Sun entering Capricorn (rashi 10)
                if rule_paksha is None and rule_tithi is None:
                    if sun_rashi == rule_rashi and d > 0:
                        # Check if Sun just entered this rashi (wasn't there yesterday)
                        prev_date = check_date - timedelta(days=1)
                        prev_transits = engine.ephemeris.get_transits_for_date(prev_date)
                        prev_sun_rashi = int(prev_transits.get('Sun', {}).get('longitude', 0) / 30) % 12 + 1
                        if prev_sun_rashi != sun_rashi:
                            upcoming.append((name, check_date.strftime('%B %d').replace(' 0', ' '), meaning, d))
                    continue

                # Standard tithi-based festival
                if sun_rashi == rule_rashi and paksha == rule_paksha and tithi_in_paksha == rule_tithi:
                    date_str = check_date.strftime('%B %d').replace(' 0', ' ')
                    upcoming.append((name, date_str, meaning, d))

        except Exception:
            continue

        # Stop after finding 3 festivals
        if len(upcoming) >= 3:
            break

    return upcoming


# ═══════════════════════════════════════════════════════════════
# 1. DAILY VIBE
# ═══════════════════════════════════════════════════════════════

def write_daily_vibe(engine):
    raw = _safe(engine.get_realtime_dashboard, {}) or {}
    hora = raw.get('current_hora', '') or 'Jupiter'
    sade = raw.get('sade_sati', '') or ''

    meaning = HORA_MEANING.get(hora, HORA_MEANING['Jupiter'])

    if 'Peak' in sade:
        anchor = 'Saturn is close.'
        line = 'The weight phase is at its deepest. Everything feels heavier — it\'s real, not imagined.'
        hold = 'Slow down. Build only what\'s honest.'
    else:
        anchor, line, hold = meaning

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'hora': hora,
            'choghadiya': (raw.get('choghadiya') or {}).get('nature', ''),
            'dasha': raw.get('dasha', ''),
            'sade_sati': sade,
            'personal_day': raw.get('personal_day_number', 0),
        },
    }


# ═══════════════════════════════════════════════════════════════
# 2. POWER HOURS
# ═══════════════════════════════════════════════════════════════

def write_power_hours(engine):
    raw = _safe(engine.get_realtime_dashboard, {}) or {}
    timing = _safe(engine.get_daily_timing, {}) or {}
    abhijit = timing.get('abhijit_muhurta') or raw.get('abhijit_muhurta') or {}
    start = abhijit.get('start', '')
    end = abhijit.get('end', '')
    rahu_kalam = raw.get('rahu_kalam', '')

    if start and end:
        anchor = f'{start} — {end}'
        line = 'Abhijit muhurta. The single strongest window today. What you begin here sticks.'
        hold = 'Don\'t waste it on errands.'
    else:
        hora = raw.get('current_hora', 'Jupiter')
        anchor = f'{hora}\'s hour.'
        line = f'The current hora. {HORA_MEANING.get(hora, HORA_MEANING["Jupiter"])[1]}'
        hold = HORA_MEANING.get(hora, HORA_MEANING['Jupiter'])[2]

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'abhijit': abhijit,
            'rahu_kalam': rahu_kalam,
            'hora': raw.get('current_hora', ''),
            'choghadiya': timing.get('choghadiya', {}),
        },
    }


# ═══════════════════════════════════════════════════════════════
# 3. PLANET STRENGTH
# ═══════════════════════════════════════════════════════════════

PLANET_DOMINANCE = {
    'Sun':     'You lead. Your chart says authority is native, not borrowed.',
    'Moon':    'You feel. Your chart says emotional intelligence is your sharpest tool.',
    'Mars':    'You act. Your chart says willpower is your defining trait.',
    'Mercury': 'You think. Your chart says your mind is your greatest asset.',
    'Jupiter': 'You believe. Your chart says wisdom and faith drive everything.',
    'Venus':   'You create. Your chart says beauty and relationships define your path.',
    'Saturn':  'You endure. Your chart says patience is your superpower.',
}


def write_planet_strength(engine):
    sb = _safe(engine.get_shadbala_complete, {}) or _safe(engine.get_shadbala, {}) or {}
    planets = sb.get('planets', []) or sb.get('results', []) or []

    strongest = None
    best_score = -1
    for p in planets:
        score = p.get('total', 0) or p.get('virupa_total', 0) or p.get('shadbala', 0)
        if isinstance(score, (int, float)) and score > best_score:
            best_score = score
            strongest = p

    if strongest:
        name = strongest.get('name') or strongest.get('planet') or 'Jupiter'
        score = int(best_score) if best_score > 0 else ''
        anchor = f'{name}.'
        line = PLANET_DOMINANCE.get(name, f'{name} dominates your chart.')
        hold = f'Shadbala: {score} virupa.' if score else ''
    else:
        anchor = 'Balanced.'
        line = 'No single planet dominates. Your chart distributes power evenly.'
        hold = 'Trust the whole, not the parts.'

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'strongest': strongest or {},
            'all': [{'planet': p.get('name', ''), 'score': p.get('total', 0)} for p in planets[:7]],
        },
    }


# ═══════════════════════════════════════════════════════════════
# 4. SOUL PROFILE
# ═══════════════════════════════════════════════════════════════

def write_soul_profile(engine):
    planets = _safe(engine.planets, {}) or {}
    asc_idx = _safe(engine.ascendant_rashi, 1) or 1

    moon = planets.get('Moon', {}) or {}
    moon_idx = moon.get('rashi', 1) or 1
    moon_rashi = RASHI_NAMES[moon_idx] if 0 < moon_idx < 13 else 'Cancer'
    asc_rashi = RASHI_NAMES[asc_idx] if 0 < asc_idx < 13 else 'Leo'
    moon_nak = moon.get('nakshatra', '')

    # Interpretation — not echo
    soul_line = RASHI_SOUL.get(moon_rashi, f'Your moon lives in {moon_rashi}.')

    if moon_rashi == asc_rashi:
        anchor = f'{moon_rashi}.'
        line = f'Moon and rising sign both here. You are undiluted. What people see is exactly what runs beneath.'
        hold = soul_line
    else:
        anchor = f'{moon_rashi} moon. {asc_rashi} rising.'
        line = f'Inside: {RASHI_SOUL.get(moon_rashi, moon_rashi + ".")} Outside: {RASHI_SOUL.get(asc_rashi, asc_rashi + ".")}'
        hold = 'The tension between them is your signature.'

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'moon_rashi': moon_rashi,
            'ascendant': asc_rashi,
            'moon_nakshatra': moon_nak,
            'moon_degrees': round(moon.get('longitude', 0), 2),
        },
    }


# ═══════════════════════════════════════════════════════════════
# 5. RARE TRAITS
# ═══════════════════════════════════════════════════════════════

def write_rare_traits(engine):
    yogas = _safe(engine.get_yogas, {}) or {}
    all_yogas = yogas.get('yogas', []) or yogas.get('active', []) or []
    raja = _safe(engine.get_raja_yogas, []) or []
    dhana = _safe(engine.get_dhana_yogas, []) or []

    yoga_names = []
    for y in (all_yogas + raja + dhana):
        name = y.get('name', '') if isinstance(y, dict) else str(y)
        if name:
            yoga_names.append(name)

    # Find a yoga we have rich copy for
    for yname in yoga_names:
        for key, (anchor, meaning) in YOGA_MEANING.items():
            if key.lower() in yname.lower():
                return {
                    'anchor': anchor,
                    'line': meaning,
                    'hold': '',
                    'math': {'matched_yoga': yname, 'all_yogas': yoga_names[:10]},
                }

    total = len(set(yoga_names))
    if total > 3:
        return {
            'anchor': f'{total} active yogas.',
            'line': 'More planetary combinations than most charts carry. Your chart is dense with potential.',
            'hold': 'The question isn\'t whether. It\'s when.',
            'math': {'yogas': yoga_names[:10], 'count': total},
        }
    elif total > 0:
        return {
            'anchor': f'{total} yoga{"s" if total > 1 else ""}.',
            'line': f'Active in your chart: {", ".join(yoga_names[:3])}.',
            'hold': '',
            'math': {'yogas': yoga_names[:10]},
        }
    return {
        'anchor': 'Quiet chart.',
        'line': 'No classical yogas fired — but the chart still speaks through house lords and aspects.',
        'hold': 'Ask the Oracle about your specific houses.',
        'math': {},
    }


def _get_karaka(karakas, key):
    """Case-insensitive karaka lookup — engine uses 'Atmakaraka', we might try 'atmakaraka'."""
    if not karakas:
        return {}
    # Try exact, then capitalized, then lowercase
    return karakas.get(key) or karakas.get(key.capitalize()) or karakas.get(key[0].upper() + key[1:]) or karakas.get(key.lower()) or {}


# ═══════════════════════════════════════════════════════════════
# 6. PERSONAL DEITIES
# ═══════════════════════════════════════════════════════════════

def write_personal_deities(engine):
    karakas = _safe(engine.get_jaimini_karakas, {}) or {}
    ak = _get_karaka(karakas, 'Atmakaraka')
    ak_planet = ak.get('planet') or ak.get('name') or 'Jupiter'

    deity, meaning = DEITY_MEANING.get(ak_planet, ('Brihaspati', 'Your soul learns through wisdom.'))

    return {
        'anchor': f'{deity}.',
        'line': meaning,
        'hold': f'Your atmakaraka is {ak_planet}.',
        'math': {
            'atmakaraka': ak_planet,
            'deity': deity,
            'all_karakas': karakas,
        },
    }


# ═══════════════════════════════════════════════════════════════
# 7. GEMSTONE PROFILE
# ═══════════════════════════════════════════════════════════════

def write_gemstone_profile(engine):
    gems = _safe(engine.get_gemstone_recommendations, []) or []

    if gems and isinstance(gems, list) and len(gems) > 0:
        primary = gems[0] if isinstance(gems[0], dict) else {}
        planet = primary.get('planet') or primary.get('for') or 'Jupiter'
    else:
        planet = 'Jupiter'

    gem = GEMSTONE_MEANING.get(planet, GEMSTONE_MEANING['Jupiter'])

    return {
        'anchor': f'{gem["stone"]}.',
        'line': gem['why'],
        'hold': f'Set in {gem["metal"]}. {gem["finger"].title()}. {gem["day"]} sunrise.',
        'math': {
            'planet': planet,
            'stone': gem['stone'],
            'metal': gem['metal'],
            'finger': gem['finger'],
            'day': gem['day'],
            'all_recommendations': gems[:5] if isinstance(gems, list) else [],
        },
    }


# ═══════════════════════════════════════════════════════════════
# 8. DANGER RADAR
# ═══════════════════════════════════════════════════════════════

def write_danger_radar(engine):
    transit = _safe(engine.get_transit_deep, {}) or {}
    eclipse = _safe(engine.get_eclipse_calendar, {}) or {}

    sade = transit.get('sade_sati', {}) or {}
    eclipses = eclipse.get('upcoming_eclipses', []) or []
    retros = transit.get('retrogrades', []) or []

    if eclipses:
        ec = eclipses[0]
        date_raw = ec.get('date', '')
        date_nice = _format_date(date_raw)
        rashi = ec.get('rashi', '')
        severity = (ec.get('personal_impact') or {}).get('severity', '')

        anchor = f'{date_nice}.'
        line = f'Eclipse in {rashi}.' if rashi else 'Eclipse corridor.'
        if severity == 'High':
            line += ' High personal impact — this one touches your chart directly.'
        hold = 'Avoid major commitments two weeks around this date.'
    elif 'Peak' in sade.get('phase', ''):
        anchor = 'Sade Sati — peak.'
        line = 'Saturn transits over your Moon. The heaviest phase. Everything tests you — relationships, health, career. It\'s real pressure, not bad luck.'
        hold = 'Build slowly. Serve others. This passes.'
    elif len(retros) >= 3:
        retro_names = [r.get('planet', str(r)) if isinstance(r, dict) else str(r) for r in retros[:4]]
        anchor = f'{len(retros)} retrogrades.'
        line = f'{", ".join(retro_names)} are all looking backward. Review, don\'t launch.'
        hold = 'Revisit old projects. Don\'t start new ones.'
    elif 'Rising' in sade.get('phase', '') or 'Setting' in sade.get('phase', ''):
        anchor = 'Sade Sati — active.'
        line = f'{sade.get("phase", "Active phase")}. Saturn is near your Moon. Lighter than peak, but still present.'
        hold = 'Stay disciplined. Rewards come later.'
    else:
        anchor = 'Clear sky.'
        line = 'No major transits threatening your chart right now.'
        hold = 'Move with intention. This window won\'t last forever.'

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'next_eclipse': eclipses[0] if eclipses else None,
            'sade_sati': sade,
            'retrogrades': [r.get('planet') if isinstance(r, dict) else str(r) for r in retros],
        },
    }


# ═══════════════════════════════════════════════════════════════
# 9. YEAR MAP
# ═══════════════════════════════════════════════════════════════

def write_year_map(engine):
    dasha = _safe(engine.get_vimshottari_dasha, {}) or {}
    md = dasha.get('mahadasha', {}) or {}
    ad = dasha.get('antardasha', {}) or {}
    md_lord = md.get('lord', '')
    ad_lord = ad.get('lord', '')

    if md_lord:
        meaning = DASHA_MEANING.get(md_lord, f'{md_lord} rules this period.')
        hold = DASHA_HOLD.get(md_lord, 'Move in this direction.')

        if ad_lord and ad_lord != md_lord:
            anchor = f'{md_lord} — {ad_lord}.'
            line = f'{meaning} Within it, {ad_lord} colors the current months.'
        else:
            anchor = f'{md_lord}.'
            line = meaning
    else:
        anchor = str(datetime.now().year) + '.'
        line = 'The year is in motion. Ask the Oracle for specifics.'
        hold = 'Stay awake to what\'s changing.'

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'mahadasha': md_lord,
            'antardasha': ad_lord,
            'md_start': md.get('start_date', ''),
            'md_end': md.get('end_date', ''),
        },
    }


# ═══════════════════════════════════════════════════════════════
# 10. COSMIC NOVEL
# ═══════════════════════════════════════════════════════════════

def write_cosmic_novel(engine):
    dasha = _safe(engine.get_vimshottari_dasha, {}) or {}
    md = dasha.get('mahadasha', {}) or {}
    lord = md.get('lord', '')

    start_yr = md.get('start_year') or md.get('age_start') or 0
    end_yr = md.get('end_year') or md.get('age_end') or 0

    meaning = DASHA_MEANING.get(lord, 'The story deepens.')
    hold = DASHA_HOLD.get(lord, 'Write it honestly.')

    if start_yr and end_yr:
        anchor = f'Ages {int(start_yr)} — {int(end_yr)}.'
        line = f'Your {lord} chapter. {meaning}'
    elif lord:
        anchor = f'The {lord} years.'
        line = meaning
    else:
        anchor = 'Your current chapter.'
        line = 'The dasha is running. Ask the Oracle which one and what it means.'
        hold = ''

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'current_mahadasha': lord,
            'age_start': start_yr,
            'age_end': end_yr,
            'antardasha': (dasha.get('antardasha') or {}).get('lord', ''),
        },
    }


# ═══════════════════════════════════════════════════════════════
# 11. MONEY CALENDAR
# ═══════════════════════════════════════════════════════════════

def write_money_calendar(engine):
    dhana = _safe(engine.get_dhana_yogas, []) or []

    # Try to get wealth-specific timeline events
    timeline = _safe(lambda: engine.get_life_timeline(years=1), {}) or {}
    events = timeline.get('events', []) or []
    wealth_events = [e for e in events if isinstance(e, dict) and
                     any(w in str(e).lower() for w in ['wealth', 'money', 'gain', 'profit', 'income', 'finance'])][:3]

    if wealth_events:
        dates = [_format_date(e.get('date', '')) for e in wealth_events if e.get('date')]
        if dates:
            anchor = ' · '.join(dates[:3]) + '.'
            line = f'{len(dates)} wealth windows in the coming year.'
            hold = 'Mark these. Prepare before, not during.'
        else:
            anchor = 'Windows ahead.'
            line = 'Wealth transits are forming. Ask the Oracle for exact timing.'
            hold = ''
    elif dhana:
        count = len(dhana)
        anchor = f'{count} dhana yoga{"s" if count > 1 else ""}.'
        line = 'Wealth is structural in your chart. Not luck — architecture.'
        hold = 'The architecture pays when its transits fire.'
    else:
        anchor = 'Steady hands.'
        line = 'No dramatic wealth yogas — but 2nd and 11th house lords shape your flow. Ask the Oracle.'
        hold = 'Consistency over windfalls.'

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'dhana_count': len(dhana),
            'wealth_events': wealth_events[:3],
            'dhana_yogas': [str(y)[:100] if isinstance(y, dict) else str(y)[:100] for y in dhana[:5]],
        },
    }


# ═══════════════════════════════════════════════════════════════
# 12. FESTIVALS
# ═══════════════════════════════════════════════════════════════

def write_festivals(engine):
    upcoming = _scan_festivals(engine, days_ahead=60)

    if upcoming:
        name, date_str, meaning, days_away = upcoming[0]
        if days_away == 0:
            anchor = f'{name}. Today.'
            line = meaning
            hold = 'This is the day.'
        elif days_away <= 3:
            anchor = f'{name}.'
            line = meaning
            hold = f'{date_str} — {days_away} day{"s" if days_away > 1 else ""} away.'
        else:
            anchor = f'{name}.'
            line = meaning
            hold = f'{date_str}.'

        # Show next 2 festivals in math
        math_upcoming = [{'name': n, 'date': d, 'days_away': da} for n, d, _, da in upcoming[:3]]
    else:
        anchor = 'Between festivals.'
        line = 'The next sacred day is further than 60 days out. The ordinary teaches too.'
        hold = ''
        math_upcoming = []

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {'upcoming': math_upcoming},
    }


# ═══════════════════════════════════════════════════════════════
# 13. IDEAL PARTNER
# ═══════════════════════════════════════════════════════════════

def write_ideal_partner(engine):
    karakas = _safe(engine.get_jaimini_karakas, {}) or {}
    dk = _get_karaka(karakas, 'Darakaraka')
    dk_planet = dk.get('planet') or dk.get('name') or 'Venus'

    desc = DK_MEANING.get(dk_planet, ('Someone significant.', 'The chart points but doesn\'t force.'))

    anchor = desc[0]
    line = desc[1]
    hold = f'Your darakaraka is {dk_planet}.'

    return {
        'anchor': anchor,
        'line': line,
        'hold': hold,
        'math': {
            'darakaraka': dk_planet,
            'all_karakas': karakas,
        },
    }


# ═══════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════

WRITERS = {
    'daily-vibe':       write_daily_vibe_enriched,
    'power-hours':      write_power_hours_enriched,
    'planet-strength':  _new_planet_strength,
    'year-map':         write_year_map_enriched,
    'danger-radar':     write_danger_radar_enriched,
    'gemstone-profile': write_gemstone_profile_enriched,
    'personal-deities': write_personal_deities,
    'soul-profile':     write_soul_profile_enriched,
    'rare-traits':      write_rare_traits_enriched,
    'cosmic-novel':     write_cosmic_novel,
    'money-calendar':   write_money_calendar_enriched,
    'festivals':        write_festivals,
    'ideal-partner':    write_ideal_partner_enriched,
    'active-yogas':     write_active_yogas,
    'health-map':       write_health_map,
    'career-path':      write_career_path,
    'eclipse-impact':   write_eclipse_impact,
    'nadi-reading':     write_nadi_reading,
    'weekly-forecast':  write_weekly_forecast,
    'numerology':       write_numerology,
    'vastu':            write_vastu,
    'nakshatra-profile': write_nakshatra_profile,
}


def write_feature(feature_id: str, engine, language: str = 'en') -> dict:
    writer = WRITERS.get(feature_id)
    if not writer:
        return {'anchor': '—', 'line': 'Unknown feature.', 'hold': '', 'math': {}}
    try:
        try:
            return writer(engine, language=language)
        except TypeError:
            return writer(engine)
    except Exception as e:
        return {'anchor': '—', 'line': 'The sky is quiet here.', 'hold': '', 'math': {'error': str(e)[:200]}}


def extract_context(engine) -> dict:
    try:
        dash = _safe(engine.get_realtime_dashboard, {}) or {}
        return {
            'sade_sati_peak': 'Peak' in (dash.get('sade_sati') or ''),
            'eclipse_soon': (dash.get('eclipse_proximity') or {}).get('high_impact', 0) > 0,
            'retrograde_count': dash.get('retrogrades_active', 0),
        }
    except Exception:
        return {}
