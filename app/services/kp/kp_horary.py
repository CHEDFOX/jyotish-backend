"""
JYOTISH ENGINE - KP HORARY (1-249 NUMBER)
User picks a number 1-249 → instant chart → prediction.
No birth data needed at all. Walk-in astrologer technique.
"""

from datetime import datetime
from typing import Dict
from ..core.constants import RASHI_NAMES, RASHI_LORDS, NAKSHATRA_NAMES, NAKSHATRA_LORDS

# 249 sub-lord divisions of the zodiac
# Each number maps to a specific degree range → nakshatra → sub-lord
TOTAL_SUBS = 249

VIMSHOTTARI_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17,
}
DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
TOTAL_YEARS = 120


class KPHorary:
    def __init__(self, number: int, latitude: float = 28.6139, longitude: float = 77.2090):
        if number < 1 or number > 249:
            raise ValueError('Number must be between 1 and 249')
        self.number = number
        self.latitude = latitude
        self.longitude = longitude

    def _number_to_cusp(self) -> Dict:
        """Convert number (1-249) to zodiac position."""
        degree_per_sub = 360 / 249
        longitude = (self.number - 1) * degree_per_sub

        rashi = int(longitude / 30) % 12
        degree_in_sign = longitude % 30
        nak_index = int(longitude / (360 / 27)) % 27
        nak_lord = NAKSHATRA_LORDS[nak_index]

        # Sub-lord calculation
        nak_span = 360 / 27
        pos_in_nak = longitude % nak_span
        start_idx = DASHA_ORDER.index(nak_lord)

        accumulated = 0.0
        sub_lord = nak_lord
        for i in range(9):
            planet = DASHA_ORDER[(start_idx + i) % 9]
            sub_span = nak_span * (VIMSHOTTARI_YEARS[planet] / TOTAL_YEARS)
            if accumulated + sub_span > pos_in_nak:
                sub_lord = planet
                break
            accumulated += sub_span

        return {
            'longitude': round(longitude, 2),
            'rashi': rashi,
            'rashi_name': RASHI_NAMES[rashi],
            'degree': round(degree_in_sign, 2),
            'nakshatra': NAKSHATRA_NAMES[nak_index],
            'nakshatra_lord': nak_lord,
            'sub_lord': sub_lord,
            'sign_lord': RASHI_LORDS[rashi],
        }

    def analyze(self, question_category: str = 'general') -> Dict:
        """Analyze the horary number for a question."""
        cusp = self._number_to_cusp()

        sign_lord = cusp['sign_lord']
        star_lord = cusp['nakshatra_lord']
        sub_lord = cusp['sub_lord']

        # Quick yes/no based on sub-lord's natural benefic/malefic
        benefics = {'Jupiter', 'Venus', 'Mercury', 'Moon'}
        malefics = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}

        yes_points = 0
        if sub_lord in benefics: yes_points += 2
        if star_lord in benefics: yes_points += 1
        if sign_lord in benefics: yes_points += 1
        total = 4

        if sub_lord in malefics: yes_points -= 1
        if star_lord in malefics: yes_points -= 0.5

        probability = max(0.1, min(0.9, (yes_points / total) * 0.5 + 0.3))

        if probability >= 0.65:
            answer = 'Yes'
        elif probability <= 0.35:
            answer = 'No'
        else:
            answer = 'Uncertain'

        return {
            'system': 'KP Horary (1-249)',
            'number': self.number,
            'cusp': cusp,
            'significators': {
                'sign_lord': sign_lord,
                'star_lord': star_lord,
                'sub_lord': sub_lord,
            },
            'answer': answer,
            'probability': round(probability, 2),
            'category': question_category,
            'interpretation': f'Number {self.number} falls in {cusp["rashi_name"]} {cusp["degree"]}deg, '
                              f'Nakshatra {cusp["nakshatra"]} (lord: {star_lord}), '
                              f'Sub-lord: {sub_lord}. '
                              f'Answer leans {"positive" if answer == "Yes" else "negative" if answer == "No" else "uncertain"}.',
        }


def kp_horary_reading(number: int, category: str = 'general'):
    return KPHorary(number).analyze(category)
