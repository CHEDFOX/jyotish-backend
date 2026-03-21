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
from .charts.bhava_chalit import BhavaChalit
from .predictions.timing_engine import TimingEngine
from .tajika.varshaphal import Varshaphal
from .remedies.remedies import RemediesEngine
from .dashas.chara_dasha import CharaDasha
from .prashna.prashna import PrashnaKundli
from .nadi.bhrigu_nandi import BhriguNandiNadi
from .kp.kp_complete import KPComplete
from .charts.sudarshana import SudarshanChakra
from .charts.varga_analysis import VargaAnalysis
from .predictions.medical_astrology import MedicalAstrology
from .transits.transit_deep import TransitDeep
from .predictions.classical_rules import ClassicalRules
from .muhurta.time_systems import TimeSystems
from .predictions.personality import PersonalityEngine
from .dashas.kalachakra_dasha import KalachakraDasha
from .dashas.narayana_dasha import NarayanaDasha
from .dashas.dasha_pravesh import DashaPravesh
from .jaimini.argala import ArgalaAnalysis
from .charts.sarvatobhadra import SarvatobhadraChakra
from .parashara.ishta_kashta import IshtaKashta
from .predictions.nakshatra_profiles import NakshatraProfiles
from .muhurta.muhurta_selector import MuhurtaSelector
from .predictions.life_timeline import LifeTimeline, ChartStrength, CrossSystemConfidence
from .predictions.baby_names import BabyNameGenerator
from .compatibility.synastry import Synastry
from .predictions.planetary_returns import PlanetaryReturns
from .numerology.core import NumerologyEngine
from .vastu.vastu import VastuAnalysis
from .chakra.chakra import ChakraAnalysis
from .predictions.career_aptitude import CareerAptitude
from .predictions.daily_ritual import DailyRitual, Biorhythm
from .transits.ashtakavarga_transit import AshtakavargaTransit
from .transits.future_transits import FutureTransitCalculator
from .parashara.yoga_timing import YogaTiming
from .dashas.pratyantar import PratyantarDasha
from .transits.transit_aspects import TransitNatalAspects
from .predictions.weekly_forecast import WeeklyForecast
from .kp.kp_horary import KPHorary
from .parashara.shadbala_complete import ShadbalaComplete
from .parashara.retrograde_natal import RetrogradeNatal
from .parashara.pushkara import PushkaraAnalysis
from .transits.eclipse_calendar import EclipseCalendar

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
from .predictions.time_query import TimeQueryEngine
from .predictions.realtime_dashboard import RealtimeDashboard
from .predictions.past_event import PastEventExplainer
from .predictions.hour_query import HourQuery
from .predictions.location_analysis import LocationAnalysis
from .predictions.dynamic_extras import DynamicRemedies, LuckyNumberFinder, DynamicMantra, ColorMetalFood
from .predictions.chart_promise import ChartPromise


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
    
    def predict_event(self, event: str, months_ahead: int = 24) -> Dict:
        """Predict timing for a life event (marriage, career, etc)."""
        self._ensure_chart()
        te = TimingEngine(self)
        return te.predict_event_timing(event)

    def scan_all_predictions(self) -> Dict:
        """Scan all major life events ranked by probability."""
        self._ensure_chart()
        te = TimingEngine(self)
        return te.scan_all_events()

    def get_period_analysis(self, months: int = 3) -> Dict:
        """What themes dominate the next N months."""
        self._ensure_chart()
        te = TimingEngine(self)
        return te.get_period_analysis(months)

    def get_varshaphal(self, year: int) -> Dict:
        """Get complete annual horoscope (Varshaphal) for a given year."""
        self._ensure_chart()
        vp = Varshaphal(self, year)
        return vp.generate_full_varshaphal()

    def get_annual_prediction(self, year: int) -> Dict:
        """Quick annual prediction — overall rating + key factors."""
        result = self.get_varshaphal(year)
        return {
            "year": year,
            "rating": result["overall"]["rating"],
            "score": result["overall"]["score"],
            "summary": result["overall"]["summary"],
            "year_lord": result["year_lord"]["planet"],
            "year_lord_strength": result["year_lord"]["strength"],
            "muntha_house": result["muntha"]["house"],
            "muntha_strength": result["muntha"]["strength"],
            "tajika_yogas_count": len(result["tajika_yogas"]),
        }













    def get_ashtakavarga_transits(self) -> Dict:
        """Personalized transit scoring using Ashtakavarga bindus."""
        self._ensure_chart()
        return AshtakavargaTransit(self).score_all_current_transits()

    def get_future_transits(self, months: int = 24) -> Dict:
        """Find when major planets change signs in next N months."""
        self._ensure_chart()
        return FutureTransitCalculator(self).find_all_major_transits(months)

    def get_yoga_timing(self) -> list:
        """When does each yoga activate based on dasha."""
        self._ensure_chart()
        return YogaTiming(self).time_yogas()

    def get_pratyantar_dasha(self) -> Dict:
        """3rd level dasha — narrows timing to weeks."""
        self._ensure_chart()
        return PratyantarDasha(self).calculate_pratyantar()

    def get_transit_aspects(self) -> list:
        """Transit planet aspects on natal planets."""
        self._ensure_chart()
        return TransitNatalAspects(self).check_aspects()

    def get_weekly_forecast(self) -> Dict:
        """7-day personalized prediction."""
        self._ensure_chart()
        return WeeklyForecast(self).generate_weekly()

    def get_shadbala_complete(self) -> Dict:
        """Full 6-fold planetary strength."""
        self._ensure_chart()
        return ShadbalaComplete(self).calculate_all()

    def get_natal_retrogrades(self) -> Dict:
        """Past-life karma from natal retrograde planets."""
        self._ensure_chart()
        return RetrogradeNatal(self).analyze()

    def get_pushkara(self) -> Dict:
        """Pushkara Navamsa and Bhaga lucky degrees."""
        self._ensure_chart()
        return PushkaraAnalysis(self).check_pushkara()

    def get_eclipse_calendar(self) -> Dict:
        """Upcoming eclipses and personal impact."""
        self._ensure_chart()
        return EclipseCalendar(self).generate_eclipse_report()
    def get_vastu(self) -> Dict:
        """Vastu Shastra — lucky directions based on chart."""
        self._ensure_chart()
        return VastuAnalysis(self).generate_vastu_report()

    def get_chakra_analysis(self) -> Dict:
        """Chakra mapping — blocked/overactive energy centers."""
        self._ensure_chart()
        return ChakraAnalysis(self).analyze_chakras()

    def get_career_aptitude(self) -> Dict:
        """Career aptitude percentages across 14 fields."""
        self._ensure_chart()
        return CareerAptitude(self).calculate_aptitude()

    def get_daily_ritual(self) -> Dict:
        """Personalized daily ritual for today."""
        self._ensure_chart()
        return DailyRitual(self).get_daily_ritual()

    def get_biorhythm(self) -> Dict:
        """Physical/emotional/intellectual biorhythm cycles."""
        from datetime import date as dt_date
        bd = self.birth_dt
        return Biorhythm(dt_date(bd.year, bd.month, bd.day)).calculate()
    def get_numerology(self, name: str = '') -> Dict:
        """Complete numerology report from birth date + optional name."""
        from datetime import date as dt_date
        bd = self.birth_dt
        ne = NumerologyEngine(name, dt_date(bd.year, bd.month, bd.day))
        return ne.generate_full_report()

    def get_name_numerology(self, name: str) -> Dict:
        """Analyze name vibration (Chaldean + Pythagorean)."""
        from datetime import date as dt_date
        bd = self.birth_dt
        ne = NumerologyEngine(name, dt_date(bd.year, bd.month, bd.day))
        return {'namank': ne.get_namank(), 'correction': ne.suggest_name_correction()}

    def get_personal_day(self) -> Dict:
        """What number rules today for this person."""
        from datetime import date as dt_date
        bd = self.birth_dt
        ne = NumerologyEngine(birth_date=dt_date(bd.year, bd.month, bd.day))
        return {'year': ne.get_personal_year(), 'month': ne.get_personal_month(), 'day': ne.get_personal_day()}
    def find_muhurta(self, event: str = 'general', days: int = 90) -> Dict:
        """Find best auspicious dates for an event."""
        ms = MuhurtaSelector(self.latitude, self.longitude)
        return ms.find_auspicious_dates(event, days)

    def get_life_timeline(self, years: int = 5) -> Dict:
        """5-year life prediction combining all systems."""
        self._ensure_chart()
        return LifeTimeline(self).generate_timeline(years)

    def get_chart_strength(self) -> Dict:
        """Single 0-100 chart strength score."""
        self._ensure_chart()
        return ChartStrength(self).calculate()

    def validate_event(self, event: str) -> Dict:
        """Cross-system confidence for an event prediction."""
        self._ensure_chart()
        return CrossSystemConfidence(self).validate_event(event)

    def get_baby_names(self, gender: str = 'both') -> Dict:
        """Baby name suggestions based on Moon nakshatra pada."""
        self._ensure_chart()
        nak = self._planets.get('Moon', {}).get('nakshatra_name', '')
        pada = self._planets.get('Moon', {}).get('pada', 1)
        return BabyNameGenerator(nak, pada).generate(gender)

    def get_synastry(self, other_engine) -> Dict:
        """Deep compatibility between two charts."""
        self._ensure_chart()
        return Synastry(self, other_engine).generate_synastry()

    def get_planetary_returns(self) -> Dict:
        """Track Saturn/Jupiter/Rahu returns — life-changing periods."""
        self._ensure_chart()
        return PlanetaryReturns(self).get_all_returns()
    def get_kalachakra_dasha(self) -> Dict:
        """Kalachakra Dasha — most complex timing system."""
        self._ensure_chart()
        kc = KalachakraDasha(self._planets['Moon']['longitude'], self.birth_dt)
        return kc.get_current_dasha()

    def get_narayana_dasha(self) -> Dict:
        """Narayana Dasha — Jaimini sign-based (K.N. Rao school)."""
        self._ensure_chart()
        nd = NarayanaDasha(self._planets, self.ascendant_rashi, self.birth_dt)
        return nd.get_current_dasha()

    def get_argala(self) -> Dict:
        """Argala — Jaimini planetary intervention analysis."""
        self._ensure_chart()
        return ArgalaAnalysis(self._planets, self.ascendant_rashi).analyze_all_houses()

    def get_sarvatobhadra(self) -> Dict:
        """Sarvatobhadra Chakra — nakshatra vedha from transits."""
        self._ensure_chart()
        transit = self.ephemeris.get_current_transits()
        return SarvatobhadraChakra(self._planets).analyze_current_vedhas(transit)

    def get_ishta_kashta(self) -> Dict:
        """Ishta/Kashta Phala — benefic/malefic strength per planet."""
        self._ensure_chart()
        return IshtaKashta(self._planets, self.ascendant_rashi).calculate_all()

    def get_nakshatra_profile(self) -> Dict:
        """108-pada nakshatra profile for Moon."""
        self._ensure_chart()
        np = NakshatraProfiles(self)
        return {'moon_profile': np.get_moon_pada_profile(), 'all_planets': np.get_all_planet_pada_info()}
    def get_medical_report(self) -> Dict:
        """Health vulnerabilities, longevity, maraka analysis."""
        self._ensure_chart()
        return MedicalAstrology(self).generate_medical_report()

    def get_transit_deep(self) -> Dict:
        """Deep transit analysis: gochar, sade sati, retrogrades, eclipses."""
        self._ensure_chart()
        return TransitDeep(self).generate_full_transit_report()

    def get_daily_timing(self) -> Dict:
        """Choghadiya, Hora, Abhijit Muhurta for today."""
        from datetime import datetime as dt
        return TimeSystems(dt.now()).generate_daily_timing()

    def get_personality(self) -> Dict:
        """Full personality profile: Moon sign, Ascendant, Nakshatra, Dasha shift."""
        self._ensure_chart()
        return PersonalityEngine(self).generate_full_personality()
    def get_sudarshana(self, current_age: int = None) -> Dict:
        """Get Sudarshana Chakra triple-ring analysis."""
        self._ensure_chart()
        sc = SudarshanChakra(self._planets, self.ascendant_rashi)
        if current_age:
            return sc.get_life_overview(current_age)
        return sc.get_full_cycle()

    def get_varga_analysis(self) -> Dict:
        """Deep analysis of all key divisional charts (D3,D7,D9,D10,D12,D24)."""
        self._ensure_chart()
        va = VargaAnalysis(self)
        return va.generate_full_varga_analysis()

    def get_navamsa_analysis(self) -> Dict:
        """Detailed D9 Navamsa analysis for marriage."""
        self._ensure_chart()
        va = VargaAnalysis(self)
        return va.analyze_navamsa()

    def get_career_analysis(self) -> Dict:
        """Detailed D10 Dasamsa career analysis."""
        self._ensure_chart()
        va = VargaAnalysis(self)
        return va.analyze_dasamsa()
    def get_kp_complete(self) -> Dict:
        """Get complete KP analysis with Placidus cusps and significators."""
        self._ensure_chart()
        kp = KPComplete(self)
        return kp.generate_full_kp_report()

    def kp_event_analysis(self, event: str) -> Dict:
        """KP analysis for specific event (marriage, career, etc)."""
        self._ensure_chart()
        kp = KPComplete(self)
        return kp.analyze_event_kp(event)

    def kp_verify_event(self, event: str) -> Dict:
        """Verify event using KP + Ruling Planets."""
        self._ensure_chart()
        kp = KPComplete(self)
        return kp.verify_event_with_rp(event)
    def get_nadi_reading(self) -> Dict:
        """Get Bhrigu Nandi Nadi reading — supernaturally specific predictions."""
        self._ensure_chart()
        nadi = BhriguNandiNadi(self)
        return nadi.generate_full_nadi_report()
    def cast_prashna(self, category: str = 'general') -> Dict:
        """Cast Prashna chart using user's location. No birth data needed for chart — uses current time."""
        from datetime import datetime as dt
        pk = PrashnaKundli(dt.utcnow(), self.latitude, self.longitude)
        return pk.generate_full_prashna(category)
    def get_chara_dasha(self) -> Dict:
        """Get current Chara Dasha (Jaimini sign-based timing)."""
        self._ensure_chart()
        cd = CharaDasha(self._planets, self.ascendant_rashi, self.birth_dt)
        return cd.get_current_dasha()

    def get_chara_dasha_analysis(self) -> Dict:
        """Deep analysis of current Chara Dasha period."""
        self._ensure_chart()
        cd = CharaDasha(self._planets, self.ascendant_rashi, self.birth_dt)
        return cd.analyze_current_period()

    def cross_validate_dashas(self) -> Dict:
        """Cross-validate Vimshottari and Chara Dasha for confidence scoring."""
        self._ensure_chart()
        vim = self.get_vimshottari_dasha()
        cd = CharaDasha(self._planets, self.ascendant_rashi, self.birth_dt)
        return cd.cross_validate_with_vimshottari(vim)
    def get_remedies(self) -> Dict:
        """Get complete personalized remedies (gemstones, mantras, rituals)."""
        self._ensure_chart()
        re = RemediesEngine(self)
        return re.generate_full_remedies()

    def get_gemstone_recommendations(self) -> list:
        """Get gemstone recommendations only."""
        self._ensure_chart()
        re = RemediesEngine(self)
        return re.recommend_gemstones()
    def get_bhava_chalit(self) -> Dict:
        """Get Bhava Chalit (cusp-based) chart with shift analysis."""
        self._ensure_chart()
        bc = BhavaChalit(self._planets, self._ascendant)
        return bc.generate_bhava_chalit()

    def get_bhava_strengths(self) -> Dict:
        """Get planet strength by Bhava position (Madhya vs Sandhi)."""
        self._ensure_chart()
        bc = BhavaChalit(self._planets, self._ascendant)
        return bc.all_planet_bhava_strengths()


    def query_time(self, target_date: str, end_date: str = None) -> Dict:
        """Query any date or period. Format: YYYY-MM-DD."""
        self._ensure_chart()
        from datetime import datetime as dt
        start = dt.strptime(target_date, '%Y-%m-%d')
        tq = TimeQueryEngine(self)
        if end_date:
            end = dt.strptime(end_date, '%Y-%m-%d')
            return tq.query_period(start, end)
        return tq.query_date(start)

    def query_month(self, year: int, month: int) -> Dict:
        """Query a specific month."""
        self._ensure_chart()
        return TimeQueryEngine(self).query_month(year, month)

    def query_year_detailed(self, year: int) -> Dict:
        """Month-by-month analysis of a year."""
        self._ensure_chart()
        return TimeQueryEngine(self).query_year(year)

    def get_realtime_dashboard(self) -> Dict:
        """Complete snapshot of this moment for this person."""
        self._ensure_chart()
        return RealtimeDashboard(self).snapshot()

    def explain_past_event(self, event_date: str, event_type: str, desc: str = '') -> Dict:
        """Why did a past event happen? Reverse astrology."""
        self._ensure_chart()
        return PastEventExplainer(self).explain_event(event_date, event_type, desc)

    def validate_life_events(self, events: list) -> Dict:
        """Validate multiple past events against astrology."""
        self._ensure_chart()
        return PastEventExplainer(self).validate_life_events(events)

    def analyze_hour(self, target_dt: str, activity: str = 'general') -> Dict:
        """Hour-level analysis. Format: YYYY-MM-DD HH:MM."""
        self._ensure_chart()
        from datetime import datetime as dt
        t = dt.strptime(target_dt, '%Y-%m-%d %H:%M')
        return HourQuery(self).analyze_hour(t, activity)

    def analyze_location(self, city: str, lat: float = None, lng: float = None) -> Dict:
        """Relocation chart for a city."""
        self._ensure_chart()
        return LocationAnalysis(self).analyze_city(city, lat, lng)

    def compare_locations(self, cities: list = None) -> Dict:
        """Compare multiple cities."""
        self._ensure_chart()
        return LocationAnalysis(self).compare_cities(cities)

    def get_dynamic_remedies(self) -> Dict:
        """Transit-aware remedies that change monthly."""
        self._ensure_chart()
        return DynamicRemedies(self).get_current_remedies()

    def get_lucky_numbers(self) -> Dict:
        """Lucky phone/car/house numbers."""
        self._ensure_chart()
        return LuckyNumberFinder(self).find_lucky()

    def get_dynamic_mantra(self) -> Dict:
        """Best mantra RIGHT NOW based on hora + dasha."""
        self._ensure_chart()
        return DynamicMantra(self).get_current_mantra()

    def get_color_metal_food(self) -> Dict:
        """What to wear, eat, use today."""
        self._ensure_chart()
        return ColorMetalFood(self).get_today()

    def get_classical_analysis(self, event: str = None) -> Dict:
        """Classical text-based life event analysis. Every rule from BPHS/Phaladeepika. No invented scores."""
        self._ensure_chart()
        try:
            cr = ClassicalRules(self)
            if event:
                event_map = {"childbirth": "children", "travel_foreign": "foreign", "health_issue": "health"}
                mapped = event_map.get(event, event)
                result = cr.evaluate(mapped)
                return result
            else:
                events = ["marriage", "children", "wealth", "career", "spiritual", "health",
                          "foreign", "property", "education", "longevity", "father", "mother",
                          "siblings", "business", "love", "fame"]
                results = {}
                for ev in events:
                    r = cr.evaluate(ev)
                    results[ev] = {"summary": r["summary"], "rules_fired": r["rules_fired"],
                                   "supports": len(r["supports"]), "opposes": len(r["opposes"]),
                                   "denials": r["denial_count"],
                                   "top_rules": [rule["text"] for rule in r["supports"][:3]] + [rule["text"] for rule in r["opposes"][:2]]}
                return {"type": "full_life_reading", "events": results}
        except Exception as e:
            return {"error": str(e)[:200]}

    def get_chart_promise(self, event: str = None) -> Dict:
        """Lifetime promise — does chart support this event ever?"""
        self._ensure_chart()
        cp = ChartPromise(self)
        if event:
            return cp.evaluate(event)
        return cp.evaluate_all()

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
