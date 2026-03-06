"""
JYOTISH ENGINE - QUERY ANALYZER
Complete analysis pipeline for any user question
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..jyotish_engine import JyotishEngine
from ..core.constants import RASHI_NAMES, RASHI_LORDS


class QueryAnalyzer:
    """
    Comprehensive query analysis using all Jyotish systems
    
    Pipeline:
    1. House Analysis (which house governs this topic)
    2. Timing Analysis (dasha + transits)
    3. Jaimini Analysis (if relationship-related)
    4. Yoga Analysis (relevant yogas)
    5. Synthesis (combine all findings)
    """
    
    TOPIC_HOUSES = {
        'MARRIAGE': {'primary': 7, 'secondary': [2, 11], 'karaka': 'Venus'},
        'LOVE': {'primary': 5, 'secondary': [7, 11], 'karaka': 'Venus'},
        'DIVORCE': {'primary': 7, 'secondary': [6, 8, 12], 'karaka': 'Venus'},
        'CHILDREN': {'primary': 5, 'secondary': [2, 11], 'karaka': 'Jupiter'},
        'PREGNANCY': {'primary': 5, 'secondary': [1, 9], 'karaka': 'Jupiter'},
        'JOB': {'primary': 10, 'secondary': [6, 2, 11], 'karaka': 'Saturn'},
        'CAREER': {'primary': 10, 'secondary': [1, 9, 11], 'karaka': 'Sun'},
        'PROMOTION': {'primary': 10, 'secondary': [11, 9], 'karaka': 'Sun'},
        'BUSINESS': {'primary': 7, 'secondary': [10, 11, 2], 'karaka': 'Mercury'},
        'MONEY': {'primary': 2, 'secondary': [11, 5, 9], 'karaka': 'Jupiter'},
        'WEALTH': {'primary': 2, 'secondary': [11, 5, 9], 'karaka': 'Jupiter'},
        'PROPERTY': {'primary': 4, 'secondary': [2, 11], 'karaka': 'Mars'},
        'EDUCATION': {'primary': 4, 'secondary': [5, 9], 'karaka': 'Jupiter'},
        'ABROAD': {'primary': 12, 'secondary': [9, 7, 3], 'karaka': 'Rahu'},
        'VISA': {'primary': 12, 'secondary': [9, 3], 'karaka': 'Rahu'},
        'HEALTH': {'primary': 1, 'secondary': [6, 8], 'karaka': 'Sun'},
        'FATHER': {'primary': 9, 'secondary': [10], 'karaka': 'Sun'},
        'MOTHER': {'primary': 4, 'secondary': [1], 'karaka': 'Moon'},
        'SIBLINGS': {'primary': 3, 'secondary': [11], 'karaka': 'Mars'},
        'SPIRITUAL': {'primary': 9, 'secondary': [12, 5], 'karaka': 'Jupiter'},
        'LUCK': {'primary': 9, 'secondary': [1, 5, 11], 'karaka': 'Jupiter'},
        'GENERAL': {'primary': 1, 'secondary': [9, 10], 'karaka': 'Sun'},
    }
    
    def __init__(self, engine: JyotishEngine):
        self.engine = engine
        self.engine._ensure_chart()
    
    def analyze(self, category: str, question_type: str = 'GUIDANCE',
                search_months: int = 24) -> Dict:
        """Complete analysis for a query"""
        
        category = category.upper()
        topic = self.TOPIC_HOUSES.get(category, self.TOPIC_HOUSES['GENERAL'])
        
        # 1. House Analysis
        house_analysis = self._analyze_house(topic['primary'], topic['karaka'])
        
        # 2. Timing Analysis
        timing = self._analyze_timing(topic['primary'], topic['karaka'], search_months)
        
        # 3. Jaimini (for relationships)
        jaimini = None
        if category in ['MARRIAGE', 'LOVE', 'SPOUSE', 'DIVORCE', 'BOYFRIEND', 'GIRLFRIEND']:
            jaimini = self._analyze_jaimini_marriage()
        
        # 4. Relevant Yogas
        yogas = self._find_relevant_yogas(category)
        
        # 5. Current State
        current = self._current_state()
        
        # 6. Synthesize
        synthesis = self._synthesize(category, house_analysis, timing, jaimini, yogas, current)
        
        return {
            'category': category,
            'question_type': question_type,
            'house_analysis': house_analysis,
            'timing': timing,
            'jaimini': jaimini,
            'yogas': yogas,
            'current_state': current,
            'synthesis': synthesis,
        }
    
    def _analyze_house(self, house: int, karaka: str) -> Dict:
        """Analyze the primary house for the topic"""
        planets = self.engine.planets
        asc_rashi = self.engine.ascendant_rashi
        
        # House rashi and lord
        house_rashi = (asc_rashi + house - 1) % 12
        house_lord = RASHI_LORDS[house_rashi]
        lord_data = planets.get(house_lord, {})
        
        # Planets in house
        planets_in_house = [p for p, d in planets.items() if d.get('house') == house]
        
        # Karaka position
        karaka_data = planets.get(karaka, {})
        
        # Dignity of lord
        from ..parashara.dignity import PlanetaryDignity
        lord_dignity = PlanetaryDignity.get_dignity(house_lord, lord_data.get('rashi', 0))
        
        # Aspects on house
        aspects = self._get_aspects_on_house(house)
        
        # Strength assessment
        strength_points = 0
        factors = []
        
        if lord_dignity.get('is_exalted'):
            strength_points += 2
            factors.append(f"{house_lord} exalted (excellent)")
        elif lord_dignity.get('is_own_sign'):
            strength_points += 1
            factors.append(f"{house_lord} in own sign (good)")
        elif lord_dignity.get('is_debilitated'):
            strength_points -= 2
            factors.append(f"{house_lord} debilitated (weak)")
        
        if 'Jupiter' in [a['planet'] for a in aspects if a['nature'] == 'Benefic']:
            strength_points += 1
            factors.append("Jupiter's blessing on house")
        
        if 'Saturn' in [a['planet'] for a in aspects]:
            strength_points -= 1
            factors.append("Saturn causes delays")
        
        if planets_in_house:
            benefics = [p for p in planets_in_house if p in ['Jupiter', 'Venus', 'Moon', 'Mercury']]
            malefics = [p for p in planets_in_house if p in ['Saturn', 'Mars', 'Rahu', 'Ketu']]
            if benefics:
                strength_points += 1
                factors.append(f"Benefics in house: {', '.join(benefics)}")
            if malefics:
                strength_points -= 1
                factors.append(f"Malefics in house: {', '.join(malefics)}")
        
        overall = 'Strong' if strength_points >= 2 else 'Weak' if strength_points <= -2 else 'Moderate'
        
        return {
            'house': house,
            'rashi': RASHI_NAMES[house_rashi],
            'lord': house_lord,
            'lord_in_house': lord_data.get('house', 1),
            'lord_dignity': lord_dignity.get('dignity', 'Neutral'),
            'planets_in_house': planets_in_house,
            'karaka': karaka,
            'karaka_house': karaka_data.get('house', 1),
            'aspects': aspects,
            'factors': factors,
            'overall_strength': overall,
            'strength_score': strength_points,
        }
    
    def _get_aspects_on_house(self, house: int) -> List[Dict]:
        """Get planets aspecting a house"""
        aspects = []
        planets = self.engine.planets
        
        from ..parashara.aspects import PlanetaryAspects
        
        for planet, data in planets.items():
            planet_house = data.get('house', 1)
            aspected = PlanetaryAspects.get_houses_aspected(planet, planet_house)
            
            for asp in aspected:
                if asp['house'] == house:
                    nature = 'Benefic' if planet in ['Jupiter', 'Venus', 'Moon', 'Mercury'] else 'Malefic'
                    aspects.append({
                        'planet': planet,
                        'from_house': planet_house,
                        'strength': asp.get('strength', 100),
                        'nature': nature,
                    })
        
        return aspects
    
    def _analyze_timing(self, house: int, karaka: str, months: int) -> Dict:
        """Analyze timing using dasha and transits"""
        
        # Current dasha
        dasha = self.engine.get_vimshottari_dasha()
        
        # House lord as significator
        asc_rashi = self.engine.ascendant_rashi
        house_rashi = (asc_rashi + house - 1) % 12
        house_lord = RASHI_LORDS[house_rashi]
        
        significators = [house_lord, karaka]
        
        # Find favorable periods
        favorable = []
        
        # Check if current dasha is favorable
        maha = dasha['mahadasha']['lord']
        antar = dasha['antardasha']['lord']
        
        if maha in significators:
            favorable.append({
                'period': f"Current {maha} Mahadasha",
                'reason': f"{maha} rules/signifies this matter",
                'strength': 'Strong',
            })
        
        if antar in significators:
            favorable.append({
                'period': f"Current {antar} Antardasha",
                'reason': f"{antar} activates this matter",
                'strength': 'Moderate',
            })
        
        # Check transits
        transits = self.engine.get_current_transits()
        
        return {
            'current_dasha': dasha['dasha_string'],
            'mahadasha': maha,
            'mahadasha_end': dasha['mahadasha']['end'][:10],
            'antardasha': antar,
            'significators': significators,
            'favorable_periods': favorable,
            'transit_period': transits.get('overall_period', 'Mixed'),
            'sade_sati': transits.get('sade_sati', {}).get('is_sade_sati', False),
        }
    
    def _analyze_jaimini_marriage(self) -> Dict:
        """Jaimini analysis for marriage/relationships"""
        karakas = self.engine.get_jaimini_karakas()
        arudhas = self.engine.get_arudha_padas()
        
        dk = karakas.get('Darakaraka', {})
        upapada = arudhas.get('A12', {})
        
        # Determine marriage type from Upapada position
        up_house = upapada.get('arudha_house', 1)
        if up_house == 5:
            marriage_type = "Love marriage indicated"
        elif up_house == 9:
            marriage_type = "Arranged marriage or through elders"
        elif up_house == 11:
            marriage_type = "Through friends or social circle"
        elif up_house == 7:
            marriage_type = "Strong marriage karma"
        else:
            marriage_type = "Mixed indications"
        
        # Spouse characteristics from Darakaraka
        spouse_traits = {
            'Sun': 'Authoritative, proud, leader',
            'Moon': 'Emotional, nurturing, caring',
            'Mars': 'Energetic, athletic, independent',
            'Mercury': 'Intelligent, communicative, youthful',
            'Jupiter': 'Wise, religious, knowledgeable',
            'Venus': 'Beautiful, artistic, romantic',
            'Saturn': 'Mature, serious, hardworking',
            'Rahu': 'Unconventional, foreign connection',
        }
        
        return {
            'darakaraka': dk.get('planet', 'Unknown'),
            'darakaraka_rashi': dk.get('rashi_name', 'Unknown'),
            'spouse_traits': spouse_traits.get(dk.get('planet', ''), 'Unknown'),
            'upapada_house': up_house,
            'upapada_rashi': upapada.get('arudha_rashi_name', 'Unknown'),
            'marriage_type': marriage_type,
        }
    
    def _find_relevant_yogas(self, category: str) -> List[Dict]:
        """Find yogas relevant to the category"""
        all_yogas = self.engine.get_yogas()
        highlights = all_yogas.get('highlights', [])[:3]
        
        return [
            {'name': y.get('name', ''), 'effect': y.get('effect', '')}
            for y in highlights
        ]
    
    def _current_state(self) -> Dict:
        """Analyze current astrological state"""
        dasha = self.engine.get_vimshottari_dasha()
        transits = self.engine.get_current_transits()
        
        favorable = []
        challenging = []
        
        maha = dasha['mahadasha']['lord']
        if maha in ['Jupiter', 'Venus', 'Moon', 'Mercury']:
            favorable.append(f"{maha} Mahadasha (benefic)")
        elif maha in ['Saturn', 'Rahu', 'Ketu']:
            challenging.append(f"{maha} Mahadasha (karmic lessons)")
        
        if transits.get('sade_sati', {}).get('is_sade_sati'):
            challenging.append("Sade Sati active")
        
        overall = transits.get('overall_period', 'Mixed')
        
        return {
            'dasha': f"{maha}-{dasha['antardasha']['lord']}",
            'transit_period': overall,
            'favorable': favorable,
            'challenging': challenging,
            'net': 'Favorable' if len(favorable) > len(challenging) else 
                  'Challenging' if len(challenging) > len(favorable) else 'Neutral',
        }
    
    def _synthesize(self, category: str, house: Dict, timing: Dict,
                    jaimini: Optional[Dict], yogas: List, current: Dict) -> Dict:
        """Synthesize all findings"""
        
        conclusions = []
        
        # House conclusion
        if house['overall_strength'] == 'Strong':
            conclusions.append(f"{category.title()} prospects are strong")
        elif house['overall_strength'] == 'Weak':
            conclusions.append(f"{category.title()} may face challenges")
        else:
            conclusions.append(f"{category.title()} has moderate indications")
        
        # Add factors
        for f in house['factors'][:2]:
            conclusions.append(f)
        
        # Timing
        if timing['favorable_periods']:
            conclusions.append(timing['favorable_periods'][0]['period'])
        
        # Jaimini
        if jaimini:
            conclusions.append(jaimini['marriage_type'])
        
        # Current
        conclusions.append(f"Current period: {current['net']}")
        
        # Best timing estimate
        best_timing = None
        if timing['favorable_periods']:
            best_timing = timing['favorable_periods'][0]['period']
        
        return {
            'conclusions': conclusions,
            'overall_promise': house['overall_strength'],
            'best_timing': best_timing,
            'current_favorability': current['net'],
            'key_planets': timing['significators'],
        }
    
    def get_ai_context(self) -> str:
        """Generate context string for AI prompt"""
        analysis = self.analyze('GENERAL')
        
        lines = [
            "ASTROLOGICAL ANALYSIS:",
            f"• House Strength: {analysis['house_analysis']['overall_strength']}",
            f"• Current Dasha: {analysis['timing']['current_dasha']}",
            f"• Transit Period: {analysis['current_state']['transit_period']}",
        ]
        
        if analysis['yogas']:
            yoga_names = [y['name'] for y in analysis['yogas']]
            lines.append(f"• Key Yogas: {', '.join(yoga_names)}")
        
        for c in analysis['synthesis']['conclusions'][:3]:
            lines.append(f"• {c}")
        
        return "\n".join(lines)


def analyze_query(engine: JyotishEngine, category: str) -> Dict:
    """Quick function to analyze a query"""
    analyzer = QueryAnalyzer(engine)
    return analyzer.analyze(category)
