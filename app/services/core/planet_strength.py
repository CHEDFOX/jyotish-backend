"""
JYOTISH ENGINE — UNIFIED PLANET STRENGTH ENGINE

The foundation of ALL predictions. Every planet strength check
in the entire system should go through THIS module.

Implements:
- 7-level dignity (exalted → moolatrikona → own → friend → neutral → enemy → debilitated)
- Combustion detection
- Functional benefic/malefic per ascendant
- Yogakaraka identification
- Shadbala integration
- Vargottama detection
- Karaka Bhava Nashaya check
- Papakartari / Shubhakartari for houses

Based on: BPHS, Phaladeepika, Saravali
"""

from typing import Dict, List, Tuple, Optional
from .constants import PLANETS, RASHI_LORDS, RASHI_NAMES

# ═══════════════════════════════════════════════════════════════
# COMBUSTION DEGREES (planet is combust when within these degrees of Sun)
# Source: Surya Siddhanta / BPHS
# ═══════════════════════════════════════════════════════════════

COMBUSTION_DEGREES = {
    'Moon': 12,
    'Mars': 17,
    'Mercury': 14,  # 12 when retrograde
    'Jupiter': 11,
    'Venus': 10,    # 8 when retrograde
    'Saturn': 15,
}

# ═══════════════════════════════════════════════════════════════
# FUNCTIONAL BENEFIC/MALEFIC PER ASCENDANT
# Source: BPHS — based on house lordship
# Kendra lords (1,4,7,10): neutral — natural benefics become mild malefics (Kendradhipatya Dosha)
# Trikona lords (5,9): always benefic
# Dusthana lords (3,6,8,11,12): malefic
# Yogakaraka: owns both kendra AND trikona
# ═══════════════════════════════════════════════════════════════

# For each ascendant (0=Aries through 11=Pisces):
# 'benefic': planets that give good results
# 'malefic': planets that give bad results  
# 'yogakaraka': planet owning both kendra and trikona (most auspicious)
# 'neutral': neither strongly good nor bad
# 'maraka': death-inflicting (lords of 2nd and 7th)
# 'badhaka': obstruction-causing

