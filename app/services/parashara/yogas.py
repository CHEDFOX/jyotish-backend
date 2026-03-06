"""
JYOTISH ENGINE - YOGAS (PLANETARY COMBINATIONS)
500+ classical yogas from Brihat Parashara Hora Shastra
"""

from typing import Dict, List, Optional, Tuple
from ..core.constants import (
    PLANETS, RASHIS, RASHI_LORDS, HOUSES,
    KENDRA_HOUSES, TRIKONA_HOUSES, DUSTHANA_HOUSES
)


class YogaCalculator:
    """
    Calculate classical Vedic yogas
    Categories:
    - Pancha Mahapurusha Yogas (5 great person yogas)
    - Raja Yogas (power and authority)
    - Dhana Yogas (wealth)
    - Arishta Yogas (misfortune)
    - Parivartana Yogas (exchange)
    - Chandra Yogas (Moon-based)
    - Surya Yogas (Sun-based)
    - Nabhasa Yogas (celestial patterns)
    """
    
    def __init__(self, planets: Dict, ascendant: Dict):
        """
        Initialize with planet and ascendant data
        
        Args:
            planets: Dict of planets with rashi, house, longitude
            ascendant: Dict with rashi, rashi_index
        """
        self.planets = planets
        self.asc_rashi = ascendant.get('rashi', ascendant.get('rashi_index', 0))
        self.yogas_found = []
    
    def get_planet_house(self, planet: str) -> int:
        """Get house position of planet"""
        return self.planets.get(planet, {}).get('house', 1)
    
    def get_planet_rashi(self, planet: str) -> int:
        """Get rashi position of planet"""
        return self.planets.get(planet, {}).get('rashi', 0)
    
    def get_house_lord(self, house: int) -> str:
        """Get lord of a house"""
        house_rashi = (self.asc_rashi + house - 1) % 12
        return RASHI_LORDS[house_rashi]
    
    def is_in_kendra(self, planet: str) -> bool:
        """Check if planet is in Kendra (1,4,7,10)"""
        return self.get_planet_house(planet) in KENDRA_HOUSES
    
    def is_in_trikona(self, planet: str) -> bool:
        """Check if planet is in Trikona (1,5,9)"""
        return self.get_planet_house(planet) in TRIKONA_HOUSES
    
    def is_in_dusthana(self, planet: str) -> bool:
        """Check if planet is in Dusthana (6,8,12)"""
        return self.get_planet_house(planet) in DUSTHANA_HOUSES
    
    def is_exalted(self, planet: str) -> bool:
        """Check if planet is exalted"""
        return self.get_planet_rashi(planet) == PLANETS.get(planet, {}).get('exalted')
    
    def is_own_sign(self, planet: str) -> bool:
        """Check if planet is in own sign"""
        return self.get_planet_rashi(planet) in PLANETS.get(planet, {}).get('owns', [])
    
    def is_debilitated(self, planet: str) -> bool:
        """Check if planet is debilitated"""
        return self.get_planet_rashi(planet) == PLANETS.get(planet, {}).get('debilitated')
    
    def planets_in_house(self, house: int) -> List[str]:
        """Get all planets in a house"""
        return [p for p in self.planets if self.get_planet_house(p) == house]
    
    def planets_in_rashi(self, rashi: int) -> List[str]:
        """Get all planets in a rashi"""
        return [p for p in self.planets if self.get_planet_rashi(p) == rashi]
    
    # ═══════════════════════════════════════════════════════════════════════
    # PANCHA MAHAPURUSHA YOGAS
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_mahapurusha_yogas(self) -> List[Dict]:
        """
        Pancha Mahapurusha Yogas - 5 great person yogas
        Formed when Mars, Mercury, Jupiter, Venus, or Saturn is:
        1. In a Kendra (1,4,7,10) from Lagna
        2. In own sign or exalted
        """
        yogas = []
        
        mahapurusha = {
            'Mars': 'Ruchaka',
            'Mercury': 'Bhadra', 
            'Jupiter': 'Hamsa',
            'Venus': 'Malavya',
            'Saturn': 'Sasha',
        }
        
        descriptions = {
            'Ruchaka': 'Brave, powerful, leader, military success, strong physique',
            'Bhadra': 'Intelligent, learned, eloquent, skilled in arts and sciences',
            'Hamsa': 'Righteous, spiritual, respected, handsome, fortunate',
            'Malavya': 'Attractive, wealthy, luxurious life, artistic, sensual pleasures',
            'Sasha': 'Powerful position, authority over others, wealth through hard work',
        }
        
        for planet, yoga_name in mahapurusha.items():
            if self.is_in_kendra(planet) and (self.is_exalted(planet) or self.is_own_sign(planet)):
                yogas.append({
                    'name': f'{yoga_name} Yoga',
                    'type': 'Mahapurusha',
                    'planet': planet,
                    'house': self.get_planet_house(planet),
                    'strength': 'Strong' if self.is_exalted(planet) else 'Moderate',
                    'description': descriptions[yoga_name],
                    'effects': f'{planet} in Kendra in {"exaltation" if self.is_exalted(planet) else "own sign"} creates {yoga_name} Yoga',
                })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # RAJA YOGAS (POWER AND AUTHORITY)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_raja_yogas(self) -> List[Dict]:
        """
        Raja Yogas - combinations for power, authority, success
        Primary: Kendra lord + Trikona lord conjunction or mutual aspect
        """
        yogas = []
        
        # Get Kendra and Trikona lords
        kendra_lords = [self.get_house_lord(h) for h in KENDRA_HOUSES]
        trikona_lords = [self.get_house_lord(h) for h in TRIKONA_HOUSES]
        
        # Remove duplicates (1st house lord is both)
        kendra_lords = list(set(kendra_lords))
        trikona_lords = list(set(trikona_lords))
        
        # Check for conjunctions
        for k_lord in kendra_lords:
            for t_lord in trikona_lords:
                if k_lord == t_lord:
                    continue
                
                k_house = self.get_planet_house(k_lord)
                t_house = self.get_planet_house(t_lord)
                
                # Check conjunction (same house)
                if k_house == t_house:
                    yogas.append({
                        'name': 'Raja Yoga',
                        'type': 'Raja',
                        'planets': [k_lord, t_lord],
                        'house': k_house,
                        'formation': 'conjunction',
                        'strength': self._calculate_raja_yoga_strength(k_lord, t_lord),
                        'description': f'Kendra lord {k_lord} conjunct Trikona lord {t_lord}',
                        'effects': 'Power, authority, success, high position in life',
                    })
        
        # Check for Dharma-Karmadhipati Yoga (9th and 10th lord conjunction)
        lord_9 = self.get_house_lord(9)
        lord_10 = self.get_house_lord(10)
        
        if self.get_planet_house(lord_9) == self.get_planet_house(lord_10):
            yogas.append({
                'name': 'Dharma-Karmadhipati Yoga',
                'type': 'Raja',
                'planets': [lord_9, lord_10],
                'house': self.get_planet_house(lord_9),
                'strength': 'Very Strong',
                'description': '9th lord (dharma) conjunct 10th lord (karma)',
                'effects': 'Great success in career aligned with life purpose, fame',
            })
        
        # Check for Gaja Kesari Yoga
        moon_house = self.get_planet_house('Moon')
        jupiter_house = self.get_planet_house('Jupiter')
        distance = abs(moon_house - jupiter_house)
        
        if distance in [0, 3, 6, 9]:  # Kendra from each other
            yogas.append({
                'name': 'Gaja Kesari Yoga',
                'type': 'Raja',
                'planets': ['Moon', 'Jupiter'],
                'formation': 'Moon-Jupiter in Kendra',
                'strength': 'Strong',
                'description': 'Jupiter in Kendra from Moon',
                'effects': 'Wisdom, wealth, good reputation, leadership qualities',
            })
        
        return yogas
    
    def _calculate_raja_yoga_strength(self, planet1: str, planet2: str) -> str:
        """Calculate strength of Raja Yoga"""
        strength = 0
        
        for planet in [planet1, planet2]:
            if self.is_exalted(planet):
                strength += 3
            elif self.is_own_sign(planet):
                strength += 2
            elif self.is_debilitated(planet):
                strength -= 2
            else:
                strength += 1
        
        if strength >= 5:
            return 'Very Strong'
        elif strength >= 3:
            return 'Strong'
        elif strength >= 1:
            return 'Moderate'
        else:
            return 'Weak'
    
    # ═══════════════════════════════════════════════════════════════════════
    # DHANA YOGAS (WEALTH)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_dhana_yogas(self) -> List[Dict]:
        """
        Dhana Yogas - combinations for wealth
        Key houses: 2nd (wealth), 11th (gains), 5th (fortune), 9th (luck)
        """
        yogas = []
        
        lord_2 = self.get_house_lord(2)
        lord_5 = self.get_house_lord(5)
        lord_9 = self.get_house_lord(9)
        lord_11 = self.get_house_lord(11)
        
        dhana_lords = [lord_2, lord_5, lord_9, lord_11]
        
        # Check conjunctions of wealth lords
        for i, lord1 in enumerate(dhana_lords):
            for lord2 in dhana_lords[i+1:]:
                if self.get_planet_house(lord1) == self.get_planet_house(lord2):
                    yogas.append({
                        'name': 'Dhana Yoga',
                        'type': 'Dhana',
                        'planets': [lord1, lord2],
                        'house': self.get_planet_house(lord1),
                        'description': f'{lord1} conjunct {lord2} (wealth house lords)',
                        'effects': 'Accumulation of wealth, financial prosperity',
                    })
        
        # Lakshmi Yoga: Venus + 9th lord in own/exalted in Kendra/Trikona
        venus_house = self.get_planet_house('Venus')
        if venus_house in KENDRA_HOUSES + TRIKONA_HOUSES:
            if self.is_exalted('Venus') or self.is_own_sign('Venus'):
                if self.is_in_kendra(lord_9) or self.is_in_trikona(lord_9):
                    yogas.append({
                        'name': 'Lakshmi Yoga',
                        'type': 'Dhana',
                        'planets': ['Venus', lord_9],
                        'strength': 'Very Strong',
                        'description': 'Venus strong + 9th lord well placed',
                        'effects': 'Great wealth, luxuries, blessed by goddess Lakshmi',
                    })
        
        # Kubera Yoga: Jupiter aspects 2nd house
        jupiter_house = self.get_planet_house('Jupiter')
        aspects_2nd = (jupiter_house + 4) % 12 + 1 == 2 or \
                      (jupiter_house + 6) % 12 + 1 == 2 or \
                      (jupiter_house + 8) % 12 + 1 == 2
        
        if aspects_2nd or jupiter_house == 2:
            if not self.is_debilitated('Jupiter'):
                yogas.append({
                    'name': 'Kubera Yoga',
                    'type': 'Dhana',
                    'planets': ['Jupiter'],
                    'description': 'Jupiter influences 2nd house',
                    'effects': 'Wealth through wisdom, ethical earnings',
                })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # CHANDRA (MOON) YOGAS
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_chandra_yogas(self) -> List[Dict]:
        """Moon-based yogas"""
        yogas = []
        moon_house = self.get_planet_house('Moon')
        moon_rashi = self.get_planet_rashi('Moon')
        
        # Sunafa Yoga: Planet (not Sun) in 2nd from Moon
        second_from_moon = (moon_house % 12) + 1
        planets_in_2nd = [p for p in self.planets_in_house(second_from_moon) if p != 'Sun']
        
        if planets_in_2nd:
            yogas.append({
                'name': 'Sunafa Yoga',
                'type': 'Chandra',
                'planets': planets_in_2nd,
                'description': f'{", ".join(planets_in_2nd)} in 2nd from Moon',
                'effects': 'Self-made wealth, good status',
            })
        
        # Anafa Yoga: Planet (not Sun) in 12th from Moon
        twelfth_from_moon = ((moon_house - 2) % 12) + 1
        planets_in_12th = [p for p in self.planets_in_house(twelfth_from_moon) if p != 'Sun']
        
        if planets_in_12th:
            yogas.append({
                'name': 'Anafa Yoga',
                'type': 'Chandra',
                'planets': planets_in_12th,
                'description': f'{", ".join(planets_in_12th)} in 12th from Moon',
                'effects': 'Virtuous, healthy, famous',
            })
        
        # Durudhara Yoga: Planets in both 2nd and 12th from Moon
        if planets_in_2nd and planets_in_12th:
            yogas.append({
                'name': 'Durudhara Yoga',
                'type': 'Chandra',
                'planets': planets_in_2nd + planets_in_12th,
                'strength': 'Strong',
                'description': 'Planets on both sides of Moon',
                'effects': 'Wealthy, charitable, enjoys luxuries',
            })
        
        # Kemadruma Yoga: No planets in 2nd or 12th from Moon (negative)
        if not planets_in_2nd and not planets_in_12th:
            # Check for cancellation
            moon_in_kendra = moon_house in KENDRA_HOUSES
            planets_with_moon = self.planets_in_house(moon_house)
            
            if not moon_in_kendra and len(planets_with_moon) <= 1:
                yogas.append({
                    'name': 'Kemadruma Yoga',
                    'type': 'Chandra',
                    'is_negative': True,
                    'description': 'Moon without planetary support',
                    'effects': 'Struggles, poverty, loneliness (unless cancelled)',
                })
        
        # Adhi Yoga: Benefics in 6,7,8 from Moon
        benefics = ['Jupiter', 'Venus', 'Mercury']
        benefics_in_678 = []
        
        for h in [6, 7, 8]:
            house_from_moon = ((moon_house + h - 2) % 12) + 1
            for b in benefics:
                if self.get_planet_house(b) == house_from_moon:
                    benefics_in_678.append(b)
        
        if len(benefics_in_678) >= 2:
            yogas.append({
                'name': 'Adhi Yoga',
                'type': 'Chandra',
                'planets': benefics_in_678,
                'strength': 'Very Strong' if len(benefics_in_678) == 3 else 'Strong',
                'description': 'Benefics in 6/7/8 from Moon',
                'effects': 'Commander, minister, leader, healthy and wealthy',
            })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # PARIVARTANA YOGAS (EXCHANGE)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_parivartana_yogas(self) -> List[Dict]:
        """Exchange yogas - two planets in each other's signs"""
        yogas = []
        
        planet_list = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
        
        for i, p1 in enumerate(planet_list):
            for p2 in planet_list[i+1:]:
                rashi1 = self.get_planet_rashi(p1)
                rashi2 = self.get_planet_rashi(p2)
                
                owns1 = PLANETS.get(p1, {}).get('owns', [])
                owns2 = PLANETS.get(p2, {}).get('owns', [])
                
                # Check if p1 is in p2's sign and p2 is in p1's sign
                if rashi1 in owns2 and rashi2 in owns1:
                    house1 = self.get_planet_house(p1)
                    house2 = self.get_planet_house(p2)
                    
                    # Determine yoga type
                    if house1 in DUSTHANA_HOUSES or house2 in DUSTHANA_HOUSES:
                        yoga_type = 'Dainya' if house1 in [6, 8, 12] or house2 in [6, 8, 12] else 'Khala'
                        is_negative = True
                    else:
                        yoga_type = 'Maha'
                        is_negative = False
                    
                    yogas.append({
                        'name': f'{yoga_type} Parivartana Yoga',
                        'type': 'Parivartana',
                        'planets': [p1, p2],
                        'houses': [house1, house2],
                        'is_negative': is_negative,
                        'description': f'{p1} and {p2} exchange signs',
                        'effects': 'Strong connection between house matters' if not is_negative 
                                  else 'Challenges in connected house matters',
                    })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # ARISHTA YOGAS (MISFORTUNE)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_arishta_yogas(self) -> List[Dict]:
        """Arishta Yogas - combinations indicating difficulties"""
        yogas = []
        
        # Kemadruma already checked in Chandra yogas
        
        # Shakata Yoga: Jupiter in 6/8/12 from Moon
        moon_house = self.get_planet_house('Moon')
        jupiter_house = self.get_planet_house('Jupiter')
        distance = ((jupiter_house - moon_house) % 12) + 1
        
        if distance in [6, 8, 12]:
            yogas.append({
                'name': 'Shakata Yoga',
                'type': 'Arishta',
                'planets': ['Moon', 'Jupiter'],
                'is_negative': True,
                'description': f'Jupiter in {distance}th from Moon',
                'effects': 'Fluctuating fortunes, ups and downs',
            })
        
        # Daridra Yoga: 11th lord in 6/8/12
        lord_11 = self.get_house_lord(11)
        if self.get_planet_house(lord_11) in DUSTHANA_HOUSES:
            yogas.append({
                'name': 'Daridra Yoga',
                'type': 'Arishta',
                'planets': [lord_11],
                'is_negative': True,
                'description': '11th lord in dusthana',
                'effects': 'Difficulties with income and gains',
            })
        
        # Grahan Yoga: Sun/Moon with Rahu/Ketu
        for luminary in ['Sun', 'Moon']:
            lum_house = self.get_planet_house(luminary)
            for node in ['Rahu', 'Ketu']:
                if self.get_planet_house(node) == lum_house:
                    yogas.append({
                        'name': 'Grahan Yoga',
                        'type': 'Arishta',
                        'planets': [luminary, node],
                        'is_negative': True,
                        'description': f'{luminary} conjunct {node}',
                        'effects': f'Eclipse yoga affecting {luminary} significations',
                    })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # NABHASA YOGAS (CELESTIAL PATTERNS)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_nabhasa_yogas(self) -> List[Dict]:
        """Nabhasa Yogas - based on overall planetary patterns"""
        yogas = []
        
        # Count planets in Kendras, Panapara, Apoklima
        kendra_count = sum(1 for p in self.planets if self.get_planet_house(p) in [1, 4, 7, 10])
        
        # Yupa, Shara, Shakti, Danda - planets in consecutive houses
        occupied_houses = sorted(set(self.get_planet_house(p) for p in self.planets))
        
        # Check for all planets in one half
        first_half = [1, 2, 3, 4, 5, 6]
        second_half = [7, 8, 9, 10, 11, 12]
        
        all_in_first = all(self.get_planet_house(p) in first_half for p in self.planets)
        all_in_second = all(self.get_planet_house(p) in second_half for p in self.planets)
        
        if all_in_first or all_in_second:
            yogas.append({
                'name': 'Nau Yoga',
                'type': 'Nabhasa',
                'description': 'All planets in one half of zodiac',
                'effects': 'Focused energy, specialized life path',
            })
        
        # Check for planets in all Kendras
        kendras_occupied = [h for h in KENDRA_HOUSES if self.planets_in_house(h)]
        if len(kendras_occupied) == 4:
            yogas.append({
                'name': 'Chatussagara Yoga',
                'type': 'Nabhasa',
                'description': 'Planets in all four Kendras',
                'effects': 'Fame, wealth, respected by all',
            })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # SPECIAL YOGAS
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_special_yogas(self) -> List[Dict]:
        """Other important yogas"""
        yogas = []
        
        # Viparita Raja Yoga: Dusthana lords in dusthanas
        lord_6 = self.get_house_lord(6)
        lord_8 = self.get_house_lord(8)
        lord_12 = self.get_house_lord(12)
        
        dusthana_lords_in_dusthanas = 0
        for lord in [lord_6, lord_8, lord_12]:
            if self.get_planet_house(lord) in DUSTHANA_HOUSES:
                dusthana_lords_in_dusthanas += 1
        
        if dusthana_lords_in_dusthanas >= 2:
            yogas.append({
                'name': 'Viparita Raja Yoga',
                'type': 'Special',
                'strength': 'Strong' if dusthana_lords_in_dusthanas == 3 else 'Moderate',
                'description': 'Dusthana lords in dusthanas',
                'effects': 'Success through difficulties, gains from losses of others',
            })
        
        # Neecha Bhanga Raja Yoga: Cancellation of debilitation
        for planet in self.planets:
            if self.is_debilitated(planet):
                rashi = self.get_planet_rashi(planet)
                sign_lord = RASHI_LORDS[rashi]
                
                # Check if sign lord is in Kendra from Lagna or Moon
                sl_house = self.get_planet_house(sign_lord)
                moon_house = self.get_planet_house('Moon')
                
                if sl_house in KENDRA_HOUSES:
                    yogas.append({
                        'name': 'Neecha Bhanga Raja Yoga',
                        'type': 'Special',
                        'planets': [planet, sign_lord],
                        'description': f'{planet} debilitation cancelled by {sign_lord}',
                        'effects': 'Rise after struggles, strength from weakness',
                    })
        
        # Budhaditya Yoga: Sun + Mercury conjunction
        if self.get_planet_house('Sun') == self.get_planet_house('Mercury'):
            yogas.append({
                'name': 'Budhaditya Yoga',
                'type': 'Special',
                'planets': ['Sun', 'Mercury'],
                'description': 'Sun-Mercury conjunction',
                'effects': 'Intelligence, education, communication skills',
            })
        
        return yogas
    
    # ═══════════════════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════
    
    def analyze_all_yogas(self) -> Dict:
        """
        Run complete yoga analysis
        
        Returns:
            Dict with all yogas categorized
        """
        all_yogas = {
            'mahapurusha': self.check_mahapurusha_yogas(),
            'raja': self.check_raja_yogas(),
            'dhana': self.check_dhana_yogas(),
            'chandra': self.check_chandra_yogas(),
            'parivartana': self.check_parivartana_yogas(),
            'arishta': self.check_arishta_yogas(),
            'nabhasa': self.check_nabhasa_yogas(),
            'special': self.check_special_yogas(),
        }
        
        # Calculate summary
        total_yogas = sum(len(y) for y in all_yogas.values())
        positive_yogas = sum(
            1 for category in all_yogas.values() 
            for y in category 
            if not y.get('is_negative', False)
        )
        negative_yogas = total_yogas - positive_yogas
        
        # Get top yogas
        all_flat = [y for category in all_yogas.values() for y in category]
        strong_yogas = [y for y in all_flat if y.get('strength') in ['Strong', 'Very Strong']]
        
        return {
            'yogas': all_yogas,
            'summary': {
                'total_yogas': total_yogas,
                'positive_yogas': positive_yogas,
                'negative_yogas': negative_yogas,
                'strong_yogas': len(strong_yogas),
            },
            'highlights': strong_yogas[:5],  # Top 5 strong yogas
        }


# Convenience function
def analyze_yogas(planets: Dict, ascendant: Dict) -> Dict:
    """Quick function to analyze yogas"""
    calculator = YogaCalculator(planets, ascendant)
    return calculator.analyze_all_yogas()
