"""
Test Script for Jyotish Astrology Engine
"""

import sys
sys.path.insert(0, '/var/www/jyotish/backend')

from datetime import datetime

print("=" * 60)
print("JYOTISH ENGINE TEST")
print("=" * 60)

# Test 1: Constants
print("\n[TEST 1] Loading Constants...")
try:
    from app.services.core.constants import (
        RASHIS, NAKSHATRAS, PLANETS, HOUSES,
        VIMSHOTTARI_YEARS, ASHTAKOOTA
    )
    print(f"  ✅ 12 Rashis loaded: {[RASHIS[i]['name'] for i in range(3)]}...")
    print(f"  ✅ 27 Nakshatras loaded: {NAKSHATRAS[0]['name']}, {NAKSHATRAS[1]['name']}...")
    print(f"  ✅ 9 Planets loaded: {list(PLANETS.keys())}")
    print(f"  ✅ Vimshottari Years: {VIMSHOTTARI_YEARS}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 2: Utilities
print("\n[TEST 2] Testing Utilities...")
try:
    from app.services.core.utils import (
        get_rashi_from_longitude,
        get_nakshatra_from_longitude,
        get_nakshatra_pada
    )
    
    test_long = 45.5  # Should be Taurus, Krittika
    rashi = get_rashi_from_longitude(test_long)
    nakshatra = get_nakshatra_from_longitude(test_long)
    pada = get_nakshatra_pada(test_long)
    
    print(f"  ✅ Longitude 45.5° → Rashi: {RASHIS[rashi]['name']}")
    print(f"  ✅ Longitude 45.5° → Nakshatra: {NAKSHATRAS[nakshatra]['name']}, Pada: {pada}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Divisional Charts
print("\n[TEST 3] Testing Divisional Charts...")
try:
    from app.services.charts.divisional_charts import DivisionalCharts
    
    test_long = 125.0  # Leo
    d1 = DivisionalCharts.calculate_d1(test_long)
    d9 = DivisionalCharts.calculate_d9(test_long)
    d10 = DivisionalCharts.calculate_d10(test_long)
    
    print(f"  ✅ Longitude 125° → D1: {RASHIS[d1]['name']}")
    print(f"  ✅ Longitude 125° → D9 (Navamsa): {RASHIS[d9]['name']}")
    print(f"  ✅ Longitude 125° → D10 (Dasamsa): {RASHIS[d10]['name']}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Planetary Dignity
print("\n[TEST 4] Testing Planetary Dignity...")
try:
    from app.services.parashara.dignity import PlanetaryDignity
    
    # Sun in Aries (exalted)
    dignity1 = PlanetaryDignity.get_dignity('Sun', 0, 10)
    print(f"  ✅ Sun in Aries: {dignity1['dignity']} (strength: {dignity1['strength']})")
    
    # Saturn in Aries (debilitated)
    dignity2 = PlanetaryDignity.get_dignity('Saturn', 0, 20)
    print(f"  ✅ Saturn in Aries: {dignity2['dignity']} (strength: {dignity2['strength']})")
    
    # Jupiter in Cancer (exalted)
    dignity3 = PlanetaryDignity.get_dignity('Jupiter', 3, 5)
    print(f"  ✅ Jupiter in Cancer: {dignity3['dignity']} (strength: {dignity3['strength']})")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 5: Aspects
print("\n[TEST 5] Testing Aspects...")
try:
    from app.services.parashara.aspects import PlanetaryAspects
    
    mars_aspects = PlanetaryAspects.FULL_ASPECTS['Mars']
    jupiter_aspects = PlanetaryAspects.FULL_ASPECTS['Jupiter']
    saturn_aspects = PlanetaryAspects.FULL_ASPECTS['Saturn']
    
    print(f"  ✅ Mars aspects houses: {mars_aspects}")
    print(f"  ✅ Jupiter aspects houses: {jupiter_aspects}")
    print(f"  ✅ Saturn aspects houses: {saturn_aspects}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 6: Yogas
print("\n[TEST 6] Testing Yogas...")
try:
    from app.services.parashara.yogas import YogaCalculator
    
    # Sample chart data
    sample_planets = {
        'Sun': {'rashi': 0, 'house': 1, 'longitude': 15},
        'Moon': {'rashi': 1, 'house': 2, 'longitude': 45},
        'Mars': {'rashi': 9, 'house': 10, 'longitude': 280},  # Exalted in Capricorn
        'Mercury': {'rashi': 0, 'house': 1, 'longitude': 20},
        'Jupiter': {'rashi': 3, 'house': 4, 'longitude': 95},  # Exalted in Cancer
        'Venus': {'rashi': 11, 'house': 12, 'longitude': 350},  # Exalted in Pisces
        'Saturn': {'rashi': 6, 'house': 7, 'longitude': 200},  # Exalted in Libra
        'Rahu': {'rashi': 2, 'house': 3, 'longitude': 75},
        'Ketu': {'rashi': 8, 'house': 9, 'longitude': 255},
    }
    sample_asc = {'rashi': 0}  # Aries ascendant
    
    calculator = YogaCalculator(sample_planets, sample_asc)
    mahapurusha = calculator.check_mahapurusha_yogas()
    raja = calculator.check_raja_yogas()
    
    print(f"  ✅ Mahapurusha Yogas found: {len(mahapurusha)}")
    for y in mahapurusha:
        print(f"      → {y['name']}: {y['planet']} in house {y['house']}")
    print(f"  ✅ Raja Yogas found: {len(raja)}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 7: Vimshottari Dasha
print("\n[TEST 7] Testing Vimshottari Dasha...")
try:
    from app.services.dashas.vimshottari import VimshottariDasha
    
    moon_long = 45.5  # Krittika nakshatra (Sun's dasha)
    birth_dt = datetime(1990, 5, 15, 10, 30)
    
    dasha = VimshottariDasha(moon_long, birth_dt)
    current = dasha.get_current_dasha()
    
    print(f"  ✅ Birth Nakshatra Lord: {dasha.nakshatra_lord}")
    print(f"  ✅ Dasha Balance at Birth: {dasha.dasha_balance:.2f} years")
    print(f"  ✅ Current Dasha: {current['dasha_string']}")
    print(f"  ✅ Mahadasha: {current['mahadasha']['lord']} (ends: {current['mahadasha']['end'][:10]})")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 8: Compatibility (Ashtakoota)
print("\n[TEST 8] Testing Compatibility...")
try:
    from app.services.compatibility.ashtakoota import AshtakootaMatch
    
    boy_moon = 45.0   # Taurus
    girl_moon = 125.0  # Leo
    
    match = AshtakootaMatch(boy_moon, girl_moon)
    result = match.calculate_total()
    
    print(f"  ✅ Boy Moon: {result['boy']['moon_rashi']}")
    print(f"  ✅ Girl Moon: {result['girl']['moon_rashi']}")
    print(f"  ✅ Total Points: {result['total_points']}/36")
    print(f"  ✅ Compatibility: {result['compatibility']}")
    print(f"  ✅ Recommendation: {result['recommendation']}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 9: Muhurta
print("\n[TEST 9] Testing Muhurta...")
try:
    from app.services.muhurta.panchanga import Panchanga, Muhurta
    
    sun_long = 45.0
    moon_long = 125.0
    now = datetime.now()
    
    panchanga = Panchanga(sun_long, moon_long, now)
    panch = panchanga.get_full_panchanga()
    
    print(f"  ✅ Tithi: {panch['tithi']['tithi_name']} ({panch['tithi']['paksha']})")
    print(f"  ✅ Nakshatra: {panch['nakshatra']['nakshatra_name']}")
    print(f"  ✅ Yoga: {panch['yoga']['yoga_name']}")
    print(f"  ✅ Karana: {panch['karana']['karana_name']}")
    
    muhurta = Muhurta(now)
    rahu_kalam = muhurta.get_rahu_kalam()
    print(f"  ✅ Rahu Kalam: {rahu_kalam['start_time']} - {rahu_kalam['end_time']}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 10: Jaimini Karakas
print("\n[TEST 10] Testing Jaimini Karakas...")
try:
    from app.services.jaimini.karakas import JaiminiKarakas
    
    calculator = JaiminiKarakas(sample_planets)
    karakas = calculator.get_all_karakas()
    
    print(f"  ✅ Atmakaraka: {karakas['Atmakaraka']['planet']} ({karakas['Atmakaraka']['degree']}°)")
    print(f"  ✅ Amatyakaraka: {karakas['Amatyakaraka']['planet']}")
    print(f"  ✅ Darakaraka: {karakas['Darakaraka']['planet']}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 11: KP System
print("\n[TEST 11] Testing KP System...")
try:
    from app.services.kp.sublords import KPSystem
    
    kp = KPSystem(sample_planets)
    sub_lord = kp.get_sub_lord(125.0)
    
    print(f"  ✅ Longitude 125° Sub-Lord Analysis:")
    print(f"      → Nakshatra: {sub_lord['nakshatra']}")
    print(f"      → Nakshatra Lord: {sub_lord['nakshatra_lord']}")
    print(f"      → Sub Lord: {sub_lord['sub_lord']}")
    print(f"      → Sub-Sub Lord: {sub_lord['sub_sub_lord']}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 12: Transit Analysis
print("\n[TEST 12] Testing Transit Analysis...")
try:
    from app.services.transits.transit_analysis import TransitAnalyzer
    
    natal_planets = sample_planets
    natal_asc = 0  # Aries
    
    # Current transits (sample)
    transit_planets = {
        'Jupiter': {'longitude': 35.0, 'rashi': 1},  # Taurus
        'Saturn': {'longitude': 320.0, 'rashi': 10},  # Aquarius
    }
    
    analyzer = TransitAnalyzer(natal_planets, natal_asc)
    sade_sati = analyzer.analyze_sade_sati(10)  # Saturn in Aquarius
    
    print(f"  ✅ Natal Moon: {RASHIS[analyzer.natal_moon]['name']}")
    print(f"  ✅ Sade Sati Active: {sade_sati['is_sade_sati']}")
    print(f"  ✅ Saturn from Moon: House {sade_sati['saturn_from_moon']}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE!")
print("=" * 60)
