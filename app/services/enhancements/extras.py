"""Additional enhancement utilities — Nadi house context, D60, Timezone, Ayanamsa"""

from typing import Dict
from ..core.constants import RASHI_NAMES

D60_NAMES = [
    'Ghora','Rakshasa','Deva','Kubera','Yaksha','Kinnara','Bhrashta','Kulaghna',
    'Garala','Agni','Maya','Purishaka','Apampathi','Marut','Kaala','Sarpa',
    'Amrita','Indu','Mridu','Komala','Heramba','Brahma','Vishnu','Maheshwara',
    'Deva','Ardra','Kalinasha','Kshitipala','Kamalakara','Gulika','Mrithyu','Kaala',
    'Davagni','Ghora','Yama','Kantaka','Sudha','Amrita','Poornachandra','Vishadagdha',
    'Kulanasha','Vamshakshaya','Utpata','Kaala','Saumya','Komala','Sheetala','Karala',
    'Chandramukhi','Praveena','Kalapavaka','Dhannayoga','Kalamrita','Saumya','Komala',
    'Mandha','Rakta','Shubha','Atisheetala','Indumukhi',
]

POSITIVE_D60 = {'Deva','Kubera','Amrita','Indu','Mridu','Komala','Brahma','Vishnu',
                'Maheshwara','Sudha','Poornachandra','Saumya','Sheetala','Chandramukhi',
                'Praveena','Shubha','Dhannayoga'}

def get_d60_name(longitude: float) -> Dict:
    d60_index = int((longitude % 30) / 0.5) % 60
    name = D60_NAMES[d60_index] if d60_index < len(D60_NAMES) else 'Unknown'
    positive = name in POSITIVE_D60
    return {'name': name, 'index': d60_index, 'nature': 'Auspicious' if positive else 'Inauspicious'}

TIMEZONE_OFFSETS = {
    'IST': 5.5, 'EST': -5, 'CST': -6, 'MST': -7, 'PST': -8,
    'GMT': 0, 'BST': 1, 'CET': 1, 'JST': 9, 'AEST': 10,
    'NPT': 5.75, 'PKT': 5, 'BDT': 6, 'ICT': 7, 'SGT': 8,
}

AYANAMSAS = {
    'lahiri': {'name': 'Lahiri (Chitrapaksha)', 'usage': 'North India default'},
    'kp': {'name': 'KP (Krishnamurti)', 'usage': 'Required for KP system'},
    'raman': {'name': 'B.V. Raman', 'usage': 'South India schools'},
}
