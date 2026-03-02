"""
Real-time Astrological State Calculator
Analyzes user's current mental/emotional state based on:
1. Mahadasha + Antardasha + Pratyantardasha
2. Current transits
3. Transit-to-natal aspects
4. Moon's current nakshatra
"""

from datetime import datetime, timedelta
import swisseph as swe

# Initialize Swiss Ephemeris
swe.set_ephe_path('/usr/share/ephe')

# Constants
RASHIS = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya', 
          'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena']

RASHIS_ENGLISH = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                  'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha',
    'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]

# Dasha periods in years
DASHA_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17
}

DASHA_SEQUENCE = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

# Planet psychological profiles
PLANET_PSYCHOLOGY = {
    'Sun': {
        'quality': 'confident and ambitious',
        'shadow': 'ego and pride',
        'need': 'recognition and respect',
        'emotions': ['confident', 'proud', 'authoritative', 'sometimes arrogant'],
        'approach': 'Validate their confidence but gently check ego. They need to feel respected.'
    },
    'Moon': {
        'quality': 'emotional and intuitive',
        'shadow': 'moody and oversensitive',
        'need': 'emotional security and nurturing',
        'emotions': ['sensitive', 'nurturing', 'moody', 'intuitive'],
        'approach': 'Be extra gentle and nurturing. Acknowledge their feelings before giving advice.'
    },
    'Mars': {
        'quality': 'driven and energetic',
        'shadow': 'aggressive and impatient',
        'need': 'action and achievement',
        'emotions': ['passionate', 'impatient', 'competitive', 'courageous'],
        'approach': 'Be direct and action-oriented. Channel their energy productively. Warn about impulsiveness.'
    },
    'Mercury': {
        'quality': 'analytical and communicative',
        'shadow': 'scattered and anxious',
        'need': 'mental stimulation and expression',
        'emotions': ['curious', 'analytical', 'nervous', 'adaptable'],
        'approach': 'Engage their intellect. Give clear, logical explanations. Help focus scattered thoughts.'
    },
    'Jupiter': {
        'quality': 'optimistic and wise',
        'shadow': 'overconfident and preachy',
        'need': 'growth and meaning',
        'emotions': ['optimistic', 'generous', 'philosophical', 'expansive'],
        'approach': 'Encourage their growth and optimism. Add practical grounding to big dreams.'
    },
    'Venus': {
        'quality': 'loving and artistic',
        'shadow': 'indulgent and vain',
        'need': 'love and beauty',
        'emotions': ['romantic', 'pleasure-seeking', 'artistic', 'harmonious'],
        'approach': 'Be warm and aesthetically pleasing. Support relationships and creative pursuits.'
    },
    'Saturn': {
        'quality': 'disciplined and responsible',
        'shadow': 'depressed and pessimistic',
        'need': 'structure and achievement through effort',
        'emotions': ['burdened', 'serious', 'patient', 'melancholic'],
        'approach': 'Acknowledge their struggles. Be patient and validating. Remind them difficulties build strength.'
    },
    'Rahu': {
        'quality': 'ambitious and unconventional',
        'shadow': 'obsessive and confused',
        'need': 'worldly achievement and new experiences',
        'emotions': ['restless', 'ambitious', 'confused', 'obsessive'],
        'approach': 'Help them see through illusions. Ground obsessive thoughts. Validate ambition but add realism.'
    },
    'Ketu': {
        'quality': 'spiritual and detached',
        'shadow': 'disconnected and aimless',
        'need': 'spiritual liberation and letting go',
        'emotions': ['detached', 'spiritual', 'confused', 'liberating'],
        'approach': 'Honor their spiritual seeking. Support letting go. Don\'t force material concerns.'
    }
}

# House meanings for transits
HOUSE_MEANINGS = {
    1: 'self, personality, physical body',
    2: 'wealth, family, speech',
    3: 'courage, siblings, communication',
    4: 'home, mother, emotions, peace of mind',
    5: 'children, creativity, intelligence, romance',
    6: 'enemies, health issues, daily work',
    7: 'marriage, partnerships, business',
    8: 'transformation, sudden events, hidden matters',
    9: 'luck, father, higher learning, spirituality',
    10: 'career, reputation, public life',
    11: 'gains, friends, aspirations',
    12: 'losses, expenses, spirituality, foreign lands'
}