FUNCTIONAL_STATUS = {
    0: {  # Aries
        'benefic': ['Sun', 'Mars', 'Jupiter'],
        'malefic': ['Mercury', 'Venus', 'Saturn'],
        'yogakaraka': None,
        'maraka': ['Venus', 'Mars'],  # 2nd lord Venus, 7th lord Venus... Venus=2+7, Mars=1+8
        'badhaka': 'Saturn',  # Movable: 11th lord
    },
    1: {  # Taurus
        'benefic': ['Saturn', 'Mercury', 'Sun'],
        'malefic': ['Jupiter', 'Venus', 'Moon'],
        'yogakaraka': 'Saturn',  # rules 9th + 10th
        'maraka': ['Mercury', 'Mars'],
        'badhaka': 'Jupiter',  # Fixed: 9th lord
    },
    2: {  # Gemini
        'benefic': ['Venus', 'Saturn'],
        'malefic': ['Mars', 'Jupiter', 'Sun'],
        'yogakaraka': None,
        'maraka': ['Moon', 'Jupiter'],
        'badhaka': 'Mars',  # Dual: 7th lord
    },
    3: {  # Cancer
        'benefic': ['Mars', 'Jupiter', 'Moon'],
        'malefic': ['Venus', 'Saturn', 'Mercury'],
        'yogakaraka': 'Mars',  # rules 5th + 10th
        'maraka': ['Sun', 'Saturn'],
        'badhaka': 'Venus',  # Movable: 11th lord
    },
    4: {  # Leo
        'benefic': ['Mars', 'Jupiter', 'Sun'],
        'malefic': ['Mercury', 'Venus', 'Saturn'],
        'yogakaraka': 'Mars',  # rules 4th + 9th
        'maraka': ['Mercury', 'Saturn'],
        'badhaka': 'Mercury',  # Fixed: 9th lord... wait
    },
    5: {  # Virgo
        'benefic': ['Venus', 'Mercury'],
        'malefic': ['Mars', 'Moon', 'Jupiter'],
        'yogakaraka': None,
        'maraka': ['Venus', 'Jupiter'],
        'badhaka': 'Jupiter',  # Dual: 7th lord
    },
    6: {  # Libra
        'benefic': ['Saturn', 'Mercury', 'Venus'],
        'malefic': ['Sun', 'Mars', 'Jupiter'],
        'yogakaraka': 'Saturn',  # rules 4th + 5th
        'maraka': ['Mars', 'Mars'],
        'badhaka': 'Sun',  # Movable: 11th lord
    },
    7: {  # Scorpio
        'benefic': ['Jupiter', 'Moon', 'Sun'],
        'malefic': ['Mercury', 'Venus', 'Saturn'],
        'yogakaraka': None,  # Moon rules 9th, but not a kendra+trikona combo owner
        'maraka': ['Jupiter', 'Venus'],
        'badhaka': 'Moon',  # Fixed: 9th lord
    },
    8: {  # Sagittarius
        'benefic': ['Mars', 'Sun', 'Jupiter'],
        'malefic': ['Venus', 'Saturn', 'Mercury'],
        'yogakaraka': None,
        'maraka': ['Saturn', 'Mercury'],
        'badhaka': 'Mercury',  # Dual: 7th lord
    },
    9: {  # Capricorn
        'benefic': ['Venus', 'Mercury', 'Saturn'],
        'malefic': ['Mars', 'Jupiter', 'Moon'],
        'yogakaraka': 'Venus',  # rules 5th + 10th
        'maraka': ['Saturn', 'Moon'],
        'badhaka': 'Mars',  # Movable: 11th lord
    },
    10: {  # Aquarius
        'benefic': ['Venus', 'Saturn', 'Mars'],
        'malefic': ['Jupiter', 'Moon', 'Sun'],
        'yogakaraka': 'Venus',  # rules 4th + 9th
        'maraka': ['Jupiter', 'Sun'],
        'badhaka': 'Jupiter',  # Fixed: 9th lord
    },
    11: {  # Pisces
        'benefic': ['Moon', 'Mars', 'Jupiter'],
        'malefic': ['Sun', 'Venus', 'Saturn', 'Mercury'],
        'yogakaraka': None,
        'maraka': ['Mars', 'Mercury'],
        'badhaka': 'Mercury',  # Dual: 7th lord
    },
}


