"""
JYOTISH ENGINE - MASTER INTEGRATION
Single entry point for all astrological calculations
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Core imports
from .core.constants import RASHIS, NAKSHATRAS, PLANETS, RASHI_NAMES, NAKSHATRA_NAMES
from .core.utils import (
    get_rashi_from_longitude, get_nakshatra_from_longitude,
    get_nakshatra_pada, normalize_longitude
)
from .core.ephemeris import Ephemeris, get_ephemeris

# Chart imports
from .charts.divisional_charts import DivisionalCharts

# Parashara imports
from .parashara.dignity import PlanetaryDignity
from .parashara.aspects import PlanetaryAspects
from .parashara.yogas import YogaCalculator
from .parashara.shadbala import ShadbalaCalculator
from .parashara.ashtakavarga import AshtakavargaCalculator

# Dasha imports
from .dashas.vimshottari import VimshottariDasha
from .dashas.yogini import YoginiDasha
from .dashas.ashtottari import AshtottariDasha

# Compatibility imports
from .compatibility.ashtakoota import AshtakootaMatch
from .compatibility.manglik import ManglikAnalysis

# Muhurta imports
from .muhurta.panchanga import Panchanga, Muhurta

# Jaimini imports
from .jaimini.karakas import JaiminiKarakas, ArudhaPada

# KP imports
from .kp.sublords import KPSystem, RulingPlanets

# Transit imports
from .transits.transit_analysis import TransitAnalyzer


class JyotishEngine:
    """
    Master Jyotish Engine - Complete Vedic Astrology Calculator
    
    Usage:
        engine = JyotishEngine(birth_datetime, latitude, longitude)
        chart = engine.generate_complete_chart()
        predictions = engine.get_predictions()
    """
    
    def __init__(self, birth_datetime: datetime, latitude: float, longitude: float,
                 ayanamsa: str = 'LAHIRI', timezone_offset: float = None):
        """
        Initialize Jyotish Engine
        
        Args:
            birth_datetime: Birth date and time in LOCAL time
            latitude: Birth latitude  
            longitude: Birth longitude (geographic)
            ayanamsa: Ayanamsa system (LAHIRI, RAMAN, KP)
            timezone_offset: Hours from UTC. If None, auto-detected from coordinates + date.
        """
        from .core.timezone_utils import get_timezone_manager
        
        self.birth_local = birth_datetime
        self.latitude = latitude
        self.longitude = longitude
        self.ayanamsa = ayanamsa
        
        # Get timezone info (considers DST and historical changes)
        tz_manager = get_timezone_manager()
        tz_info = tz_manager.get_timezone_info(latitude, longitude, birth_datetime)
        
        if timezone_offset is None:
            timezone_offset = tz_info['offset_hours']
        
        self.tz_offset = timezone_offset
        self.tz_name = tz_info['timezone_name']
        self.tz_info = tz_info
        
        # Convert local time to UTC for Swiss Ephemeris calculations
        self.birth_dt = tz_manager.local_to_utc(birth_datetime, latitude, longitude, timezone_offset)
        
        self.ephemeris = get_ephemeris(ayanamsa)
        self._chart = None
        self._planets = None
        self._ascendant = None
    
    def _ensure_chart(self):
        if self._chart is None:
            self._chart = self.ephemeris.generate_chart(
                self.birth_dt, self.latitude, self.longitude
            )
            self._planets = self._chart['planets']
            self._ascendant = self._chart['ascendant']
    
    @property
    def planets(self) -> Dict:
        self._ensure_chart()
        return self._planets
    
    @property
    def ascendant(self) -> Dict:
        self._ensure_chart()
        return self._ascendant
    
    @property
    def ascendant_rashi(self) -> int:
        self._ensure_chart()
        return self._ascendant['rashi']
    
    def get_rashi_chart(self) -> Dict:
        self._ensure_chart()
        return self._chart
    
    def get_navamsa_chart(self) -> Dict:
        self._ensure_chart()
        return DivisionalCharts.generate_divisional_chart(self._planets, 9)
    
    def get_dasamsa_chart(self) -> Dict:
        self._ensure_chart()
        return DivisionalCharts.generate_divisional_chart(self._planets, 10)
    
    def get_all_divisional_charts(self) -> Dict:
        self._ensure_chart()
        return DivisionalCharts.generate_all_vargas(self._planets)
    
    def get_divisional_chart(self, division: int) -> Dict:
        self._ensure_chart()
        return DivisionalCharts.generate_divisional_chart(self._planets, division)
    
    def get_planetary_dignity(self) -> Dict:
        self._ensure_chart()
        return PlanetaryDignity.analyze_all_planets(self._planets, self.ascendant_rashi)
    
    def get_planetary_aspects(self) -> Dict:
        self._ensure_chart()
        return PlanetaryAspects.generate_aspect_table(self._planets)
    
    def get_shadbala(self) -> Dict:
        self._ensure_chart()
        calculator = ShadbalaCalculator(
            self._planets, self._ascendant, 
            self.birth_dt, self.latitude, self.longitude
        )
        return calculator.calculate_all_planets_shadbala()
    
    def get_ashtakavarga(self) -> Dict:
        self._ensure_chart()
        calculator = AshtakavargaCalculator(self._planets, self.ascendant_rashi)
        return calculator.calculate_sarvashtakavarga()
    
    def get_yogas(self) -> Dict:
        self._ensure_chart()
        calculator = YogaCalculator(self._planets, self._ascendant)
        return calculator.analyze_all_yogas()
    
    def get_raja_yogas(self) -> List[Dict]:
        yogas = self.get_yogas()
        return yogas['yogas'].get('raja', [])
    
    def get_dhana_yogas(self) -> List[Dict]:
        yogas = self.get_yogas()
        return yogas['yogas'].get('dhana', [])
    
    def get_vimshottari_dasha(self) -> Dict:
        self._ensure_chart()
        moon_long = self._planets['Moon']['longitude']
        dasha = VimshottariDasha(moon_long, self.birth_dt)
        return dasha.get_current_dasha()
    
    def get_vimshottari_periods(self, years: int = 120) -> List[Dict]:
        self._ensure_chart()
        moon_long = self._planets['Moon']['longitude']
        dasha = VimshottariDasha(moon_long, self.birth_dt)
        return dasha.calculate_mahadasha_periods(years)
    
    def get_yogini_dasha(self) -> Dict:
        self._ensure_chart()
        moon_long = self._planets['Moon']['longitude']
        dasha = YoginiDasha(moon_long, self.birth_dt)
        return dasha.get_current_dasha()
    
    def get_dasha_for_date(self, date: datetime) -> Dict:
        self._ensure_chart()
        moon_long = self._planets['Moon']['longitude']
        dasha = VimshottariDasha(moon_long, self.birth_dt)
        return dasha.get_dasha_for_date(date)
    
    def get_current_transits(self) -> Dict:
        self._ensure_chart()
        current_planets = self.ephemeris.get_current_transits()
        analyzer = TransitAnalyzer(self._planets, self.ascendant_rashi)
        return analyzer.get_current_transit_summary(current_planets)
    
    def get_transit_for_date(self, date: datetime) -> Dict:
        self._ensure_chart()
        transit_planets = self.ephemeris.get_transits_for_date(date)
        analyzer = TransitAnalyzer(self._planets, self.ascendant_rashi)
        return analyzer.get_current_transit_summary(transit_planets)
    
    def check_sade_sati(self) -> Dict:
        self._ensure_chart()
        current_planets = self.ephemeris.get_current_transits()
        saturn_rashi = current_planets['Saturn']['rashi']
        analyzer = TransitAnalyzer(self._planets, self.ascendant_rashi)
        return analyzer.analyze_sade_sati(saturn_rashi)
    
    def get_jaimini_karakas(self) -> Dict:
        self._ensure_chart()
        calculator = JaiminiKarakas(self._planets, include_rahu=True)
        return calculator.get_all_karakas()
    
    def get_arudha_padas(self) -> Dict:
        self._ensure_chart()
        calculator = ArudhaPada(self._planets, self.ascendant_rashi)
        return calculator.calculate_all_arudhas()
    
    def get_karakamsa(self) -> Dict:
        self._ensure_chart()
        asc_long = self._ascendant['longitude']
        nav_asc = DivisionalCharts.calculate_d9(asc_long)
        calculator = JaiminiKarakas(self._planets, include_rahu=True)
        return calculator.analyze_karakamsa(nav_asc)
    
    def get_kp_analysis(self) -> Dict:
        self._ensure_chart()
        kp = KPSystem(self._planets)
        planet_sublords = {}
        for planet, data in self._planets.items():
            planet_sublords[planet] = kp.get_sub_lord(data['longitude'])
        return {'planet_sublords': planet_sublords}
    
    def get_kp_significators(self, house: int) -> Dict:
        self._ensure_chart()
        kp = KPSystem(self._planets)
        return kp.get_house_significators(house)
    
    def match_compatibility(self, partner_moon_longitude: float) -> Dict:
        self._ensure_chart()
        my_moon = self._planets['Moon']['longitude']
        match = AshtakootaMatch(my_moon, partner_moon_longitude)
        return match.calculate_total()
    
    def check_manglik(self) -> Dict:
        self._ensure_chart()
        weekday = self.birth_dt.weekday()
        analyzer = ManglikAnalysis(self._planets, self.ascendant_rashi, weekday)
        return analyzer.full_analysis()
    
    def get_panchanga(self, date: datetime = None) -> Dict:
        if date is None:
            date = datetime.now()
        planets = self.ephemeris.get_transits_for_date(date)
        sun_long = planets['Sun']['longitude']
        moon_long = planets['Moon']['longitude']
        panchanga = Panchanga(sun_long, moon_long, date)
        return panchanga.get_full_panchanga()
    
    def get_muhurta(self, date: datetime = None) -> Dict:
        if date is None:
            date = datetime.now()
        muhurta = Muhurta(date)
        return muhurta.get_all_muhurtas()
    
    def generate_complete_chart(self) -> Dict:
        self._ensure_chart()
        return {
            'birth_details': {
                'datetime': self.birth_dt.isoformat(),
                'latitude': self.latitude,
                'longitude': self.longitude,
                'ayanamsa': self.ayanamsa,
            },
            'chart': self._chart,
            'ascendant': self._ascendant,
            'planets': self._planets,
            'dignity': self.get_planetary_dignity(),
            'navamsa': self.get_navamsa_chart(),
        }
    
    def generate_full_analysis(self) -> Dict:
        self._ensure_chart()
        return {
            'chart': self.generate_complete_chart(),
            'yogas': self.get_yogas(),
            'dasha': self.get_vimshottari_dasha(),
            'shadbala': self.get_shadbala(),
            'ashtakavarga': self.get_ashtakavarga(),
            'jaimini': {
                'karakas': self.get_jaimini_karakas(),
                'arudhas': self.get_arudha_padas(),
            },
            'transits': self.get_current_transits(),
            'manglik': self.check_manglik(),
        }
    
    def get_prediction_data(self) -> Dict:
        self._ensure_chart()
        return {
            'ascendant': {
                'rashi': self._ascendant['rashi_name'],
                'nakshatra': self._ascendant['nakshatra_name'],
            },
            'moon': {
                'rashi': self._planets['Moon']['rashi_name'],
                'nakshatra': self._planets['Moon']['nakshatra_name'],
                'house': self._planets['Moon']['house'],
            },
            'sun': {
                'rashi': self._planets['Sun']['rashi_name'],
                'house': self._planets['Sun']['house'],
            },
            'current_dasha': self.get_vimshottari_dasha(),
            'yogas_summary': self.get_yogas()['summary'],
            'strong_yogas': self.get_yogas()['highlights'][:3],
            'transits': self.get_current_transits()['overall_period'],
            'sade_sati': self.check_sade_sati()['is_sade_sati'],
        }


def create_engine(birth_datetime: datetime, latitude: float, longitude: float,
                  ayanamsa: str = 'LAHIRI') -> JyotishEngine:
    return JyotishEngine(birth_datetime, latitude, longitude, ayanamsa)