def get_current_transits():
    """Get current planetary positions"""
    now = datetime.utcnow()
    jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60)
    
    planets = {
        'Sun': swe.SUN,
        'Moon': swe.MOON,
        'Mars': swe.MARS,
        'Mercury': swe.MERCURY,
        'Jupiter': swe.JUPITER,
        'Venus': swe.VENUS,
        'Saturn': swe.SATURN,
        'Rahu': swe.MEAN_NODE,
    }
    
    transits = {}
    for name, planet_id in planets.items():
        pos = swe.calc_ut(jd, planet_id)[0][0]
        rashi_index = int(pos / 30)
        degree = pos % 30
        nakshatra_index = int(pos / 13.333333)
        
        transits[name] = {
            'longitude': pos,
            'rashi_index': rashi_index,
            'rashi': RASHIS[rashi_index],
            'rashi_english': RASHIS_ENGLISH[rashi_index],
            'degree': round(degree, 2),
            'nakshatra': NAKSHATRAS[nakshatra_index] if nakshatra_index < 27 else NAKSHATRAS[0]
        }
    
    # Ketu is opposite Rahu
    rahu_long = transits['Rahu']['longitude']
    ketu_long = (rahu_long + 180) % 360
    ketu_rashi_index = int(ketu_long / 30)
    ketu_nakshatra_index = int(ketu_long / 13.333333)
    transits['Ketu'] = {
        'longitude': ketu_long,
        'rashi_index': ketu_rashi_index,
        'rashi': RASHIS[ketu_rashi_index],
        'rashi_english': RASHIS_ENGLISH[ketu_rashi_index],
        'degree': round(ketu_long % 30, 2),
        'nakshatra': NAKSHATRAS[ketu_nakshatra_index] if ketu_nakshatra_index < 27 else NAKSHATRAS[0]
    }
    
    return transits


def calculate_antardasha(mahadasha_lord, mahadasha_start, mahadasha_end, current_date=None):
    """Calculate current Antardasha and Pratyantardasha within Mahadasha"""
    if current_date is None:
        current_date = datetime.now()
    
    if not mahadasha_lord or not mahadasha_start or not mahadasha_end:
        return None
    
    # Parse dates
    if isinstance(mahadasha_start, str):
        mahadasha_start_dt = datetime.strptime(mahadasha_start, '%Y-%m-%d')
    else:
        mahadasha_start_dt = mahadasha_start
        
    if isinstance(mahadasha_end, str):
        mahadasha_end_dt = datetime.strptime(mahadasha_end, '%Y-%m-%d')
    else:
        mahadasha_end_dt = mahadasha_end
    
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
    
    # Find starting position in sequence
    try:
        start_idx = DASHA_SEQUENCE.index(mahadasha_lord)
    except ValueError:
        return None
        
    ordered_sequence = DASHA_SEQUENCE[start_idx:] + DASHA_SEQUENCE[:start_idx]
    
    # Calculate total mahadasha days
    total_days = (mahadasha_end_dt - mahadasha_start_dt).days
    
    # Calculate each antardasha
    current_start = mahadasha_start_dt
    for planet in ordered_sequence:
        # Antardasha duration = (planet's years / 120) * mahadasha days
        antardasha_days = (DASHA_YEARS[planet] / 120) * total_days
        antardasha_end = current_start + timedelta(days=antardasha_days)
        
        if current_start <= current_date < antardasha_end:
            # Found current antardasha, now calculate pratyantardasha
            pratyantardasha = calculate_pratyantardasha(
                planet, current_start, antardasha_end, current_date, ordered_sequence
            )
            
            days_remaining = (antardasha_end - current_date).days
            
            return {
                'lord': planet,
                'start': current_start.strftime('%Y-%m-%d'),
                'end': antardasha_end.strftime('%Y-%m-%d'),
                'days_remaining': days_remaining,
                'pratyantardasha': pratyantardasha
            }
        
        current_start = antardasha_end
    
    return None


