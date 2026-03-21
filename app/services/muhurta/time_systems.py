"""
JYOTISH ENGINE - TIME-BASED SYSTEMS
- Choghadiya (sub-muhurta periods)
- Hora (planetary hours)
- Abhijit Muhurta (universal auspicious window)
- Tithi-based personality and predictions
"""

from datetime import datetime, timedelta
from typing import Dict, List

# Choghadiya names and nature
CHOGHADIYA_DAY = {
    0: [('Udveg', 'Sun', 'Bad'), ('Char', 'Venus', 'Good'), ('Labh', 'Mercury', 'Good'),
        ('Amrit', 'Moon', 'Best'), ('Kaal', 'Saturn', 'Bad'), ('Shubh', 'Jupiter', 'Good'),
        ('Rog', 'Mars', 'Bad'), ('Udveg', 'Sun', 'Bad')],
    1: [('Char', 'Venus', 'Good'), ('Labh', 'Mercury', 'Good'), ('Amrit', 'Moon', 'Best'),
        ('Kaal', 'Saturn', 'Bad'), ('Shubh', 'Jupiter', 'Good'), ('Rog', 'Mars', 'Bad'),
        ('Udveg', 'Sun', 'Bad'), ('Char', 'Venus', 'Good')],
    2: [('Labh', 'Mercury', 'Good'), ('Amrit', 'Moon', 'Best'), ('Kaal', 'Saturn', 'Bad'),
        ('Shubh', 'Jupiter', 'Good'), ('Rog', 'Mars', 'Bad'), ('Udveg', 'Sun', 'Bad'),
        ('Char', 'Venus', 'Good'), ('Labh', 'Mercury', 'Good')],
    3: [('Amrit', 'Moon', 'Best'), ('Kaal', 'Saturn', 'Bad'), ('Shubh', 'Jupiter', 'Good'),
        ('Rog', 'Mars', 'Bad'), ('Udveg', 'Sun', 'Bad'), ('Char', 'Venus', 'Good'),
        ('Labh', 'Mercury', 'Good'), ('Amrit', 'Moon', 'Best')],
    4: [('Shubh', 'Jupiter', 'Good'), ('Rog', 'Mars', 'Bad'), ('Udveg', 'Sun', 'Bad'),
        ('Char', 'Venus', 'Good'), ('Labh', 'Mercury', 'Good'), ('Amrit', 'Moon', 'Best'),
        ('Kaal', 'Saturn', 'Bad'), ('Shubh', 'Jupiter', 'Good')],
    5: [('Rog', 'Mars', 'Bad'), ('Udveg', 'Sun', 'Bad'), ('Char', 'Venus', 'Good'),
        ('Labh', 'Mercury', 'Good'), ('Amrit', 'Moon', 'Best'), ('Kaal', 'Saturn', 'Bad'),
        ('Shubh', 'Jupiter', 'Good'), ('Rog', 'Mars', 'Bad')],
    6: [('Kaal', 'Saturn', 'Bad'), ('Shubh', 'Jupiter', 'Good'), ('Rog', 'Mars', 'Bad'),
        ('Udveg', 'Sun', 'Bad'), ('Char', 'Venus', 'Good'), ('Labh', 'Mercury', 'Good'),
        ('Amrit', 'Moon', 'Best'), ('Kaal', 'Saturn', 'Bad')],
}

# Planetary hours sequence
HORA_SEQUENCE = ['Sun', 'Venus', 'Mercury', 'Moon', 'Saturn', 'Jupiter', 'Mars']
DAY_START_HORA = {6: 'Sun', 0: 'Moon', 1: 'Mars', 2: 'Mercury', 3: 'Jupiter', 4: 'Venus', 5: 'Saturn'}

# Birth Tithi personality
TITHI_PERSONALITY = {
    1: {'name': 'Pratipada', 'nature': 'Unstable', 'personality': 'Pioneering, restless, initiator, but inconsistent'},
    2: {'name': 'Dwitiya', 'nature': 'Stable', 'personality': 'Nurturing, family-oriented, wealth-conscious, artistic'},
    3: {'name': 'Tritiya', 'nature': 'Stable', 'personality': 'Courageous, adventurous, siblings important, communicator'},
    4: {'name': 'Chaturthi', 'nature': 'Unstable', 'personality': 'Aggressive, argumentative, but conquers obstacles'},
    5: {'name': 'Panchami', 'nature': 'Stable', 'personality': 'Intelligent, creative, romantic, fond of learning'},
    6: {'name': 'Shashthi', 'nature': 'Stable', 'personality': 'Victorious over enemies, health-conscious, competitive'},
    7: {'name': 'Saptami', 'nature': 'Stable', 'personality': 'Partnership-oriented, diplomatic, travels frequently'},
    8: {'name': 'Ashtami', 'nature': 'Unstable', 'personality': 'Transformative, secretive, occult interest, struggles then rises'},
    9: {'name': 'Navami', 'nature': 'Unstable', 'personality': 'Aggressive, creates enemies, but dharmic warrior'},
    10: {'name': 'Dashami', 'nature': 'Stable', 'personality': 'Career-focused, authoritative, righteous, famous'},
    11: {'name': 'Ekadashi', 'nature': 'Stable', 'personality': 'Devoted, fasting ability, gains, friends help, spiritual'},
    12: {'name': 'Dwadashi', 'nature': 'Stable', 'personality': 'Generous, charitable, spiritual, expenses on good causes'},
    13: {'name': 'Trayodashi', 'nature': 'Stable', 'personality': 'Lucky, victorious, friendships, social, joyful'},
    14: {'name': 'Chaturdashi', 'nature': 'Unstable', 'personality': 'Fierce, angry, but extremely talented, destroys opposition'},
    15: {'name': 'Purnima', 'nature': 'Stable', 'personality': 'Complete, luminous, popular, emotional, public figure'},
    30: {'name': 'Amavasya', 'nature': 'Unstable', 'personality': 'Introspective, hidden power, spiritual, ancestors connection'},
}


