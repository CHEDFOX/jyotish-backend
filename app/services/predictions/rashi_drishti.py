"""
BPHS CH.8 — RASHI DRISHTI (Sign Aspects)

Different from Graha Drishti (planet aspects).
Movable signs aspect Fixed signs (except adjacent)
Fixed signs aspect Movable signs (except adjacent)
Dual signs aspect other Dual signs

A planet in a sign gives the same drishti as the sign.
"""

from typing import List, Tuple


def get_rashi_drishti(rashi_index: int) -> List[int]:
    """
    BPHS Ch.8: Get rashis aspected by this rashi.
    
    Movable (0,3,6,9): aspects all Fixed except adjacent Fixed
    Fixed (1,4,7,10): aspects all Movable except adjacent Movable
    Dual (2,5,8,11): aspects all other Dual signs
    """
    modality = rashi_index % 3
    
    if modality == 0:  # Movable
        # All Fixed signs: 1,4,7,10
        fixed = [1, 4, 7, 10]
        # Remove adjacent Fixed (next sign)
        adjacent_fixed = (rashi_index + 1) % 12
        return [f for f in fixed if f != adjacent_fixed]
    
    elif modality == 1:  # Fixed
        # All Movable signs: 0,3,6,9
        movable = [0, 3, 6, 9]
        # Remove adjacent Movable (previous sign)
        adjacent_movable = (rashi_index - 1) % 12
        return [m for m in movable if m != adjacent_movable]
    
    else:  # Dual
        # All other Dual signs: 2,5,8,11 minus self
        dual = [2, 5, 8, 11]
        return [d for d in dual if d != rashi_index]


def check_rashi_aspect(from_rashi: int, to_rashi: int) -> bool:
    """Check if from_rashi aspects to_rashi via Rashi Drishti."""
    return to_rashi in get_rashi_drishti(from_rashi)


def get_rashi_aspects_on_house(engine, house: int) -> List[str]:
    """Get all planets that aspect a house via Rashi Drishti."""
    asc = engine.ascendant_rashi
    target_sign = (asc + house - 1) % 12
    
    aspecting_planets = []
    for planet in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']:
        planet_rashi = engine.planets.get(planet, {}).get('rashi', 0)
        if check_rashi_aspect(planet_rashi, target_sign):
            aspecting_planets.append(planet)
    
    return aspecting_planets