def calculate_pratyantardasha(antardasha_lord, antardasha_start, antardasha_end, current_date, sequence):
    """Calculate current Pratyantardasha within Antardasha"""
    try:
        start_idx = sequence.index(antardasha_lord)
    except ValueError:
        return None
        
    ordered_sequence = sequence[start_idx:] + sequence[:start_idx]
    
    total_days = (antardasha_end - antardasha_start).days
    
    current_start = antardasha_start
    for planet in ordered_sequence:
        pratya_days = (DASHA_YEARS[planet] / 120) * total_days
        pratya_end = current_start + timedelta(days=pratya_days)
        
        if current_start <= current_date < pratya_end:
            days_remaining = (pratya_end - current_date).days
            return {
                'lord': planet,
                'start': current_start.strftime('%Y-%m-%d'),
                'end': pratya_end.strftime('%Y-%m-%d'),
                'days_remaining': days_remaining
            }
        
        current_start = pratya_end
    
    return None


def get_transit_house(transit_rashi_index, ascendant_rashi_index):
    """Calculate which house a transiting planet is in relative to ascendant"""
    house = ((transit_rashi_index - ascendant_rashi_index) % 12) + 1
    return house


def analyze_mental_state(kundli_data, current_date=None):
    """
    Main function: Analyze user's current mental/emotional state
    Returns comprehensive astrological analysis for Oracle
    """
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
    
    # Get current transits
    transits = get_current_transits()
    
    # Get user's ascendant rashi index
    ascendant = kundli_data.get('ascendant', {})
    if isinstance(ascendant, dict):
        asc_rashi_index = ascendant.get('rashi_index', 0)
    else:
        asc_rashi_index = 0
    
    # Get mahadasha info
    mahadasha = kundli_data.get('current_dasha', {})
    if isinstance(mahadasha, dict):
        mahadasha_lord = mahadasha.get('lord') or mahadasha.get('planet')
        mahadasha_start = mahadasha.get('start')
        mahadasha_end = mahadasha.get('end')
    else:
        mahadasha_lord = None
        mahadasha_start = None
        mahadasha_end = None
    
    # Calculate current antardasha and pratyantardasha
    antardasha = calculate_antardasha(
        mahadasha_lord,
        mahadasha_start,
        mahadasha_end,
        current_date
    )
    
    # Analyze transit positions relative to user's ascendant
    transit_analysis = {}
    significant_transits = []
    
    for planet, data in transits.items():
        house = get_transit_house(data['rashi_index'], asc_rashi_index)
        transit_analysis[planet] = {
            'current_rashi': data['rashi_english'],
            'house_from_ascendant': house,
            'house_meaning': HOUSE_MEANINGS.get(house, ''),
            'nakshatra': data['nakshatra']
        }
        
        # Identify significant transits
        if planet == 'Saturn' and house in [1, 4, 7, 8, 10, 12]:
            significant_transits.append(f"Saturn transiting {house}th house ({HOUSE_MEANINGS[house]}): Challenges and lessons in this area")
        elif planet == 'Jupiter' and house in [1, 5, 9, 11]:
            significant_transits.append(f"Jupiter transiting {house}th house ({HOUSE_MEANINGS[house]}): Growth and blessings here")
        elif planet == 'Rahu' and house in [1, 7, 10]:
            significant_transits.append(f"Rahu transiting {house}th house ({HOUSE_MEANINGS[house]}): Intense desires and obsessions in this area")
        elif planet == 'Ketu' and house in [1, 4, 12]:
            significant_transits.append(f"Ketu transiting {house}th house ({HOUSE_MEANINGS[house]}): Detachment and spiritual lessons here")
    
    # Get psychological profiles
    mahadasha_psych = PLANET_PSYCHOLOGY.get(mahadasha_lord, PLANET_PSYCHOLOGY['Sun'])
    
    antardasha_lord = antardasha.get('lord') if antardasha else None
    antardasha_psych = PLANET_PSYCHOLOGY.get(antardasha_lord, {}) if antardasha_lord else {}
    
    pratya_lord = antardasha.get('pratyantardasha', {}).get('lord') if antardasha else None
    pratya_psych = PLANET_PSYCHOLOGY.get(pratya_lord, {}) if pratya_lord else {}
    
    # Generate Oracle guidance
    oracle_guidance = generate_oracle_guidance(
        mahadasha_lord, mahadasha_psych,
        antardasha_lord, antardasha_psych, antardasha,
        pratya_lord, pratya_psych,
        transits['Moon']['nakshatra'],
        significant_transits,
        transit_analysis
    )
    
    return {
        'current_datetime': current_date.strftime('%Y-%m-%d %H:%M'),
        'mahadasha': {
            'lord': mahadasha_lord,
            'start': mahadasha_start,
            'end': mahadasha_end
        },
        'antardasha': antardasha,
        'transits': transit_analysis,
        'moon_nakshatra': transits['Moon']['nakshatra'],
        'significant_transits': significant_transits,
        'oracle_guidance': oracle_guidance
    }


