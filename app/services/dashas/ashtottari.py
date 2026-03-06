"""
JYOTISH ENGINE - ASHTOTTARI DASHA
108-year planetary period system
Used when Rahu is in Kendra/Trikona from Lagna Lord
"""

from datetime import datetime, timedelta
from typing import Dict, List
from ..core.constants import ASHTOTTARI_YEARS, ASHTOTTARI_ORDER, ASHTOTTARI_TOTAL
from ..core.utils import get_nakshatra_from_longitude


class AshtottariDasha:
    """
    Calculate Ashtottari Dasha periods
    8 planets (no Ketu), 108-year cycle
    
    Applicable when:
    - Birth is at night in Krishna Paksha (waning Moon)
    - OR Rahu is in Kendra/Trikona from Lagna Lord
    """
    
    # Nakshatra starting points for each planet
    # Ashtottari uses specific nakshatra groups
    NAKSHATRA_LORD = {
        # Ardra, Punarvasu, Pushya, Ashlesha (5-8) = Sun
        5: 'Sun', 6: 'Sun', 7: 'Sun', 8: 'Sun',
        # Magha, P.Phalguni, U.Phalguni, Hasta (9-12) = Moon
        9: 'Moon', 10: 'Moon', 11: 'Moon', 12: 'Moon',
        # Chitra, Swati, Vishakha, Anuradha (13-16) = Mars
        13: 'Mars', 14: 'Mars', 15: 'Mars', 16: 'Mars',
        # Jyeshtha, Mula, P.Ashadha, U.Ashadha (17-20) = Mercury
        17: 'Mercury', 18: 'Mercury', 19: 'Mercury', 20: 'Mercury',
        # Shravana, Dhanishta, Shatabhisha, P.Bhadra (21-24) = Saturn
        21: 'Saturn', 22: 'Saturn', 23: 'Saturn', 24: 'Saturn',
        # U.Bhadrapada, Revati, Ashwini, Bharani (25-27, 0-1) = Jupiter
        25: 'Jupiter', 26: 'Jupiter', 0: 'Jupiter', 1: 'Jupiter',
        # Krittika, Rohini, Mrigashira (2-4) = Rahu
        2: 'Rahu', 3: 'Rahu', 4: 'Rahu',
        # Remaining go to Venus
    }
    
    def __init__(self, moon_longitude: float, birth_datetime: datetime):
        """
        Initialize with Moon position and birth time
        """
        self.moon_longitude = moon_longitude
        self.birth_dt = birth_datetime
        
        self.nakshatra = get_nakshatra_from_longitude(moon_longitude)
        self.birth_lord = self._get_ashtottari_lord(self.nakshatra)
        self.dasha_balance = self._calculate_dasha_balance()
    
    def _get_ashtottari_lord(self, nakshatra: int) -> str:
        """Get Ashtottari dasha lord for nakshatra"""
        return self.NAKSHATRA_LORD.get(nakshatra, 'Venus')
    
    def _calculate_dasha_balance(self) -> float:
        """Calculate remaining years of first dasha"""
        nakshatra_span = 360 / 27
        degree_in_nakshatra = self.moon_longitude % nakshatra_span
        portion_remaining = 1 - (degree_in_nakshatra / nakshatra_span)
        
        dasha_years = ASHTOTTARI_YEARS[self.birth_lord]
        return dasha_years * portion_remaining
    
    def get_dasha_sequence(self) -> List[str]:
        """Get dasha sequence starting from birth lord"""
        start_index = ASHTOTTARI_ORDER.index(self.birth_lord)
        sequence = []
        
        for i in range(8):
            index = (start_index + i) % 8
            sequence.append(ASHTOTTARI_ORDER[index])
        
        return sequence
    
    def calculate_mahadasha_periods(self, years_to_calculate: int = 108) -> List[Dict]:
        """Calculate Ashtottari Mahadasha periods"""
        periods = []
        current_date = self.birth_dt
        sequence = self.get_dasha_sequence()
        
        # First dasha with balance
        first_lord = sequence[0]
        first_end = current_date + timedelta(days=self.dasha_balance * 365.25)
        
        periods.append({
            'lord': first_lord,
            'start': current_date,
            'end': first_end,
            'years': round(self.dasha_balance, 2),
            'is_birth_dasha': True,
        })
        
        current_date = first_end
        total_years = self.dasha_balance
        
        # Subsequent dashas
        for i in range(1, len(sequence)):
            if total_years >= years_to_calculate:
                break
            
            lord = sequence[i]
            years = ASHTOTTARI_YEARS[lord]
            end_date = current_date + timedelta(days=years * 365.25)
            
            periods.append({
                'lord': lord,
                'start': current_date,
                'end': end_date,
                'years': years,
            })
            
            current_date = end_date
            total_years += years
        
        return periods
    
    def calculate_antardasha(self, mahadasha_lord: str,
                             maha_start: datetime, maha_years: float) -> List[Dict]:
        """Calculate Antardasha within a Mahadasha"""
        antardashas = []
        start_index = ASHTOTTARI_ORDER.index(mahadasha_lord)
        current_date = maha_start
        
        for i in range(8):
            antar_lord = ASHTOTTARI_ORDER[(start_index + i) % 8]
            antar_years = (maha_years * ASHTOTTARI_YEARS[antar_lord]) / ASHTOTTARI_TOTAL
            antar_days = antar_years * 365.25
            
            end_date = current_date + timedelta(days=antar_days)
            
            antardashas.append({
                'lord': antar_lord,
                'start': current_date,
                'end': end_date,
                'months': round(antar_years * 12, 2),
                'days': round(antar_days, 1),
            })
            
            current_date = end_date
        
        return antardashas
    
    def get_current_dasha(self, query_date: datetime = None) -> Dict:
        """Get current running Ashtottari dasha"""
        if query_date is None:
            query_date = datetime.now()
        
        mahadashas = self.calculate_mahadasha_periods()
        
        current_maha = None
        for maha in mahadashas:
            if maha['start'] <= query_date < maha['end']:
                current_maha = maha
                break
        
        if not current_maha:
            return {'error': 'Date outside range'}
        
        antardashas = self.calculate_antardasha(
            current_maha['lord'],
            current_maha['start'],
            current_maha['years']
        )
        
        current_antar = None
        for antar in antardashas:
            if antar['start'] <= query_date < antar['end']:
                current_antar = antar
                break
        
        if not current_antar:
            current_antar = antardashas[0]
        
        return {
            'system': 'Ashtottari',
            'total_cycle': 108,
            'query_date': query_date.isoformat(),
            'mahadasha': {
                'lord': current_maha['lord'],
                'start': current_maha['start'].isoformat(),
                'end': current_maha['end'].isoformat(),
                'years_total': current_maha['years'],
            },
            'antardasha': {
                'lord': current_antar['lord'],
                'start': current_antar['start'].isoformat(),
                'end': current_antar['end'].isoformat(),
                'months': current_antar['months'],
            },
            'dasha_string': f"{current_maha['lord']}-{current_antar['lord']}",
        }
    
    @staticmethod
    def is_applicable(planets: Dict, ascendant_rashi: int, birth_datetime: datetime) -> Dict:
        """
        Check if Ashtottari Dasha is applicable
        
        Conditions:
        1. Night birth during Krishna Paksha (waning Moon)
        2. OR Rahu in Kendra/Trikona from Lagna Lord
        """
        # Check night birth
        hour = birth_datetime.hour
        is_night = hour < 6 or hour >= 18
        
        # Check Moon phase (Krishna Paksha = waning)
        sun_long = planets.get('Sun', {}).get('longitude', 0)
        moon_long = planets.get('Moon', {}).get('longitude', 0)
        sun_moon_diff = (moon_long - sun_long) % 360
        is_krishna_paksha = sun_moon_diff >= 180
        
        condition1 = is_night and is_krishna_paksha
        
        # Check Rahu position from Lagna Lord
        from ..core.constants import RASHI_LORDS
        lagna_lord = RASHI_LORDS[ascendant_rashi]
        lagna_lord_rashi = planets.get(lagna_lord, {}).get('rashi', 0)
        rahu_rashi = planets.get('Rahu', {}).get('rashi', 0)
        
        rahu_from_lord = ((rahu_rashi - lagna_lord_rashi) % 12) + 1
        condition2 = rahu_from_lord in [1, 4, 5, 7, 9, 10]  # Kendra or Trikona
        
        is_applicable = condition1 or condition2
        
        return {
            'is_applicable': is_applicable,
            'reason': 'Night birth in Krishna Paksha' if condition1 
                      else 'Rahu in Kendra/Trikona from Lagna Lord' if condition2
                      else 'Not applicable - use Vimshottari',
            'night_birth': is_night,
            'krishna_paksha': is_krishna_paksha,
            'rahu_position': rahu_from_lord,
        }


# Convenience function
def calculate_ashtottari(moon_longitude: float, birth_datetime: datetime) -> Dict:
    """Quick function to calculate current Ashtottari dasha"""
    calculator = AshtottariDasha(moon_longitude, birth_datetime)
    return calculator.get_current_dasha()
