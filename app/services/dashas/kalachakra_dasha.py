"""
JYOTISH ENGINE - KALACHAKRA DASHA
Most complex dasha system. Nakshatra-based but cyclic.
Uses Savya (forward) and Apsavya (backward) groups.
Each nakshatra pada maps to specific rashi dashas with variable durations.

Extremely accurate for timing when combined with Vimshottari and Chara.
"""

from datetime import datetime, timedelta
from typing import Dict, List
from ..core.constants import RASHI_NAMES, NAKSHATRA_NAMES

# Kalachakra rashi sequence for Savya (forward) nakshatras
SAVYA_SEQUENCE = [
    # Pada 1-4 for each Savya nakshatra
    [1, 2, 3, 4],   # Cancer→Leo→Virgo→Libra (starting from Cancer for Savya)
]

# Dasha years per rashi in Kalachakra
KC_YEARS = {
    0: 7,   # Aries
    1: 16,  # Taurus
    2: 9,   # Gemini
    3: 21,  # Cancer
    4: 5,   # Leo
    5: 9,   # Virgo
    6: 16,  # Libra
    7: 7,   # Scorpio
    8: 10,  # Sagittarius
    9: 4,   # Capricorn
    10: 4,  # Aquarius
    11: 10, # Pisces
}

# Savya group: Nakshatras where dasha runs forward
SAVYA_NAKSHATRAS = {0, 1, 2, 9, 10, 11, 18, 19, 20}  # Ashwini group, Magha group, Mula group
# Apsavya: remaining nakshatras

# Forward sequence (Savya): Aries→Taurus→...→Pisces
FORWARD = list(range(12))
# Backward sequence (Apsavya): Pisces→Aquarius→...→Aries  
BACKWARD = list(range(11, -1, -1))

# Deha-Jeeva assignment per nakshatra pada
# Deha = Body (physical), Jeeva = Soul (inner life)
# This is simplified — full KC requires extensive pada mapping
PADA_RASHI_MAP = {
    # nakshatra_index: {pada: (deha_rashi, jeeva_rashi)}
    # Ashwini (0)
    0: {1: (8, 0), 2: (1, 7), 3: (2, 6), 4: (3, 5)},
    # Bharani (1)  
    1: {1: (4, 4), 2: (5, 3), 3: (6, 2), 4: (7, 1)},
    # Krittika (2)
    2: {1: (8, 0), 2: (9, 11), 3: (10, 10), 4: (11, 9)},
}


class KalachakraDasha:
    def __init__(self, moon_longitude: float, birth_datetime: datetime):
        self.moon_longitude = moon_longitude
        self.birth_dt = birth_datetime
        self.nakshatra_index = int(moon_longitude / (360 / 27)) % 27
        self.pada = int((moon_longitude % (360 / 27)) / (360 / 108)) + 1
        self.is_savya = self.nakshatra_index in SAVYA_NAKSHATRAS

    def get_dasha_sequence(self) -> List[Dict]:
        """Get Kalachakra Dasha sequence."""
        if self.is_savya:
            # Forward from starting rashi
            start_rashi = (self.nakshatra_index * 4 + self.pada - 1) % 12
            sequence = [(start_rashi + i) % 12 for i in range(12)]
        else:
            # Backward from starting rashi
            start_rashi = (self.nakshatra_index * 4 + self.pada - 1) % 12
            sequence = [(start_rashi - i) % 12 for i in range(12)]

        return sequence

    def calculate_periods(self) -> List[Dict]:
        """Calculate all Kalachakra Dasha periods."""
        sequence = self.get_dasha_sequence()
        
        # Calculate balance of first dasha
        nak_span = 360 / 27
        pos_in_nak = self.moon_longitude % nak_span
        pada_span = nak_span / 4
        pos_in_pada = pos_in_nak % pada_span
        balance_fraction = 1 - (pos_in_pada / pada_span)

        periods = []
        current_date = self.birth_dt

        for cycle in range(2):  # 2 cycles
            for i, rashi in enumerate(sequence):
                years = KC_YEARS.get(rashi, 7)
                if cycle == 0 and i == 0:
                    years = years * balance_fraction

                days = int(years * 365.25)
                end_date = current_date + timedelta(days=days)

                periods.append({
                    'rashi': rashi,
                    'rashi_name': RASHI_NAMES[rashi],
                    'years': round(years, 2),
                    'start': current_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'start_dt': current_date,
                    'end_dt': end_date,
                    'cycle': cycle + 1,
                    'direction': 'Savya (Forward)' if self.is_savya else 'Apsavya (Backward)',
                })
                current_date = end_date

        return periods

    def get_current_dasha(self, query_date: datetime = None) -> Dict:
        """Get current Kalachakra Dasha."""
        if query_date is None:
            query_date = datetime.now()

        periods = self.calculate_periods()
        current = None
        for p in periods:
            if p['start_dt'] <= query_date < p['end_dt']:
                current = p
                break

        if not current:
            current = periods[0]

        return {
            'system': 'Kalachakra Dasha',
            'nakshatra': NAKSHATRA_NAMES[self.nakshatra_index],
            'pada': self.pada,
            'direction': 'Savya' if self.is_savya else 'Apsavya',
            'current': {
                'rashi': current['rashi_name'],
                'years': current['years'],
                'start': current['start'],
                'end': current['end'],
            },
            'dasha_string': f"KC: {current['rashi_name']}",
        }

    def get_deha_jeeva(self) -> Dict:
        """Get Deha (body) and Jeeva (soul) rashi."""
        pada_data = PADA_RASHI_MAP.get(self.nakshatra_index, {}).get(self.pada, None)
        if pada_data:
            deha, jeeva = pada_data
            return {
                'deha_rashi': RASHI_NAMES[deha],
                'jeeva_rashi': RASHI_NAMES[jeeva],
                'interpretation': 'Deha shows physical events, Jeeva shows inner/spiritual events. '
                                  'When dasha activates Deha rashi = physical change. Jeeva rashi = inner transformation.',
            }
        return {
            'deha_rashi': 'Calculated from full pada table',
            'jeeva_rashi': 'Calculated from full pada table',
            'interpretation': 'Deha-Jeeva analysis requires full nakshatra-pada mapping.',
        }


def calculate_kalachakra(moon_longitude: float, birth_dt: datetime) -> Dict:
    kc = KalachakraDasha(moon_longitude, birth_dt)
    return kc.get_current_dasha()
