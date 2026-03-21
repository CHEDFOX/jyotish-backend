"""
BPHS CH.75 — VEDHA (Transit Obstruction)

When a planet transits a beneficial house, its good effects can be
BLOCKED (vedha) by another planet transiting a specific obstructing house.

Vedha pairs from BPHS:
Sun: 1↔8, 2↔5, 3↔9, 4↔10, 6↔12, 7↔11
Moon: 1↔5, 3↔9, 6↔12, 7↔2, 10↔4, 11↔8
Mars: same as Sun
Mercury: same as Moon
Jupiter: 2↔12, 5↔4, 7↔3, 9↔10, 11↔8
Venus: same as Mercury
Saturn: 1↔8, 2↔5, 3↔11, 4↔10, 6↔9, 7↔12
"""

from typing import Dict, List


# Vedha pairs: {transit_house: obstructing_house}
VEDHA_PAIRS = {
    'Sun':     {1:8, 2:5, 3:9, 4:10, 5:2, 6:12, 7:11, 8:1, 9:3, 10:4, 11:7, 12:6},
    'Moon':    {1:5, 2:7, 3:9, 4:10, 5:1, 6:12, 7:2, 8:11, 9:3, 10:4, 11:8, 12:6},
    'Mars':    {1:8, 2:5, 3:9, 4:10, 5:2, 6:12, 7:11, 8:1, 9:3, 10:4, 11:7, 12:6},
    'Mercury': {1:5, 2:7, 3:9, 4:10, 5:1, 6:12, 7:2, 8:11, 9:3, 10:4, 11:8, 12:6},
    'Jupiter': {1:8, 2:12, 3:7, 4:5, 5:4, 7:3, 8:1, 9:10, 10:9, 11:8, 12:2},
    'Venus':   {1:5, 2:7, 3:9, 4:10, 5:1, 6:12, 7:2, 8:11, 9:3, 10:4, 11:8, 12:6},
    'Saturn':  {1:8, 2:5, 3:11, 4:10, 5:2, 6:9, 7:12, 8:1, 9:6, 10:4, 11:3, 12:7},
}


def check_vedha(transit_planet: str, transit_house: int, all_transit_houses: Dict) -> Dict:
    """
    Check if a planet's transit is obstructed by vedha.
    
    Args:
        transit_planet: Planet transiting
        transit_house: House being transited (from natal Moon)
        all_transit_houses: Dict of {planet: house_from_moon} for all transiting planets
    
    Returns:
        Dict with vedha status
    """
    pairs = VEDHA_PAIRS.get(transit_planet, {})
    obstruct_house = pairs.get(transit_house)
    
    if obstruct_house is None:
        return {'has_vedha': False, 'planet': transit_planet, 'transit_house': transit_house}
    
    # Check if ANY planet is in the obstructing house
    obstructing_planets = [p for p, h in all_transit_houses.items() 
                          if h == obstruct_house and p != transit_planet]
    
    if obstructing_planets:
        return {
            'has_vedha': True,
            'planet': transit_planet,
            'transit_house': transit_house,
            'obstruct_house': obstruct_house,
            'obstructing_planets': obstructing_planets,
            'text': f'{transit_planet} transit in H{transit_house} BLOCKED by {obstructing_planets} in H{obstruct_house} (Vedha)',
            'source': 'BPHS Ch.75',
        }
    
    return {'has_vedha': False, 'planet': transit_planet, 'transit_house': transit_house}


def check_all_vedhas(engine) -> List[Dict]:
    """Check vedha for all current transits."""
    try:
        transits = engine.get_current_transits()
    except Exception:
        return []
    
    moon_rashi = engine.planets.get('Moon', {}).get('rashi', 0)
    
    # Get transit houses from Moon
    transit_houses = {}
    if isinstance(transits, dict):
        for planet, data in transits.items():
            if isinstance(data, dict) and 'rashi' in data:
                t_rashi = data['rashi']
                house_from_moon = (t_rashi - moon_rashi) % 12 + 1
                transit_houses[planet] = house_from_moon
    
    vedhas = []
    for planet, house in transit_houses.items():
        if planet in VEDHA_PAIRS:
            result = check_vedha(planet, house, transit_houses)
            if result.get('has_vedha'):
                vedhas.append(result)
    
    return vedhas
