"""
JYOTISH ENGINE - CAREER APTITUDE ENGINE
Combines D10, Nadi, KP, personality for career recommendations with percentages.
"""

from typing import Dict, List
from ..core.constants import PLANETS, RASHI_LORDS, RASHI_NAMES

CAREER_FIELDS = {
    'technology': {'planets': ['Mercury', 'Rahu'], 'houses': [3, 10, 11], 'signs': [2, 5, 10]},
    'medicine': {'planets': ['Sun', 'Mars', 'Ketu'], 'houses': [6, 8, 12], 'signs': [3, 7, 5]},
    'law': {'planets': ['Jupiter', 'Saturn'], 'houses': [9, 10, 6], 'signs': [6, 8]},
    'business': {'planets': ['Mercury', 'Venus'], 'houses': [7, 10, 11], 'signs': [1, 2, 6]},
    'arts': {'planets': ['Venus', 'Moon'], 'houses': [5, 2, 3], 'signs': [1, 4, 6, 11]},
    'government': {'planets': ['Sun', 'Saturn'], 'houses': [10, 9, 1], 'signs': [4, 9]},
    'finance': {'planets': ['Jupiter', 'Mercury', 'Venus'], 'houses': [2, 11, 10], 'signs': [1, 2, 9]},
    'education': {'planets': ['Jupiter', 'Mercury'], 'houses': [4, 5, 9], 'signs': [2, 5, 8]},
    'sports': {'planets': ['Mars', 'Sun'], 'houses': [3, 6, 10], 'signs': [0, 4, 8]},
    'government': {'planets': ['Sun', 'Saturn', 'Moon'], 'houses': [10, 9, 1, 6], 'signs': [3, 4, 9]},
    'politics': {'planets': ['Sun', 'Moon', 'Mars', 'Saturn'], 'houses': [10, 1, 2, 11], 'signs': [0, 3, 4, 9]},
    'spiritual': {'planets': ['Ketu', 'Jupiter', 'Moon'], 'houses': [9, 12, 5], 'signs': [3, 7, 11]},
    'media': {'planets': ['Mercury', 'Moon', 'Venus'], 'houses': [3, 5, 10], 'signs': [2, 4, 6]},
    'engineering': {'planets': ['Mars', 'Saturn', 'Mercury'], 'houses': [10, 3, 6], 'signs': [0, 5, 9]},
    'real_estate': {'planets': ['Mars', 'Saturn', 'Venus'], 'houses': [4, 10, 11], 'signs': [1, 3, 9]},
    'hospitality': {'planets': ['Moon', 'Venus'], 'houses': [4, 7, 10], 'signs': [1, 3, 6]},
}


class CareerAptitude:
    def __init__(self, engine):
        self.engine = engine
        self.planets = engine.planets
        self.asc_rashi = engine.ascendant_rashi

    def _planet_house(self, planet: str) -> int:
        return self.planets.get(planet, {}).get('house', 1)

    def _planet_rashi(self, planet: str) -> int:
        return self.planets.get(planet, {}).get('rashi', 0)

    def _is_strong(self, planet: str) -> bool:
        r = self._planet_rashi(planet)
        pd = PLANETS.get(planet, {})
        return r == pd.get('exalted') or r in pd.get('owns', [])

    def calculate_aptitude(self) -> Dict:
        scores = {}
        l10 = RASHI_LORDS[(self.asc_rashi + 9) % 12]
        l10_house = self._planet_house(l10)
        h10_occupants = [p for p in self.planets if self._planet_house(p) == 10]

        for field, criteria in CAREER_FIELDS.items():
            score = None  # removed invented percentage
            reasons = []

            # Planet strength check
            for planet in criteria['planets']:
                if planet in self.planets:
                    if self._is_strong(planet):
                        score = None  # removed
                        reasons.append(f'{planet} strong')
                    elif self._planet_house(planet) in criteria['houses']:
                        score = None  # removed
                        reasons.append(f'{planet} in relevant house')
                    else:
                        score = None  # removed

            # 10th lord in relevant house
            if l10_house in criteria['houses']:
                score = None  # removed
                reasons.append(f'10th lord {l10} in house {l10_house}')

            # 10th house occupants match
            for occ in h10_occupants:
                if occ in criteria['planets']:
                    score = None  # removed
                    reasons.append(f'{occ} in 10th house')

            # Ascendant sign match
            if self.asc_rashi in criteria.get('signs', []):
                score = None  # removed
                reasons.append(f'Ascendant in matching sign')

            # EXTRA: 10th lord in 2nd house = political speech/public career
            if field in ('government', 'politics'):
                moon_h = self._planet_house('Moon')
                sun_h = self._planet_house('Sun')
                mars_h = self._planet_house('Mars')
                # Moon (mind of masses) in kendra/trikona = public leader
                if moon_h in [1, 4, 7, 10, 5, 9]:
                    score = None  # removed
                    reasons.append('Moon in strong house — public appeal')
                # Sun strong = authority and government
                if sun_h in [1, 10, 9, 11]:
                    score = None  # removed
                    reasons.append('Sun strong — authority and power')
                # Mars + Moon together = warrior leader
                if mars_h == moon_h:
                    score = None  # removed
                    reasons.append('Mars-Moon conjunction — aggressive leadership')
                # Saturn in 11th = mass following, political network
                sat_h = self._planet_house('Saturn')
                if sat_h == 11:
                    score = None  # removed
                    reasons.append('Saturn in 11th — mass following')

            # Normalize to percentage
            max_possible = 15 * len(criteria['planets']) + 12 + 15 * 2 + 8 + 42  # +42 for politics extras
            pct = min(100, int((score / max(max_possible, 1)) * 100))

            scores[field] = {
                'score': pct,
                'reasons': reasons[:3],
            }

        ranked = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)

        return {
            'system': 'career_aptitude',
            'category': 'prediction',
            'triggers': ['career', 'job', 'profession', 'work', 'aptitude'],
            'rankings': [
                {'field': f, 'score': d['score'], 'reasons': d['reasons']}
                for f, d in ranked
            ],
            'top_3': [
                {'field': f, 'score': d['score'], 'match': 'Strong' if d['score'] >= 50 else 'Moderate'}
                for f, d in ranked[:3]
            ],
            'tenth_lord': l10,
            'tenth_occupants': h10_occupants,
            'confidence': 0.75,
        }


def get_career_aptitude(engine):
    return CareerAptitude(engine).calculate_aptitude()
