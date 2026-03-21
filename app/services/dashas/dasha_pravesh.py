"""
JYOTISH ENGINE - DASHA PRAVESH
Chart cast for the exact moment a new Mahadasha begins.
Sub-prediction tool — shows what the dasha will bring.
"""

from datetime import datetime
from typing import Dict
from ..core.constants import RASHI_NAMES, RASHI_LORDS, KENDRA_HOUSES, TRIKONA_HOUSES, DUSTHANA_HOUSES
from ..core.ephemeris import get_ephemeris


class DashaPravesh:
    def __init__(self, engine, dasha_start_date: str, dasha_lord: str):
        """
        Args:
            engine: Birth chart JyotishEngine
            dasha_start_date: Date string 'YYYY-MM-DD' when dasha begins
            dasha_lord: Planet whose dasha is starting
        """
        self.engine = engine
        self.dasha_lord = dasha_lord
        self.latitude = engine.latitude
        self.longitude = engine.longitude
        self.ephemeris = get_ephemeris()

        # Parse dasha start date
        parts = dasha_start_date.split('-')
        self.dasha_start = datetime(int(parts[0]), int(parts[1]), int(parts[2]), 12, 0)

    def generate_pravesh_chart(self) -> Dict:
        """Generate chart for dasha start moment."""
        try:
            chart = self.ephemeris.generate_chart(
                self.dasha_start, self.latitude, self.longitude
            )
            return chart
        except Exception:
            return {}

    def analyze_dasha_pravesh(self) -> Dict:
        """Analyze what the dasha will bring based on pravesh chart."""
        chart = self.generate_pravesh_chart()
        if not chart:
            return {'error': 'Could not generate pravesh chart'}

        planets = chart.get('planets', {})
        asc = chart.get('ascendant', {})
        asc_rashi = asc.get('rashi', 0)

        # Find dasha lord's position in pravesh chart
        dl_data = planets.get(self.dasha_lord, {})
        dl_house = dl_data.get('house', 1)
        dl_rashi = dl_data.get('rashi', 0)

        # Assess dasha lord strength in pravesh
        dl_exalted = dl_rashi == (self.engine.planets.get(self.dasha_lord, {}).get('rashi', -1))
        dl_in_kendra = dl_house in KENDRA_HOUSES
        dl_in_dusthana = dl_house in DUSTHANA_HOUSES

        if dl_in_kendra:
            dl_strength = 'Strong'
            outlook = 'Favorable dasha — dasha lord strong in Kendra at time of entry'
        elif dl_in_dusthana:
            dl_strength = 'Weak'
            outlook = 'Challenging dasha — dasha lord in dusthana at entry, requires remedies'
        else:
            dl_strength = 'Moderate'
            outlook = 'Mixed dasha — moderate results, some effort needed'

        # Check benefic/malefic influences
        benefics_kendra = [p for p in ['Jupiter', 'Venus'] if planets.get(p, {}).get('house', 0) in KENDRA_HOUSES]
        malefics_kendra = [p for p in ['Saturn', 'Mars', 'Rahu'] if planets.get(p, {}).get('house', 0) in KENDRA_HOUSES]

        if len(benefics_kendra) > len(malefics_kendra):
            overall = 'Positive'
        elif len(malefics_kendra) > len(benefics_kendra):
            overall = 'Challenging'
        else:
            overall = 'Mixed'

        # Moon in pravesh = emotional theme of dasha
        moon_h = planets.get('Moon', {}).get('house', 1)
        moon_themes = {
            1: 'Self-focus, new identity', 2: 'Wealth, family matters',
            3: 'Communication, courage', 4: 'Home, property, comfort',
            5: 'Children, creativity, romance', 6: 'Health, service, competition',
            7: 'Marriage, partnerships', 8: 'Transformation, hidden matters',
            9: 'Fortune, travel, higher learning', 10: 'Career, status, authority',
            11: 'Gains, friends, desires', 12: 'Expenses, foreign, spiritual',
        }

        return {
            'dasha_lord': self.dasha_lord,
            'dasha_start': self.dasha_start.strftime('%Y-%m-%d'),
            'pravesh_ascendant': RASHI_NAMES[asc_rashi],
            'dasha_lord_position': {
                'house': dl_house, 'rashi': RASHI_NAMES[dl_rashi],
                'strength': dl_strength,
            },
            'overall_outlook': overall,
            'outlook_detail': outlook,
            'emotional_theme': moon_themes.get(moon_h, 'General'),
            'benefics_in_kendra': benefics_kendra,
            'malefics_in_kendra': malefics_kendra,
        }


def analyze_dasha_pravesh(engine, dasha_start: str, dasha_lord: str) -> Dict:
    dp = DashaPravesh(engine, dasha_start, dasha_lord)
    return dp.analyze_dasha_pravesh()
