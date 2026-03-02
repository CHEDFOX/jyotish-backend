"""
Time-Aware + Age-Aware + Psychology-Aware Astrology Analysis
"""

import swisseph as swe
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import re

RASHIS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
          'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha',
    'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]

PLANETS = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
    'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER, 'Venus': swe.VENUS,
    'Saturn': swe.SATURN, 'Rahu': swe.MEAN_NODE,
}

DASHA_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17
}

DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

HOUSE_AREAS = {
    1: 'self', 2: 'wealth', 3: 'courage', 4: 'home', 5: 'creativity',
    6: 'challenges', 7: 'partnership', 8: 'transformation', 9: 'fortune',
    10: 'career', 11: 'gains', 12: 'release'
}

# Planet psychological states
PLANET_PSYCHOLOGY = {
    'Sun': {
        'energy': 'confident, ambitious, seeking recognition',
        'shadow': 'ego, pride, authority issues',
        'emotional_state': 'self-focused, wanting to shine',
        'needs': 'validation, respect, purpose',
        'tone': 'empowering but grounding'
    },
    'Moon': {
        'energy': 'emotional, intuitive, nurturing',
        'shadow': 'moody, anxious, oversensitive',
        'emotional_state': 'emotionally heightened, seeking security',
        'needs': 'comfort, understanding, emotional safety',
        'tone': 'gentle, nurturing, validating'
    },
    'Mars': {
        'energy': 'driven, courageous, action-oriented',
        'shadow': 'angry, impatient, aggressive',
        'emotional_state': 'restless, wanting to act',
        'needs': 'direction, challenge, outlet for energy',
        'tone': 'direct, action-focused, channeling'
    },
    'Mercury': {
        'energy': 'curious, analytical, communicative',
        'shadow': 'scattered, anxious, overthinking',
        'emotional_state': 'mentally active, seeking clarity',
        'needs': 'information, expression, understanding',
        'tone': 'clear, logical, engaging intellect'
    },
    'Jupiter': {
        'energy': 'optimistic, wise, expansive',
        'shadow': 'overconfident, preachy, excessive',
        'emotional_state': 'hopeful, seeking meaning',
        'needs': 'growth, wisdom, faith',
        'tone': 'encouraging, philosophical, uplifting'
    },
    'Venus': {
        'energy': 'loving, artistic, pleasure-seeking',
        'shadow': 'indulgent, vain, dependent',
        'emotional_state': 'seeking love, beauty, harmony',
        'needs': 'connection, beauty, pleasure',
        'tone': 'warm, appreciative, romantic'
    },
    'Saturn': {
        'energy': 'disciplined, responsible, structured',
        'shadow': 'depressed, fearful, pessimistic',
        'emotional_state': 'burdened, seeking stability',
        'needs': 'patience, acknowledgment of struggle, hope',
        'tone': 'patient, validating struggle, realistic hope'
    },
    'Rahu': {
        'energy': 'ambitious, unconventional, obsessive',
        'shadow': 'confused, addicted, illusioned',
        'emotional_state': 'hungry for something undefined',
        'needs': 'clarity, grounding, direction',
        'tone': 'grounding, clarifying, redirecting'
    },
    'Ketu': {
        'energy': 'spiritual, detached, intuitive',
        'shadow': 'disconnected, aimless, escapist',
        'emotional_state': 'feeling lost or transcendent',
        'needs': 'meaning, spiritual connection, acceptance',
        'tone': 'spiritual, accepting, finding meaning in loss'
    }
}


