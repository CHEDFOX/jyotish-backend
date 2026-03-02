"""
JYOTISH - Vedic Astrology Engine
================================
Core calculations using Swiss Ephemeris
"""

import swisseph as swe
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Zodiac Signs (Rashis)
RASHIS = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"
]

RASHIS_ENGLISH = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Nakshatras
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

NAKSHATRA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
    "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS,
    "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE
}


def initialize():
    swe.set_ephe_path(None)
    swe.set_sid_mode(swe.SIDM_LAHIRI)


def calculate_julian_day(year: int, month: int, day: int, hour: int, minute: int, timezone: float = 5.5) -> float:
    decimal_hours = hour + (minute / 60) - timezone
    return swe.julday(year, month, day, decimal_hours)


def get_planet_position(julian_day: float, planet_name: str) -> Dict:
    planet_id = PLANETS[planet_name]
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(julian_day, planet_id, flags)
    
    longitude = result[0]
    speed = result[3]
    
    rashi_index = int(longitude / 30)
    degree_in_rashi = longitude % 30
    nakshatra_index = int(longitude / (360 / 27))
    degree_in_nakshatra = longitude % (360 / 27)
    pada = int(degree_in_nakshatra / (360 / 108)) + 1
    lord_index = nakshatra_index % 9
    
    return {
        "longitude": round(longitude, 4),
        "rashi": RASHIS[rashi_index],
        "rashi_english": RASHIS_ENGLISH[rashi_index],
        "rashi_index": rashi_index,
        "degree": round(degree_in_rashi, 2),
        "nakshatra": NAKSHATRAS[nakshatra_index],
        "nakshatra_index": nakshatra_index,
        "pada": pada,
        "nakshatra_lord": NAKSHATRA_LORDS[lord_index],
        "retrograde": speed < 0
    }


def get_ascendant(julian_day: float, latitude: float, longitude: float) -> Dict:
    flags = swe.FLG_SIDEREAL
    houses, angles = swe.houses_ex(julian_day, latitude, longitude, b'W', flags)
    
    asc = angles[0]
    rashi_index = int(asc / 30)
    nakshatra_index = int(asc / (360 / 27))
    
    return {
        "longitude": round(asc, 4),
        "rashi": RASHIS[rashi_index],
        "rashi_english": RASHIS_ENGLISH[rashi_index],
        "rashi_index": rashi_index,
        "degree": round(asc % 30, 2),
        "nakshatra": NAKSHATRAS[nakshatra_index]
    }


def calculate_house(planet_rashi_index: int, ascendant_rashi_index: int) -> int:
    return ((planet_rashi_index - ascendant_rashi_index) % 12) + 1


def calculate_dasha(moon_longitude: float, birth_date: datetime) -> List[Dict]:
    nakshatra_index = int(moon_longitude / (360 / 27))
    lord_index = nakshatra_index % 9
    starting_lord = NAKSHATRA_LORDS[lord_index]
    
    nakshatra_span = 360 / 27
    position_in_nakshatra = (moon_longitude % nakshatra_span) / nakshatra_span
    
    sequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    start_index = sequence.index(starting_lord)
    
    dashas = []
    current_date = birth_date
    
    for i in range(18):
        lord = sequence[(start_index + i) % 9]
        total_years = DASHA_YEARS[lord]
        
        if i == 0:
            years = total_years * (1 - position_in_nakshatra)
        else:
            years = total_years
        
        days = int(years * 365.25)
        end_date = current_date + timedelta(days=days)
        
        dashas.append({
            "lord": lord,
            "start": current_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "years": round(years, 2)
        })
        
        current_date = end_date
    
    return dashas


def get_current_dasha(dashas: List[Dict], check_date: datetime = None) -> Optional[Dict]:
    if check_date is None:
        check_date = datetime.now()
    
    for dasha in dashas:
        start = datetime.strptime(dasha["start"], "%Y-%m-%d")
        end = datetime.strptime(dasha["end"], "%Y-%m-%d")
        if start <= check_date <= end:
            return dasha
    return None