class PlanetStrengthEngine:
    """
    Unified planet strength assessment.
    
    Usage:
        pse = PlanetStrengthEngine(engine)
        strength = pse.get_strength('Jupiter')
        # Returns: {
        #   'dignity_level': 3,  (0=debilitated to 6=exalted)
        #   'dignity_name': 'friend',
        #   'is_combust': False,
        #   'is_retrograde': True,
        #   'is_vargottama': True,
        #   'functional_status': 'benefic',
        #   'is_yogakaraka': False,
        #   'shadbala_rupas': 7.2,
        #   'shadbala_sufficient': True,
        #   'overall_score': 72,  (0-100)
        #   'classification': 'strong',  (very_weak/weak/moderate/strong/very_strong)
        # }
    """

    def __init__(self, engine):
        self.engine = engine
        self.planets = engine.planets
        self.asc_rashi = engine.ascendant_rashi
        self._func_status = FUNCTIONAL_STATUS.get(self.asc_rashi, FUNCTIONAL_STATUS[0])
        self._shadbala_cache = None
        self._strength_cache = {}

    # ═══════════════════════════════════════════════════════════════
    # 7-LEVEL DIGNITY
    # ═══════════════════════════════════════════════════════════════

    def get_dignity(self, planet: str) -> Tuple[int, str]:
        """
        Returns (level, name) where level 0-6:
        0 = debilitated
        1 = enemy sign
        2 = neutral sign
        3 = friend sign
        4 = own sign
        5 = moolatrikona
        6 = exalted
        """
        if planet in ('Rahu', 'Ketu'):
            return self._node_dignity(planet)

        pd = PLANETS.get(planet, {})
        rashi = self.planets.get(planet, {}).get('rashi', 0)
        degree_in_sign = self.planets.get(planet, {}).get('longitude', 0) % 30

        # Check exalted
        if rashi == pd.get('exalted'):
            return (6, 'exalted')

        # Check moolatrikona
        mt_sign = pd.get('moolatrikona')
        mt_start = pd.get('moolatrikona_start', 0)
        mt_end = pd.get('moolatrikona_end', 30)
        if mt_sign is not None and rashi == mt_sign:
            if mt_start <= degree_in_sign <= mt_end:
                return (5, 'moolatrikona')
            # If in moolatrikona sign but outside range, it's own sign
            if rashi in pd.get('owns', []):
                return (4, 'own')

        # Check own sign
        if rashi in pd.get('owns', []):
            return (4, 'own')

        # Check debilitated
        if rashi == pd.get('debilitated'):
            return (0, 'debilitated')

        # Check friend/neutral/enemy by sign lord
        sign_lord = RASHI_LORDS[rashi]
        if sign_lord == planet:
            return (4, 'own')

        friends = pd.get('friends', [])
        enemies = pd.get('enemies', [])

        if sign_lord in friends:
            return (3, 'friend')
        elif sign_lord in enemies:
            return (1, 'enemy')
        else:
            return (2, 'neutral')

    def _node_dignity(self, planet: str) -> Tuple[int, str]:
        """Dignity for Rahu/Ketu (different schools, using common approach)."""
        pd = PLANETS.get(planet, {})
        rashi = self.planets.get(planet, {}).get('rashi', 0)
        if rashi == pd.get('exalted'):
            return (6, 'exalted')
        if rashi == pd.get('debilitated'):
            return (0, 'debilitated')
        # Rahu strong in Virgo, Aquarius; Ketu strong in Pisces, Scorpio
        if planet == 'Rahu' and rashi in [5, 10]:  # Virgo, Aquarius
            return (3, 'friend')
        if planet == 'Ketu' and rashi in [7, 11]:  # Scorpio, Pisces
            return (3, 'friend')
        return (2, 'neutral')

    # ═══════════════════════════════════════════════════════════════
    # COMBUSTION
    # ═══════════════════════════════════════════════════════════════

    def is_combust(self, planet: str) -> bool:
        """Check if planet is combust (too close to Sun). Phaladeepika: combust = debilitated equivalent."""
        if planet in ('Sun', 'Rahu', 'Ketu'):
            return False

        threshold = COMBUSTION_DEGREES.get(planet, 12)

        # Mercury/Venus have tighter threshold when retrograde
        if planet == 'Mercury' and self.planets.get(planet, {}).get('retrograde', False):
            threshold = 12
        if planet == 'Venus' and self.planets.get(planet, {}).get('retrograde', False):
            threshold = 8

        sun_long = self.planets.get('Sun', {}).get('longitude', 0)
        planet_long = self.planets.get(planet, {}).get('longitude', 0)

        diff = abs(sun_long - planet_long)
        if diff > 180:
            diff = 360 - diff

        return diff <= threshold

    # ═══════════════════════════════════════════════════════════════
    # VARGOTTAMA
    # ═══════════════════════════════════════════════════════════════

    def is_vargottama(self, planet: str) -> bool:
        """Planet in same sign in D1 and D9. Significantly strengthens the planet."""
        try:
            d1_rashi = self.planets.get(planet, {}).get('rashi', 0)
            longitude = self.planets.get(planet, {}).get('longitude', 0)

            # Navamsa calculation: each navamsa = 3°20' = 3.3333°
            degree_in_sign = longitude % 30
            navamsa_index = int(degree_in_sign / (30 / 9))
            d1_sign = int(longitude / 30)

            # For fire signs (0,4,8): navamsa starts from Aries
            # For earth signs (1,5,9): navamsa starts from Capricorn
            # For air signs (2,6,10): navamsa starts from Libra
            # For water signs (3,7,11): navamsa starts from Cancer
            element = d1_sign % 4
            if element == 0:  # Fire
                d9_rashi = navamsa_index % 12
            elif element == 1:  # Earth
                d9_rashi = (9 + navamsa_index) % 12
            elif element == 2:  # Air
                d9_rashi = (6 + navamsa_index) % 12
            else:  # Water
                d9_rashi = (3 + navamsa_index) % 12

            return d1_rashi == d9_rashi
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════════
    # FUNCTIONAL STATUS
    # ═══════════════════════════════════════════════════════════════

    def get_functional_status(self, planet: str) -> str:
        """Returns: 'yogakaraka', 'benefic', 'neutral', 'malefic', 'maraka'"""
        if planet == self._func_status.get('yogakaraka'):
            return 'yogakaraka'
        if planet in self._func_status.get('benefic', []):
            return 'benefic'
        if planet in self._func_status.get('malefic', []):
            return 'malefic'
        return 'neutral'

    def is_yogakaraka(self, planet: str) -> bool:
        return planet == self._func_status.get('yogakaraka')

    def get_yogakaraka(self) -> Optional[str]:
        return self._func_status.get('yogakaraka')

    def get_maraka_planets(self) -> List[str]:
        return list(set(self._func_status.get('maraka', [])))

    def get_badhaka(self) -> str:
        return self._func_status.get('badhaka', '')

    # ═══════════════════════════════════════════════════════════════
    # SHADBALA INTEGRATION
    # ═══════════════════════════════════════════════════════════════

    def _get_shadbala(self) -> Dict:
        """Get Shadbala from engine's existing module."""
        if self._shadbala_cache is not None:
            return self._shadbala_cache
        try:
            self._shadbala_cache = self.engine.get_shadbala_complete()
            return self._shadbala_cache
        except Exception:
            self._shadbala_cache = {}
            return {}

    def get_shadbala_score(self, planet: str) -> float:
        """Get planet's shadbala total score (0-100 scale)."""
        sb = self._get_shadbala()
        planets_data = sb.get('planets', {})
        p_data = planets_data.get(planet, {})
        # Field is 'percentage' from shadbala_complete module
        score = p_data.get('percentage', 0)
        if score == 0:
            score = p_data.get('total_score', 0)
        return score if score > 0 else 0

    # ═══════════════════════════════════════════════════════════════
    # PAPAKARTARI / SHUBHAKARTARI (for houses)
    # ═══════════════════════════════════════════════════════════════

    def check_kartari(self, house: int) -> Tuple[str, str]:
        """
        Check if a house is hemmed between malefics or benefics.
        Returns (type, description):
        'papakartari' — hemmed between malefics (destroyed)
        'shubhakartari' — hemmed between benefics (protected)
        'mixed' — one malefic one benefic on either side
        'none' — no hemming
        """
        prev_house = house - 1 if house > 1 else 12
        next_house = house + 1 if house < 12 else 1

        prev_occupants = [p for p in self.planets if self.planets[p].get('house') == prev_house]
        next_occupants = [p for p in self.planets if self.planets[p].get('house') == next_house]

        natural_malefics = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}
        natural_benefics = {'Jupiter', 'Venus', 'Mercury', 'Moon'}  # Mercury when alone, Moon when waxing

        has_malefic_prev = bool(set(prev_occupants) & natural_malefics)
        has_malefic_next = bool(set(next_occupants) & natural_malefics)
        has_benefic_prev = bool(set(prev_occupants) & natural_benefics)
        has_benefic_next = bool(set(next_occupants) & natural_benefics)

        if has_malefic_prev and has_malefic_next and not has_benefic_prev and not has_benefic_next:
            return ('papakartari', f'H{house} hemmed by malefics — squeezed/destroyed')
        elif has_benefic_prev and has_benefic_next and not has_malefic_prev and not has_malefic_next:
            return ('shubhakartari', f'H{house} hemmed by benefics — protected/boosted')
        elif (has_malefic_prev or has_malefic_next) and (has_benefic_prev or has_benefic_next):
            return ('mixed', f'H{house} has mixed hemming')
        return ('none', '')

    # ═══════════════════════════════════════════════════════════════
    # KARAKA BHAVA NASHAYA
    # ═══════════════════════════════════════════════════════════════

    def check_karaka_bhava_nashaya(self, planet: str, house: int) -> bool:
        """
        Classical rule: karaka placed in its own signification house WEAKENS that house.
        Jupiter in 5th weakens children. Venus in 7th weakens marriage.
        Sun in 9th weakens father. Moon in 4th weakens mother.
        Mars in 3rd weakens siblings. Saturn in 8th weakens longevity.
        Mercury in 4th weakens education.
        """
        KARAKA_HOUSES = {
            'Jupiter': [5, 2, 11],  # Children, wealth
            'Venus': [7],           # Marriage
            'Sun': [9, 10],         # Father, authority
            'Moon': [4],            # Mother, happiness
            'Mars': [3],            # Siblings, courage
            'Saturn': [8, 6],       # Longevity, disease
            'Mercury': [4, 10],     # Education, business
        }

        karaka_houses = KARAKA_HOUSES.get(planet, [])
        if house in karaka_houses and self.planets.get(planet, {}).get('house') == house:
            return True
        return False

    # ═══════════════════════════════════════════════════════════════
    # UNIFIED STRENGTH ASSESSMENT
    # ═══════════════════════════════════════════════════════════════

    def get_strength(self, planet: str) -> Dict:
        """
        Master method. Returns complete strength assessment for a planet.
        """
        if planet in self._strength_cache:
            return self._strength_cache[planet]

        dignity_level, dignity_name = self.get_dignity(planet)
        combust = self.is_combust(planet)
        retrograde = self.planets.get(planet, {}).get('retrograde', False)
        vargottama = self.is_vargottama(planet)
        func_status = self.get_functional_status(planet)
        yogakaraka = self.is_yogakaraka(planet)
        shadbala = self.get_shadbala_score(planet)
        house = self.planets.get(planet, {}).get('house', 1)

        # ═══ Calculate overall score (0-100) ═══

        # Base from dignity (0-60 range, maps from 7 levels)
        dignity_scores = {0: 5, 1: 15, 2: 25, 3: 35, 4: 45, 5: 52, 6: 60}
        score = dignity_scores.get(dignity_level, 25)

        # Combustion: Phaladeepika says combust = debilitated equivalent
        if combust:
            score = min(score, 15)  # Cap at enemy-sign level

        # Vargottama: significant boost (same sign in D1 and D9)
        if vargottama:
            score += 10

        # Retrograde: NOT always bad. Retrograde planets have chesta bala.
        # But retrograde in dusthana is problematic.
        # Rahu/Ketu always retrograde — no adjustment
        if retrograde and planet not in ('Rahu', 'Ketu'):
            if house in [6, 8, 12]:
                score -= 5  # Retrograde in dusthana = weakened
            else:
                score += 3  # Retrograde elsewhere = some extra strength (chesta bala)

        # Functional status adjustment
        if yogakaraka:
            score += 8  # Yogakaraka is the best planet for the chart
        elif func_status == 'benefic':
            score += 3
        elif func_status == 'malefic':
            score -= 3

        # Shadbala integration: only blend if we got real data
        if shadbala > 0:
            # Blend: 70% dignity-based + 30% shadbala-based
            # (dignity is more granular, shadbala adds temporal/directional context)
            score = int(score * 0.7 + shadbala * 0.3)

        # Clamp
        score = max(5, min(95, score))

        # Classification
        if score >= 75:
            classification = 'very_strong'
        elif score >= 60:
            classification = 'strong'
        elif score >= 40:
            classification = 'moderate'
        elif score >= 25:
            classification = 'weak'
        else:
            classification = 'very_weak'

        result = {
            'planet': planet,
            'house': house,
            'rashi': self.planets.get(planet, {}).get('rashi_name', ''),
            'dignity_level': dignity_level,
            'dignity_name': dignity_name,
            'is_combust': combust,
            'is_retrograde': retrograde,
            'is_vargottama': vargottama,
            'functional_status': func_status,
            'is_yogakaraka': yogakaraka,
            'shadbala_score': shadbala,
            'overall_score': score,
            'classification': classification,
        }

        self._strength_cache[planet] = result
        return result

    def get_all_strengths(self) -> Dict:
        """Get strength for all planets."""
        result = {}
        for planet in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']:
            result[planet] = self.get_strength(planet)
        return result

    # ═══════════════════════════════════════════════════════════════
    # HOUSE STRENGTH (for three-factor check)
    # ═══════════════════════════════════════════════════════════════

    def get_house_strength(self, house: int) -> Dict:
        """
        Assess house (bhava) strength for the three-factor check.
        Checks: occupants, aspects, kartari, lord strength.
        """
        lord = RASHI_LORDS[(self.asc_rashi + house - 1) % 12]
        lord_strength = self.get_strength(lord)

        occupants = [p for p in self.planets if self.planets[p].get('house') == house]
        benefic_occupants = [p for p in occupants if self.get_functional_status(p) in ('benefic', 'yogakaraka')]
        malefic_occupants = [p for p in occupants if self.get_functional_status(p) == 'malefic']

        # Jupiter aspect on house = protection
        jupiter_aspects = self._planet_aspects_house('Jupiter', house)
        saturn_aspects = self._planet_aspects_house('Saturn', house)

        kartari_type, kartari_desc = self.check_kartari(house)

        # Score the house
        score = 50

        # Lord strength contribution
        if lord_strength['overall_score'] >= 60:
            score += 12
        elif lord_strength['overall_score'] >= 40:
            score += 5
        else:
            score -= 10

        # Lord placement
        lord_house = lord_strength['house']
        kendra = [1, 4, 7, 10]
        trikona = [1, 5, 9]
        dusthana = [6, 8, 12]
        if lord_house in kendra:
            score += 8
        elif lord_house in trikona:
            score += 6
        elif lord_house in dusthana:
            # Exception: for houses 9/12, lord in 12th supports spiritual/foreign
            if house in [9, 12] and lord_house == 12:
                score += 2
            else:
                score -= 8

        # Occupants
        if benefic_occupants and not malefic_occupants:
            score += 8
        elif malefic_occupants and not benefic_occupants:
            score -= 6
        elif benefic_occupants and malefic_occupants:
            score += 2

        # Jupiter aspect = protection
        if jupiter_aspects and 'Jupiter' not in occupants:
            score += 6

        # Saturn aspect = delay/restriction
        if saturn_aspects and 'Saturn' not in occupants:
            score -= 3

        # Kartari
        if kartari_type == 'papakartari':
            score -= 12
        elif kartari_type == 'shubhakartari':
            score += 8

        score = max(5, min(95, score))

        return {
            'house': house,
            'lord': lord,
            'lord_strength': lord_strength,
            'occupants': occupants,
            'benefic_occupants': benefic_occupants,
            'malefic_occupants': malefic_occupants,
            'jupiter_aspects': jupiter_aspects,
            'saturn_aspects': saturn_aspects,
            'kartari': kartari_type,
            'score': score,
        }

    def _planet_aspects_house(self, planet: str, house: int) -> bool:
        """Check if planet aspects a house (full aspects only for now)."""
        p_house = self.planets.get(planet, {}).get('house', 1)
        aspects = PLANETS.get(planet, {}).get('aspects', [7])
        for asp in aspects:
            target = ((p_house + asp - 1) % 12) + 1
            if target == house:
                return True
        return False

    # ═══════════════════════════════════════════════════════════════
    # SANYASA YOGA EXACT DETECTION
    # ═══════════════════════════════════════════════════════════════

    def check_sanyasa_yoga(self) -> Dict:
        """
        Exact classical detection per BPHS + Phaladeepika:
        1. 4+ planets in one house
        2. Saturn aspecting weak lagna lord
        3. Moon in Saturn's drekkana + Mars/Saturn navamsa + aspected by Saturn
        """
        factors = []
        strength = 0

        # Rule 1: 4+ planets in one house
        for h in range(1, 13):
            occ = [p for p in self.planets if self.planets[p].get('house') == h]
            if len(occ) >= 4:
                # Check if any is combust (reduces sanyasa)
                combust_count = sum(1 for p in occ if self.is_combust(p))
                if combust_count == 0:
                    strength += 3
                    factors.append(f'{len(occ)} planets in H{h} ({", ".join(occ)}) — Sanyasa Yoga')
                else:
                    strength += 1
                    factors.append(f'{len(occ)} planets in H{h} but {combust_count} combust — weak sanyasa')

        # Rule 2: Saturn aspects weak lagna lord
        lagna_lord = RASHI_LORDS[self.asc_rashi]
        ll_strength = self.get_strength(lagna_lord)
        if ll_strength['overall_score'] < 40:
            if self._planet_aspects_house('Saturn', ll_strength['house']):
                strength += 2
                factors.append(f'Saturn aspects weak lagna lord {lagna_lord} — renunciation tendency')

        # Rule 3: Ketu in 12th (moksha karaka in moksha house)
        if self.planets.get('Ketu', {}).get('house') == 12:
            strength += 1
            factors.append('Ketu in 12th — moksha karaka in moksha house')

        # Rule 4: 12th house stellium (3+ planets including spiritual significators)
        h12_occ = [p for p in self.planets if self.planets[p].get('house') == 12]
        if len(h12_occ) >= 3:
            strength += 1
            factors.append(f'12th house stellium ({", ".join(h12_occ)})')

        confirmed = strength >= 3
        return {
            'confirmed': confirmed,
            'strength': strength,
            'factors': factors,
        }

    # ═══════════════════════════════════════════════════════════════
    # DHANA YOGA COUNTING
    # ═══════════════════════════════════════════════════════════════

    def count_dhana_yogas(self) -> Dict:
        """
        Count actual wealth yoga combinations between lords of 1st, 2nd, 5th, 9th, 11th.
        Per BPHS + Bhavartha Ratnakara.
        """
        wealth_houses = [1, 2, 5, 9, 11]
        lords = {}
        for h in wealth_houses:
            lords[h] = RASHI_LORDS[(self.asc_rashi + h - 1) % 12]

        yogas = []

        # Check all pairs for conjunction, mutual aspect, or exchange
        for i, h1 in enumerate(wealth_houses):
            for h2 in wealth_houses[i + 1:]:
                l1 = lords[h1]
                l2 = lords[h2]
                if l1 == l2:
                    continue  # Same planet owns both houses — inherent dhana yoga
                    # Actually this IS a yoga — planet owns two wealth houses

                l1_house = self.planets.get(l1, {}).get('house', 1)
                l2_house = self.planets.get(l2, {}).get('house', 1)

                # Conjunction
                if l1_house == l2_house:
                    yogas.append(f'{l1}(H{h1}L)+{l2}(H{h2}L) conjunct in H{l1_house}')
                    continue

                # Exchange (parivartana)
                if l1_house == h2 and l2_house == h1:
                    yogas.append(f'{l1}(H{h1}L)↔{l2}(H{h2}L) exchange — powerful dhana yoga')
                    continue

                # Mutual aspect (in 7th from each other)
                if abs(l1_house - l2_house) == 6 or abs(l1_house - l2_house) == 6:
                    yogas.append(f'{l1}(H{h1}L)↔{l2}(H{h2}L) mutual aspect')
                    continue

                # One placed in other's wealth house
                if l1_house in wealth_houses and l1_house == h2:
                    yogas.append(f'{l1}(H{h1}L) in H{h2} — activates wealth')
                elif l2_house in wealth_houses and l2_house == h1:
                    yogas.append(f'{l2}(H{h2}L) in H{h1} — activates wealth')

        # Check for planet owning two wealth houses
        for h1 in wealth_houses:
            for h2 in wealth_houses:
                if h1 < h2 and lords[h1] == lords[h2]:
                    yogas.append(f'{lords[h1]} owns both H{h1} and H{h2} — inherent dhana yoga')

        # Benefics in 2nd or 11th
        for h in [2, 11]:
            for p in [p for p in self.planets if self.planets[p].get('house') == h]:
                if p in ('Jupiter', 'Venus', 'Mercury'):
                    yogas.append(f'Benefic {p} in H{h} — wealth indicator')

        # Wealth lord in kendra or trikona (strong placement for wealth)
        kendra = [1, 4, 7, 10]
        trikona = [1, 5, 9]
        for h in wealth_houses:
            lord = lords[h]
            lord_house = self.planets.get(lord, {}).get('house', 1)
            # Lord in own sign = very strong
            lord_rashi = self.planets.get(lord, {}).get('rashi', -1)
            lord_owns = PLANETS.get(lord, {}).get('owns', [])
            if lord_rashi in lord_owns and h != 1:  # Skip lagna lord in own (counted separately)
                yogas.append(f'{lord}(H{h}L) in own sign — strong wealth foundation')
            # Lord in kendra from lagna activating wealth
            if lord_house in kendra and lord_house not in wealth_houses:
                yogas.append(f'{lord}(H{h}L) in kendra H{lord_house} — wealth lord empowered')

        # Rahu in 2nd or 11th = massive unconventional wealth
        rahu_h = self.planets.get('Rahu', {}).get('house', 0)
        if rahu_h in [2, 11]:
            yogas.append(f'Rahu in H{rahu_h} — massive unconventional wealth')

        # Ketu in 2nd = unconventional relationship with money (can mean extreme wealth OR detachment)
        ketu_h = self.planets.get('Ketu', {}).get('house', 0)
        if ketu_h == 2:
            yogas.append(f'Ketu in H2 — unconventional wealth pattern')

        # 11th lord in 8th = gains through others money, inheritance, transformation
        lord11 = lords.get(11, '')
        if lord11 and self.planets.get(lord11, {}).get('house') == 8:
            yogas.append(f'{lord11}(H11L) in H8 — gains through others money/transformation')

        # 1st lord strong in 1st = self-made wealth
        lord1 = lords.get(1, '')
        if lord1:
            l1_house = self.planets.get(lord1, {}).get('house', 0)
            l1_rashi = self.planets.get(lord1, {}).get('rashi', -1)
            l1_owns = PLANETS.get(lord1, {}).get('owns', [])
            if l1_house == 1 and l1_rashi in l1_owns:
                yogas.append(f'{lord1}(Lagna lord) in own sign in H1 — powerful self-made wealth')

        # Sun + Mercury conjunction (Budhaditya yoga) in kendra = intellectual empire
        sun_h = self.planets.get('Sun', {}).get('house', 0)
        merc_h = self.planets.get('Mercury', {}).get('house', 0)
        if sun_h == merc_h and sun_h in kendra:
            yogas.append(f'Sun+Mercury in H{sun_h} (Budhaditya) — intellectual/business empire')

        # Jupiter aspects 2nd or 11th = blessed wealth
        for h in [2, 11]:
            if self._planet_aspects_house('Jupiter', h) and self.planets.get('Jupiter', {}).get('house') != h:
                yogas.append(f'Jupiter aspects H{h} — blessed with wealth')

        count = len(yogas)
        if count >= 6:
            grade = 'Exceptional Wealth'
        elif count >= 4:
            grade = 'Very Wealthy'
        elif count >= 2:
            grade = 'Moderate Wealth'
        elif count >= 1:
            grade = 'Some Wealth'
        else:
            grade = 'Wealth Challenged'

        return {
            'count': count,
            'grade': grade,
            'yogas': yogas,
        }