def get_user_age_info(kundli_data: Dict) -> Dict:
    """Calculate user's age and life stage from birth data"""
    
    birth_date = None
    
    # Try multiple paths to find birth date
    if isinstance(kundli_data.get('raw'), dict):
        birth_details = kundli_data['raw'].get('birth_details', {})
        if birth_details.get('date'):
            try:
                birth_date = datetime.strptime(birth_details['date'], '%Y-%m-%d')
            except:
                pass
    
    if not birth_date and kundli_data.get('birth_date'):
        try:
            birth_date = datetime.strptime(kundli_data['birth_date'], '%Y-%m-%d')
        except:
            pass
    
    if not birth_date:
        return {
            'age': None,
            'stage': 'unknown',
            'is_minor': False,
            'appropriate_topics': ['career', 'life', 'growth', 'timing'],
            'avoid_topics': []
        }
    
    today = datetime.now()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    # Determine life stage and appropriate topics
    if age < 13:
        return {
            'age': age,
            'stage': 'child',
            'is_minor': True,
            'appropriate_topics': ['school', 'learning', 'friends', 'hobbies', 'family', 'growth'],
            'avoid_topics': ['marriage', 'romance', 'love', 'partner', 'relationship', 'career', 'job', 'money', 'investment'],
            'guidance': 'User is a CHILD. Focus on school, friendships, learning, and personal growth. NEVER discuss romance, marriage, or adult topics.'
        }
    elif age < 18:
        return {
            'age': age,
            'stage': 'teenager',
            'is_minor': True,
            'appropriate_topics': ['education', 'exams', 'career direction', 'friendships', 'self-discovery', 'skills'],
            'avoid_topics': ['marriage', 'having children', 'serious romance', 'investments'],
            'guidance': 'User is a TEENAGER. Focus on education, future career, self-discovery. Avoid marriage, serious romance, or adult financial advice.'
        }
    elif age < 25:
        return {
            'age': age,
            'stage': 'young_adult',
            'is_minor': False,
            'appropriate_topics': ['career', 'education', 'relationships', 'love', 'self-discovery', 'travel', 'growth'],
            'avoid_topics': [],
            'guidance': 'User is a YOUNG ADULT. Open to all topics but focus on career building, relationships, and self-discovery.'
        }
    elif age < 35:
        return {
            'age': age,
            'stage': 'adult',
            'is_minor': False,
            'appropriate_topics': ['career', 'marriage', 'relationships', 'children', 'wealth', 'property', 'growth'],
            'avoid_topics': [],
            'guidance': 'User is an ADULT in prime years. All topics appropriate including marriage, children, career advancement.'
        }
    elif age < 50:
        return {
            'age': age,
            'stage': 'middle_adult',
            'is_minor': False,
            'appropriate_topics': ['career', 'family', 'wealth', 'health', 'children', 'legacy', 'stability'],
            'avoid_topics': [],
            'guidance': 'User is in MIDDLE ADULTHOOD. Focus on stability, family, career peak, health, legacy.'
        }
    elif age < 65:
        return {
            'age': age,
            'stage': 'mature_adult',
            'is_minor': False,
            'appropriate_topics': ['health', 'family', 'grandchildren', 'retirement', 'legacy', 'wisdom', 'spiritual growth'],
            'avoid_topics': ['having children'],
            'guidance': 'User is a MATURE ADULT. Focus on health, family, retirement planning, grandchildren, legacy. Avoid suggesting having children.'
        }
    else:
        return {
            'age': age,
            'stage': 'elder',
            'is_minor': False,
            'appropriate_topics': ['health', 'family', 'spirituality', 'peace', 'legacy', 'wisdom', 'grandchildren'],
            'avoid_topics': ['having children', 'new career', 'marriage'],
            'guidance': 'User is an ELDER. Focus on health, peace, family, spirituality, and legacy. Avoid suggesting major life changes like new career or having children.'
        }


def get_psychological_state(kundli_data: Dict) -> Dict:
    """Analyze user's current psychological state based on dashas and transits"""
    
    # Get current dasha lords
    current_dasha = kundli_data.get('current_dasha', {})
    maha_lord = current_dasha.get('lord', 'Sun')
    
    # Get psychology for mahadasha
    maha_psych = PLANET_PSYCHOLOGY.get(maha_lord, PLANET_PSYCHOLOGY['Sun'])
    
    # Try to get antardasha (if available)
    antar_lord = kundli_data.get('antardasha', {}).get('lord', maha_lord)
    antar_psych = PLANET_PSYCHOLOGY.get(antar_lord, maha_psych)
    
    # Combine psychological states
    return {
        'primary_energy': maha_psych['energy'],
        'secondary_energy': antar_psych['energy'],
        'emotional_state': maha_psych['emotional_state'],
        'shadow_risk': maha_psych['shadow'],
        'needs': maha_psych['needs'],
        'recommended_tone': maha_psych['tone'],
        'combined_state': f"{maha_lord}-{antar_lord} period: {maha_psych['energy']}, currently {antar_psych['emotional_state']}"
    }