def generate_oracle_guidance(
    mahadasha_lord, mahadasha_psych,
    antardasha_lord, antardasha_psych, antardasha_data,
    pratya_lord, pratya_psych,
    moon_nakshatra,
    significant_transits,
    transit_analysis
):
    """Generate comprehensive guidance for Oracle on how to respond"""
    
    # Calculate days remaining
    antardasha_days = antardasha_data.get('days_remaining', 0) if antardasha_data else 0
    pratya_days = antardasha_data.get('pratyantardasha', {}).get('days_remaining', 0) if antardasha_data else 0
    
    guidance = f"""
═══════════════════════════════════════════════════════════════
           REAL-TIME ASTROLOGICAL STATE ANALYSIS
═══════════════════════════════════════════════════════════════

🔮 CURRENT DASHA PERIODS:
─────────────────────────
- MAHADASHA (Major Period): {mahadasha_lord or 'Unknown'}
  - Quality: {mahadasha_psych.get('quality', 'N/A')}
  - Shadow: {mahadasha_psych.get('shadow', 'N/A')}
  - Core Need: {mahadasha_psych.get('need', 'N/A')}

- ANTARDASHA (Sub-Period): {antardasha_lord or 'Unknown'}
  - Quality: {antardasha_psych.get('quality', 'N/A')}
  - Shadow: {antardasha_psych.get('shadow', 'N/A')}
  - Days Remaining: {antardasha_days} days
  
- PRATYANTARDASHA (Sub-Sub): {pratya_lord or 'Unknown'}
  - Quality: {pratya_psych.get('quality', 'N/A')}
  - Days Remaining: {pratya_days} days

🌙 MOON'S CURRENT NAKSHATRA: {moon_nakshatra}
   (This colors today's emotional atmosphere)

⚡ SIGNIFICANT TRANSITS RIGHT NOW:
─────────────────────────────────
{chr(10).join('• ' + t for t in significant_transits) if significant_transits else '• No major challenging transits currently'}

🧠 USER'S LIKELY MENTAL STATE:
──────────────────────────────
Primary Energy: {mahadasha_psych.get('quality', 'balanced')}
Current Influence: {antardasha_psych.get('quality', 'neutral')}
Immediate Mood: {pratya_psych.get('quality', 'stable')}
Possible Emotions: {', '.join(mahadasha_psych.get('emotions', ['balanced'])[:2] + antardasha_psych.get('emotions', [])[:2])}

💡 HOW TO RESPOND TO THIS USER:
───────────────────────────────
{mahadasha_psych.get('approach', 'Be balanced and supportive.')}

{antardasha_psych.get('approach', '') if antardasha_psych else ''}

SPECIFIC TIMING TO MENTION:
- Antardasha of {antardasha_lord} ends in {antardasha_days} days
- Current sub-sub period ({pratya_lord}) shifts in {pratya_days} days
- Use these for specific predictions when relevant

═══════════════════════════════════════════════════════════════
"""
    
    return guidance