def generate_kundli(name: str, year: int, month: int, day: int, hour: int, minute: int,
                    latitude: float, longitude: float, timezone: float = 5.5, gender: str = None) -> Dict:
    initialize()
    
    jd = calculate_julian_day(year, month, day, hour, minute, timezone)
    ascendant = get_ascendant(jd, latitude, longitude)
    
    planets = {}
    for planet_name in PLANETS.keys():
        position = get_planet_position(jd, planet_name)
        position["house"] = calculate_house(position["rashi_index"], ascendant["rashi_index"])
        planets[planet_name] = position
    
    # Calculate Ketu (opposite to Rahu)
    rahu = planets["Rahu"]
    ketu_longitude = (rahu["longitude"] + 180) % 360
    ketu_rashi_index = int(ketu_longitude / 30)
    ketu_nakshatra_index = int(ketu_longitude / (360 / 27))
    
    planets["Ketu"] = {
        "longitude": round(ketu_longitude, 4),
        "rashi": RASHIS[ketu_rashi_index],
        "rashi_english": RASHIS_ENGLISH[ketu_rashi_index],
        "rashi_index": ketu_rashi_index,
        "degree": round(ketu_longitude % 30, 2),
        "nakshatra": NAKSHATRAS[ketu_nakshatra_index],
        "nakshatra_index": ketu_nakshatra_index,
        "pada": int((ketu_longitude % (360/27)) / (360/108)) + 1,
        "nakshatra_lord": NAKSHATRA_LORDS[ketu_nakshatra_index % 9],
        "retrograde": True,
        "house": calculate_house(ketu_rashi_index, ascendant["rashi_index"])
    }
    
    birth_datetime = datetime(year, month, day, hour, minute)
    dashas = calculate_dasha(planets["Moon"]["longitude"], birth_datetime)
    current_dasha = get_current_dasha(dashas)
    
    return {
        "name": name,
        "gender": gender,
        "birth_details": {
            "date": f"{year}-{month:02d}-{day:02d}",
            "time": f"{hour:02d}:{minute:02d}",
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone
        },
        "ascendant": ascendant,
        "planets": planets,
        "dashas": dashas[:9],
        "current_dasha": current_dasha
    }


def calculate_matching(kundli1: Dict, kundli2: Dict) -> Dict:
    moon1 = kundli1["planets"]["Moon"]
    moon2 = kundli2["planets"]["Moon"]
    
    n1, n2 = moon1["nakshatra_index"], moon2["nakshatra_index"]
    r1, r2 = moon1["rashi_index"], moon2["rashi_index"]
    
    scores = {}
    
    # Varna (1 point)
    varna_map = [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]
    scores["varna"] = 1 if varna_map[r1] >= varna_map[r2] else 0
    
    # Vashya (2 points)
    scores["vashya"] = 2 if abs(r1 - r2) <= 4 else 1
    
    # Tara (3 points)
    tara_diff = (n2 - n1) % 9
    scores["tara"] = 3 if tara_diff in [1, 2, 4, 6, 8] else 1.5
    
    # Yoni (4 points)
    scores["yoni"] = 4 if (n1 % 14) == (n2 % 14) else 2
    
    # Graha Maitri (5 points)
    scores["graha_maitri"] = 5 if abs(r1 - r2) in [0, 4, 8] else 2.5
    
    # Gana (6 points)
    gana_map = [3, 2, 1] * 9
    g1, g2 = gana_map[n1], gana_map[n2]
    scores["gana"] = 6 if g1 == g2 else (3 if abs(g1-g2) == 1 else 0)
    
    # Bhakoot (7 points)
    diff = abs(r1 - r2)
    scores["bhakoot"] = 0 if diff in [2, 5, 6, 8, 9, 12] else 7
    
    # Nadi (8 points)
    scores["nadi"] = 0 if (n1 % 3) == (n2 % 3) else 8
    
    total = sum(scores.values())
    
    return {
        "person1": kundli1["name"],
        "person2": kundli2["name"],
        "scores": scores,
        "total": total,
        "max": 36,
        "percentage": round((total / 36) * 100, 1),
        "verdict": "Excellent" if total >= 30 else "Good" if total >= 24 else "Acceptable" if total >= 18 else "Not Recommended"
    }


def format_kundli_for_ai(kundli: Dict) -> str:
    lines = [f"=== KUNDLI FOR {kundli['name'].upper()} ==="]
    lines.append(f"Birth: {kundli['birth_details']['date']} at {kundli['birth_details']['time']}")
    if kundli.get('gender'):
        lines.append(f"Gender: {kundli['gender']}")
    lines.append(f"\nLAGNA: {kundli['ascendant']['rashi']} ({kundli['ascendant']['rashi_english']}) at {kundli['ascendant']['degree']}°")
    lines.append(f"Lagna Nakshatra: {kundli['ascendant']['nakshatra']}")
    lines.append("\nPLANETARY POSITIONS:")
    
    for planet, data in kundli['planets'].items():
        retro = " (R)" if data['retrograde'] else ""
        lines.append(f"  {planet}: {data['rashi']} ({data['rashi_english']}) {data['degree']}° | House {data['house']} | {data['nakshatra']} Pada {data['pada']}{retro}")
    
    if kundli.get('current_dasha'):
        d = kundli['current_dasha']
        lines.append(f"\nCURRENT MAHADASHA: {d['lord']} (until {d['end']})")
    
    return "\n".join(lines)