def get_transits_for_date(target_date: datetime) -> Dict:
    """Calculate planetary positions for any date"""
    julian_day = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
    
    transits = {}
    for planet, planet_id in PLANETS.items():
        result = swe.calc_ut(julian_day, planet_id)
        longitude = result[0][0] if isinstance(result[0], (tuple, list)) else result[0]
        rashi_index = int(longitude / 30)
        
        transits[planet] = {
            'rashi': RASHIS[rashi_index],
            'rashi_index': rashi_index,
            'degree': round(longitude % 30, 2),
            'nakshatra': NAKSHATRAS[int(longitude / 13.333333) % 27],
        }
    
    # Ketu
    rahu_long = transits['Rahu']['rashi_index'] * 30 + transits['Rahu']['degree']
    ketu_long = (rahu_long + 180) % 360
    transits['Ketu'] = {
        'rashi': RASHIS[int(ketu_long / 30)],
        'rashi_index': int(ketu_long / 30),
        'degree': round(ketu_long % 30, 2),
    }
    
    return transits


def get_transit_houses(transits: Dict, ascendant_index: int) -> Dict:
    """Calculate which house each planet transits"""
    houses = {}
    for planet, data in transits.items():
        house = ((data['rashi_index'] - ascendant_index) % 12) + 1
        houses[planet] = {'house': house, 'area': HOUSE_AREAS[house]}
    return houses


def get_dasha_for_date(kundli_data: Dict, target_date: datetime) -> Dict:
    """Calculate dasha periods for target date"""
    current_dasha = kundli_data.get('current_dasha', {})
    if not current_dasha:
        return {}
    
    maha_lord = current_dasha.get('lord', 'Sun')
    try:
        maha_start = datetime.strptime(current_dasha.get('start', '2020-01-01'), '%Y-%m-%d')
        maha_end = datetime.strptime(current_dasha.get('end', '2030-01-01'), '%Y-%m-%d')
    except:
        return {'mahadasha': maha_lord, 'antardasha': maha_lord}
    
    # Find correct mahadasha if target outside current
    if target_date >= maha_end:
        lord_index = DASHA_ORDER.index(maha_lord)
        dasha_start = maha_end
        for i in range(1, 10):
            lord = DASHA_ORDER[(lord_index + i) % 9]
            dasha_days = DASHA_YEARS[lord] * 365.25
            dasha_end = dasha_start + timedelta(days=dasha_days)
            if dasha_start <= target_date < dasha_end:
                maha_lord, maha_start, maha_end = lord, dasha_start, dasha_end
                break
            dasha_start = dasha_end
    
    # Calculate Antardasha
    maha_total_days = (maha_end - maha_start).days
    lord_index = DASHA_ORDER.index(maha_lord)
    
    antar_start = maha_start
    antar_lord = maha_lord
    antar_end = maha_end
    
    for i in range(9):
        planet = DASHA_ORDER[(lord_index + i) % 9]
        antar_days = (DASHA_YEARS[planet] / 120) * maha_total_days
        antar_end = antar_start + timedelta(days=antar_days)
        if antar_start <= target_date < antar_end:
            antar_lord = planet
            break
        antar_start = antar_end
    
    return {
        'mahadasha': maha_lord,
        'antardasha': antar_lord,
        'maha_end': maha_end.strftime('%Y-%m-%d'),
        'antar_end': antar_end.strftime('%Y-%m-%d'),
    }


def extract_time_from_query(query: str) -> Optional[Dict]:
    """Extract time reference from user's question"""
    query_lower = query.lower()
    now = datetime.now()
    
    # Month + Year
    month_year = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})', query_lower)
    if month_year:
        months = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                  'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
        return {'type': 'month', 'date': datetime(int(month_year.group(2)), months[month_year.group(1)], 15),
                'description': f"{month_year.group(1).title()} {month_year.group(2)}"}
    
    # Year only
    year_match = re.search(r'\b(20\d{2})\b', query_lower)
    if year_match:
        year = int(year_match.group(1))
        return {'type': 'year', 'date': datetime(year, 6, 15), 'description': str(year)}
    
    # Relative time
    if 'next year' in query_lower:
        return {'type': 'year', 'date': datetime(now.year + 1, 6, 15), 'description': str(now.year + 1)}
    if 'next month' in query_lower:
        next_month = now.month + 1 if now.month < 12 else 1
        next_year = now.year if now.month < 12 else now.year + 1
        return {'type': 'month', 'date': datetime(next_year, next_month, 15), 'description': 'next month'}
    if 'this year' in query_lower:
        return {'type': 'year', 'date': now, 'description': str(now.year)}
    if 'tomorrow' in query_lower:
        return {'type': 'day', 'date': now + timedelta(days=1), 'description': 'tomorrow'}
    if 'next week' in query_lower:
        return {'type': 'week', 'date': now + timedelta(days=7), 'description': 'next week'}
    
    # "When" questions
    if query_lower.startswith('when') or 'best time' in query_lower or 'right time' in query_lower or 'should i' in query_lower:
        return {'type': 'when_question', 'date': None, 'description': 'finding best time'}
    
    return None