class TimeSystems:
    def __init__(self, date: datetime = None, latitude: float = 28.6139):
        self.date = date or datetime.now()
        self.latitude = latitude
        self.sunrise_hour = 6.0  # Approximate
        self.sunset_hour = 18.0

    def get_choghadiya(self) -> Dict:
        """Get current and upcoming Choghadiya periods."""
        weekday = self.date.weekday()
        day_chog = CHOGHADIYA_DAY.get(weekday, CHOGHADIYA_DAY[0])

        day_duration = (self.sunset_hour - self.sunrise_hour) / 8  # 8 periods in day
        current_hour = self.date.hour + self.date.minute / 60

        periods = []
        current_period = None
        for i, (name, lord, nature) in enumerate(day_chog):
            start = self.sunrise_hour + (i * day_duration)
            end = start + day_duration
            period = {
                'name': name, 'lord': lord, 'nature': nature,
                'start': f'{int(start):02d}:{int((start % 1) * 60):02d}',
                'end': f'{int(end):02d}:{int((end % 1) * 60):02d}',
                'is_current': start <= current_hour < end,
            }
            periods.append(period)
            if period['is_current']:
                current_period = period

        return {
            'current': current_period,
            'periods': periods,
            'date': self.date.strftime('%Y-%m-%d'),
        }

    def get_hora(self) -> Dict:
        """Get current planetary hour (Hora)."""
        weekday = self.date.weekday()
        start_planet = DAY_START_HORA.get(weekday, 'Sun')
        start_idx = HORA_SEQUENCE.index(start_planet)

        current_hour = self.date.hour + self.date.minute / 60
        hora_duration = 1.0  # Each hora = 1 hour (simplified)

        hours_from_sunrise = current_hour - self.sunrise_hour
        if hours_from_sunrise < 0:
            hours_from_sunrise += 24

        hora_index = int(hours_from_sunrise) % 7
        current_planet = HORA_SEQUENCE[(start_idx + hora_index) % 7]

        good_for = {
            'Sun': 'Government work, authority matters, father',
            'Moon': 'Travel, public dealings, mother, emotions',
            'Mars': 'Surgery, competition, property, courage',
            'Mercury': 'Business, communication, writing, study',
            'Jupiter': 'Religious acts, teaching, legal, finance',
            'Venus': 'Romance, arts, beauty, luxury purchases',
            'Saturn': 'Labor, discipline, mining, serving poor',
        }

        return {
            'current_hora': current_planet,
            'good_for': good_for.get(current_planet, ''),
            'hora_number': hora_index + 1,
            'day_lord': start_planet,
        }

    def get_abhijit_muhurta(self) -> Dict:
        """
        Abhijit Muhurta — the universally auspicious 48-minute window.
        Occurs around local noon (11:36 AM to 12:24 PM approximately).
        """
        midday = (self.sunrise_hour + self.sunset_hour) / 2
        abhijit_start = midday - 0.4  # ~24 min before noon
        abhijit_end = midday + 0.4    # ~24 min after noon

        current_hour = self.date.hour + self.date.minute / 60
        is_active = abhijit_start <= current_hour <= abhijit_end

        return {
            'start': f'{int(abhijit_start):02d}:{int((abhijit_start % 1) * 60):02d}',
            'end': f'{int(abhijit_end):02d}:{int((abhijit_end % 1) * 60):02d}',
            'is_active': is_active,
            'description': 'Universally auspicious window — good for any new beginning',
            'note': 'Abhijit Muhurta overrides most inauspicious factors',
        }

    def get_tithi_personality(self, tithi_number: int) -> Dict:
        """Get personality profile based on birth Tithi."""
        if tithi_number > 15:
            tithi_number = tithi_number - 15  # Krishna Paksha maps to same tithis
        data = TITHI_PERSONALITY.get(tithi_number, TITHI_PERSONALITY[1])
        return data

    def generate_daily_timing(self) -> Dict:
        return {
            'date': self.date.strftime('%Y-%m-%d %H:%M'),
            'choghadiya': self.get_choghadiya(),
            'hora': self.get_hora(),
            'abhijit_muhurta': self.get_abhijit_muhurta(),
        }


def get_daily_timing(date: datetime = None) -> Dict:
    ts = TimeSystems(date)
    return ts.generate_daily_timing()
