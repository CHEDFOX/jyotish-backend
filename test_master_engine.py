"""
Test Master Jyotish Engine
"""
import sys
sys.path.insert(0, '/var/www/jyotish/backend')

from datetime import datetime

print("=" * 60)
print("TESTING MASTER JYOTISH ENGINE")
print("=" * 60)

try:
    from app.services.jyotish_engine import JyotishEngine, create_engine
    print("✅ JyotishEngine imported successfully!")
    
    # Create engine for sample birth
    birth_dt = datetime(1990, 5, 15, 10, 30)
    lat = 28.6139  # Delhi
    lon = 77.2090
    
    print(f"\n📅 Birth: {birth_dt}")
    print(f"📍 Location: Delhi ({lat}, {lon})")
    
    engine = create_engine(birth_dt, lat, lon)
    print("✅ Engine created!")
    
    # Test basic chart
    print("\n[TEST 1] Rashi Chart...")
    chart = engine.get_rashi_chart()
    print(f"  ✅ Ascendant: {chart['ascendant']['rashi_name']}")
    print(f"  ✅ Moon: {chart['planets']['Moon']['rashi_name']}")
    print(f"  ✅ Sun: {chart['planets']['Sun']['rashi_name']}")
    
    # Test Navamsa
    print("\n[TEST 2] Navamsa Chart...")
    navamsa = engine.get_navamsa_chart()
    print(f"  ✅ Division: D{navamsa['division']}")
    print(f"  ✅ Moon Navamsa: {navamsa['planets']['Moon']['rashi_name']}")
    
    # Test Yogas
    print("\n[TEST 3] Yogas...")
    yogas = engine.get_yogas()
    print(f"  ✅ Total Yogas: {yogas['summary']['total_yogas']}")
    print(f"  ✅ Positive: {yogas['summary']['positive_yogas']}")
    print(f"  ✅ Negative: {yogas['summary']['negative_yogas']}")
    
    # Test Dasha
    print("\n[TEST 4] Vimshottari Dasha...")
    dasha = engine.get_vimshottari_dasha()
    print(f"  ✅ Current: {dasha['dasha_string']}")
    print(f"  ✅ Mahadasha: {dasha['mahadasha']['lord']}")
    print(f"  ✅ Antardasha: {dasha['antardasha']['lord']}")
    
    # Test Jaimini
    print("\n[TEST 5] Jaimini Karakas...")
    karakas = engine.get_jaimini_karakas()
    print(f"  ✅ Atmakaraka: {karakas['Atmakaraka']['planet']}")
    print(f"  ✅ Darakaraka: {karakas['Darakaraka']['planet']}")
    
    # Test Manglik
    print("\n[TEST 6] Manglik Check...")
    manglik = engine.check_manglik()
    print(f"  ✅ Is Manglik: {manglik['is_manglik']}")
    print(f"  ✅ Strength: {manglik['dosha_strength']}")
    
    # Test Panchanga
    print("\n[TEST 7] Today's Panchanga...")
    panchanga = engine.get_panchanga()
    print(f"  ✅ Tithi: {panchanga['tithi']['tithi_name']}")
    print(f"  ✅ Nakshatra: {panchanga['nakshatra']['nakshatra_name']}")
    print(f"  ✅ Yoga: {panchanga['yoga']['yoga_name']}")
    
    # Test Prediction Data (for AI)
    print("\n[TEST 8] Prediction Data...")
    pred = engine.get_prediction_data()
    print(f"  ✅ Ascendant: {pred['ascendant']['rashi']}")
    print(f"  ✅ Moon Sign: {pred['moon']['rashi']}")
    print(f"  ✅ Current Dasha: {pred['current_dasha']['dasha_string']}")
    print(f"  ✅ Transits: {pred['transits']}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ENGINE IS READY!")
    print("=" * 60)

except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