def get_search_years_for_topic(topic: str, age_info: Dict) -> int:
    """Determine how many years to search based on topic and age"""
    
    topic_lower = topic.lower()
    age = age_info.get('age', 30)
    stage = age_info.get('stage', 'adult')
    
    # Marriage: search more years for younger people
    if any(w in topic_lower for w in ['marry', 'marriage', 'wedding', 'spouse']):
        if stage == 'young_adult':
            return 7  # 7 years
        elif stage == 'adult':
            return 5
        else:
            return 3
    
    # Children: depends heavily on age
    if any(w in topic_lower for w in ['child', 'baby', 'pregnant', 'kids']):
        if age < 35:
            return 10
        elif age < 42:
            return 5
        else:
            return 2
    
    # Career: varies
    if any(w in topic_lower for w in ['job', 'career', 'promotion', 'business']):
        if stage in ['young_adult', 'adult']:
            return 5
        else:
            return 3
    
    # Default
    return 3


def find_best_periods(kundli_data: Dict, purpose: str, age_info: Dict) -> List[Dict]:
    """Find favorable periods for a purpose with age-appropriate duration"""
    
    purpose_lower = purpose.lower()
    
    # Check if topic is appropriate for age
    avoid_topics = age_info.get('avoid_topics', [])
    for avoid in avoid_topics:
        if avoid in purpose_lower:
            return [{'blocked': True, 'reason': f"Topic not appropriate for {age_info.get('stage', 'user')}'s life stage"}]
    
    # Determine target house
    if any(w in purpose_lower for w in ['marry', 'marriage', 'wedding', 'relationship', 'partner', 'love']):
        target_house = 7
    elif any(w in purpose_lower for w in ['job', 'career', 'promotion', 'work', 'business']):
        target_house = 10
    elif any(w in purpose_lower for w in ['money', 'wealth', 'invest', 'property']):
        target_house = 2
    elif any(w in purpose_lower for w in ['travel', 'abroad', 'foreign', 'move']):
        target_house = 9
    elif any(w in purpose_lower for w in ['child', 'baby', 'pregnant']):
        target_house = 5
    elif any(w in purpose_lower for w in ['education', 'study', 'exam', 'learn']):
        target_house = 5
    elif any(w in purpose_lower for w in ['health', 'medical', 'surgery']):
        target_house = 6
    else:
        target_house = 1
    
    # Get ascendant
    ascendant_index = 0
    if isinstance(kundli_data.get('ascendant'), dict):
        ascendant_index = kundli_data['ascendant'].get('rashi_index', 0)
    elif isinstance(kundli_data.get('ascendant'), str):
        asc_map = {name: i for i, name in enumerate(RASHIS)}
        ascendant_index = asc_map.get(kundli_data.get('ascendant'), 0)
    
    # Determine search duration
    years_to_search = get_search_years_for_topic(purpose, age_info)
    months_to_search = years_to_search * 12
    
    good_periods = []
    now = datetime.now()
    
    for m in range(0, months_to_search, 2):  # Check every 2 months
        check_date = now + timedelta(days=30 * m)
        transits = get_transits_for_date(check_date)
        houses = get_transit_houses(transits, ascendant_index)
        dashas = get_dasha_for_date(kundli_data, check_date)
        
        jupiter_house = houses['Jupiter']['house']
        saturn_house = houses['Saturn']['house']
        venus_house = houses.get('Venus', {}).get('house', 1)
        
        score = 0
        reasons = []
        
        # Jupiter in favorable position
        if jupiter_house == target_house:
            score += 3
            reasons.append('strong blessing')
        elif jupiter_house in [1, 5, 9, 11]:
            score += 2
            reasons.append('supportive energy')
        
        # Saturn not afflicting
        if saturn_house != target_house:
            score += 1
            reasons.append('no major blocks')
        
        # Venus for relationship matters
        if target_house == 7 and venus_house in [1, 5, 7, 11]:
            score += 2
            reasons.append('love energy strong')
        
        # Favorable dasha
        antar_lord = dashas.get('antardasha', '')
        if antar_lord == 'Jupiter':
            score += 2
            reasons.append('growth period')
        elif antar_lord == 'Venus' and target_house in [5, 7]:
            score += 2
            reasons.append('love period')
        elif antar_lord == 'Sun' and target_house == 10:
            score += 2
            reasons.append('recognition period')
        
        if score >= 3:
            good_periods.append({
                'month': check_date.strftime('%B %Y'),
                'date': check_date,
                'score': score,
                'reasons': reasons
            })
    
    # Sort by score
    good_periods.sort(key=lambda x: x['score'], reverse=True)
    return good_periods[:5]


def generate_time_aware_guidance(kundli_data: Dict, query: str) -> str:
    """Generate complete guidance for Oracle"""
    
    # Get age info
    age_info = get_user_age_info(kundli_data)
    
    # Get psychological state
    psych_state = get_psychological_state(kundli_data)
    
    # Extract time reference
    time_ref = extract_time_from_query(query)
    
    # Build guidance
    guidance = f"""
AGE CONTEXT:
- Age: {age_info.get('age', 'unknown')}
- Life Stage: {age_info.get('stage', 'unknown')}
- Is Minor: {age_info.get('is_minor', False)}
- Guidance: {age_info.get('guidance', 'No restrictions')}
- Avoid Topics: {', '.join(age_info.get('avoid_topics', [])) or 'None'}

PSYCHOLOGICAL STATE:
- Current Energy: {psych_state.get('primary_energy', 'unknown')}
- Emotional State: {psych_state.get('emotional_state', 'unknown')}
- Shadow Risk: {psych_state.get('shadow_risk', 'unknown')}
- User Needs: {psych_state.get('needs', 'unknown')}
- Recommended Tone: {psych_state.get('recommended_tone', 'warm')}
"""
    
    if not time_ref:
        return guidance
    
    # Handle "when" questions
    if time_ref['type'] == 'when_question':
        best = find_best_periods(kundli_data, query, age_info)
        
        if best and best[0].get('blocked'):
            guidance += f"\nTOPIC BLOCKED: {best[0].get('reason')}"
            return guidance
        
        if best:
            guidance += "\nBEST PERIODS FOUND:\n"
            for i, p in enumerate(best[:3], 1):
                guidance += f"{i}. {p['month']} (score: {p['score']}/8) - {', '.join(p['reasons'])}\n"
        return guidance
    
    # Analyze specific time
    target_date = time_ref['date']
    
    ascendant_index = 0
    if isinstance(kundli_data.get('ascendant'), dict):
        ascendant_index = kundli_data['ascendant'].get('rashi_index', 0)
    elif isinstance(kundli_data.get('ascendant'), str):
        asc_map = {name: i for i, name in enumerate(RASHIS)}
        ascendant_index = asc_map.get(kundli_data.get('ascendant'), 0)
    
    transits = get_transits_for_date(target_date)
    houses = get_transit_houses(transits, ascendant_index)
    dashas = get_dasha_for_date(kundli_data, target_date)
    
    guidance += f"""
TIME ASKED: {time_ref['description']}

TRANSITS:
- Jupiter in {houses['Jupiter']['area']} (house {houses['Jupiter']['house']})
- Saturn in {houses['Saturn']['area']} (house {houses['Saturn']['house']})
- Venus in {houses.get('Venus', {}).get('area', 'unknown')}

DASHA: {dashas.get('mahadasha', '?')}-{dashas.get('antardasha', '?')} period

THEMES:
- Growth: {houses['Jupiter']['area']}
- Work/Lessons: {houses['Saturn']['area']}
- Karma: {houses.get('Rahu', {}).get('area', 'unknown')}
"""
    
    return guidance


def generate_relationship_context(kundli_data: Dict, partner_kundli: Dict = None) -> str:
    """Generate context for relationship/matchmaking mode"""
    
    age_info = get_user_age_info(kundli_data)
    
    if age_info.get('is_minor'):
        return "USER IS A MINOR. Do NOT provide romantic or marriage advice. Focus only on friendships and family relationships."
    
    context = f"""
RELATIONSHIP MODE ACTIVE

USER PROFILE:
- Age: {age_info.get('age', 'unknown')}
- Life Stage: {age_info.get('stage', 'unknown')}
- 7th House: Partnership
- Venus Position: Love nature

CONTEXT: User is seeking relationship guidance.
TONE: Warm, supportive, insightful about relationship dynamics.
"""
    
    if partner_kundli:
        context += """
PARTNER DATA PROVIDED: Yes
- Analyze compatibility
- Note strengths and challenges
- Be balanced and constructive
- Never be deterministic ("you're incompatible") - show nuance
"""
    
    return context
