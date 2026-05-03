"""
ZI WEI DOU SHU (紫微斗数) — Purple Star Astrology
The second pillar of Chinese astrology alongside BaZi.

14 Major Stars placed in 12 Palaces based on birth data.
4 Transformations (Hua) applied annually.
"""
from datetime import datetime
from typing import Dict, List

# ═══════════════════════════════════════════════════════════════
# 12 PALACES
# ═══════════════════════════════════════════════════════════════
PALACES = [
    "Life (命宫)", "Siblings (兄弟)", "Spouse (夫妻)", "Children (子女)",
    "Wealth (财帛)", "Health (疾厄)", "Travel (迁移)", "Friends (交友)",
    "Career (官禄)", "Property (田宅)", "Fortune (福德)", "Parents (父母)",
]

# ═══════════════════════════════════════════════════════════════
# 14 MAJOR STARS
# ═══════════════════════════════════════════════════════════════
MAJOR_STARS = {
    'Zi Wei':   {'chinese': '紫微', 'nature': 'Emperor', 'element': 'Earth', 'type': 'leader',
                 'meaning': 'Authority, dignity, leadership, decision-making power'},
    'Tian Ji':  {'chinese': '天机', 'nature': 'Strategist', 'element': 'Wood', 'type': 'advisor',
                 'meaning': 'Intelligence, planning, quick-thinking, nervous energy'},
    'Tai Yang': {'chinese': '太阳', 'nature': 'Sun', 'element': 'Fire', 'type': 'giver',
                 'meaning': 'Generosity, public service, fame, sacrifice for others'},
    'Wu Qu':    {'chinese': '武曲', 'nature': 'Warrior', 'element': 'Metal', 'type': 'wealth',
                 'meaning': 'Financial ability, determination, loneliness, action'},
    'Tian Tong':{'chinese': '天同', 'nature': 'Blessing', 'element': 'Water', 'type': 'comfort',
                 'meaning': 'Comfort, leisure, emotional sensitivity, late bloomer'},
    'Lian Zhen':{'chinese': '廉贞', 'nature': 'Judge', 'element': 'Fire', 'type': 'penal',
                 'meaning': 'Justice, politics, complications in love, sharp mind'},
    'Tai Yin':  {'chinese': '太阴', 'nature': 'Moon', 'element': 'Water', 'type': 'wealth',
                 'meaning': 'Real estate, savings, patience, beauty, mother figure'},
    'Tan Lang': {'chinese': '贪狼', 'nature': 'Greedy Wolf', 'element': 'Wood', 'type': 'desire',
                 'meaning': 'Ambition, desire, talent, transformation, romance'},
    'Ju Men':   {'chinese': '巨门', 'nature': 'Giant Gate', 'element': 'Water', 'type': 'speech',
                 'meaning': 'Debate, argument, analysis, suspicion, verbal talent'},
    'Tian Xiang':{'chinese': '天相', 'nature': 'Minister', 'element': 'Water', 'type': 'service',
                  'meaning': 'Service, diplomacy, reliability, support role'},
    'Tian Liang':{'chinese': '天梁', 'nature': 'Pillar', 'element': 'Earth', 'type': 'elder',
                  'meaning': 'Wisdom, protection, tradition, authority figure'},
    'Qi Sha':   {'chinese': '七杀', 'nature': '7 Killings', 'element': 'Metal', 'type': 'warrior',
                 'meaning': 'Power, reform, risk, military, extreme action'},
    'Po Jun':   {'chinese': '破军', 'nature': 'Destroyer', 'element': 'Water', 'type': 'pioneer',
                 'meaning': 'Destruction for creation, pioneer, wasteful but innovative'},
    'Tian Fu':  {'chinese': '天府', 'nature': 'Treasury', 'element': 'Earth', 'type': 'wealth',
                 'meaning': 'Stability, storage, conservative wealth, reliability'},
}

# ═══════════════════════════════════════════════════════════════
# 4 TRANSFORMATIONS (四化)
# ═══════════════════════════════════════════════════════════════
# Keyed by year stem index (0-9), values are [Hua Lu, Hua Quan, Hua Ke, Hua Ji]
FOUR_TRANSFORMATIONS = {
    0: ['Lian Zhen', 'Po Jun', 'Wu Qu', 'Tai Yang'],     # Jia
    1: ['Tian Ji', 'Tian Liang', 'Zi Wei', 'Tai Yin'],   # Yi
    2: ['Tian Tong', 'Tian Ji', 'Wen Chang', 'Lian Zhen'], # Bing
    3: ['Tai Yin', 'Tian Tong', 'Tian Ji', 'Ju Men'],    # Ding
    4: ['Tan Lang', 'Tai Yin', 'You Bi', 'Tian Ji'],     # Wu
    5: ['Wu Qu', 'Tan Lang', 'Tian Liang', 'Wen Qu'],    # Ji
    6: ['Tai Yang', 'Wu Qu', 'Tai Yin', 'Tian Tong'],    # Geng
    7: ['Ju Men', 'Tai Yang', 'Wen Qu', 'Wen Chang'],    # Xin
    8: ['Tian Liang', 'Zi Wei', 'Zuo Fu', 'Wu Qu'],      # Ren
    9: ['Po Jun', 'Ju Men', 'Tai Yin', 'Tan Lang'],      # Gui
}

# ═══════════════════════════════════════════════════════════════
# STAR PLACEMENT ALGORITHM
# ═══════════════════════════════════════════════════════════════
# Zi Wei position based on Day Stem and Lunar Day
# Simplified: use a lookup based on stem group and day number
ZI_WEI_PALACE = {}  # Will be computed

def _calculate_life_palace(month: int, hour_branch: int) -> int:
    """Calculate the Life Palace (Ming Gong) position."""
    # Formula: Life Palace = (month + hour_branch) adjusted to 12 palaces
    # Traditional: count from Yin (Tiger) month, reverse from hour
    base = (2 + month - 1) % 12  # Month 1 = Yin position
    life = (base - hour_branch + 14) % 12  # Reverse count from hour
    return life

def _place_zi_wei(lunar_day: int, day_stem: int) -> int:
    """Place Zi Wei (Emperor star) based on lunar day and day stem."""
    # Simplified algorithm: lunar day determines initial palace
    # Day stem group (Wood/Fire/Earth/Metal/Water) adjusts
    stem_group = day_stem // 2  # 0=Wood, 1=Fire, 2=Earth, 3=Metal, 4=Water
    base = (lunar_day - 1 + stem_group * 2) % 12
    return base

def _place_stars_from_zi_wei(zi_wei_palace: int) -> Dict:
    """Place all 14 major stars relative to Zi Wei's position."""
    # Stars are placed at fixed distances from Zi Wei
    # These are the classical distances
    placements = {
        'Zi Wei': zi_wei_palace,
        'Tian Ji': (zi_wei_palace - 1) % 12,
        'Tai Yang': (zi_wei_palace - 3) % 12,
        'Wu Qu': (zi_wei_palace - 4) % 12,
        'Tian Tong': (zi_wei_palace - 5) % 12,
        'Lian Zhen': (zi_wei_palace - 8) % 12,
        # Tian Fu group (opposite direction)
        'Tian Fu': (zi_wei_palace + 4) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 4) % 12,
        'Tai Yin': (zi_wei_palace + 5) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 5) % 12,
        'Tan Lang': (zi_wei_palace + 1) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 1) % 12,
        'Ju Men': (zi_wei_palace + 2) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 2) % 12,
        'Tian Xiang': (zi_wei_palace + 3) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 3) % 12,
        'Tian Liang': (zi_wei_palace + 6) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 6) % 12,
        'Qi Sha': (zi_wei_palace + 7) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 7) % 12,
        'Po Jun': (zi_wei_palace + 8) % 12 if zi_wei_palace <= 6 else (12 - zi_wei_palace + 8) % 12,
    }
    return placements


class ZiWeiChart:
    """Zi Wei Dou Shu chart calculator."""
    
    def __init__(self, birth_dt: datetime, gender: str = "male"):
        self.birth_dt = birth_dt
        self.gender = gender
        self._palaces = None
        self._stars = None
    
    def _ensure_calculated(self):
        if self._palaces is not None:
            return
        self._calculate()
    
    def _calculate(self):
        year = self.birth_dt.year
        month = self.birth_dt.month  # Approximate lunar month
        day = self.birth_dt.day
        hour_branch = ((self.birth_dt.hour + 1) // 2) % 12
        
        year_stem = (year - 4) % 10
        
        # Life Palace
        life_palace = _calculate_life_palace(month, hour_branch)
        
        # Place Zi Wei
        zi_wei_pos = _place_zi_wei(day, year_stem)
        
        # Place all 14 stars
        star_positions = _place_stars_from_zi_wei(zi_wei_pos)
        
        # Build palace contents
        self._palaces = {}
        for i in range(12):
            palace_idx = (life_palace + i) % 12
            palace_name = PALACES[i]
            stars_here = [star for star, pos in star_positions.items() if pos == palace_idx]
            
            self._palaces[palace_name] = {
                'position': palace_idx,
                'stars': stars_here,
                'star_details': [MAJOR_STARS[s] for s in stars_here if s in MAJOR_STARS],
            }
        
        self._stars = star_positions
        
        # Apply 4 Transformations
        transforms = FOUR_TRANSFORMATIONS.get(year_stem, [])
        self._transformations = {}
        transform_names = ['Hua Lu (化禄)', 'Hua Quan (化权)', 'Hua Ke (化科)', 'Hua Ji (化忌)']
        transform_meanings = ['Wealth/Prosperity', 'Authority/Power', 'Fame/Recognition', 'Trouble/Obstruction']
        
        for i, star_name in enumerate(transforms):
            if i < len(transform_names):
                self._transformations[transform_names[i]] = {
                    'star': star_name,
                    'meaning': transform_meanings[i],
                    'palace': self._find_star_palace(star_name),
                }
    
    def _find_star_palace(self, star_name: str) -> str:
        if not self._stars:
            return ''
        pos = self._stars.get(star_name, -1)
        if pos >= 0:
            for palace_name, data in self._palaces.items():
                if data.get('position') == pos:
                    return palace_name
        return 'Unknown'
    
    def get_life_palace(self) -> Dict:
        """Get the Life Palace (most important)."""
        self._ensure_calculated()
        return self._palaces.get("Life (命宫)", {})
    
    def get_all_palaces(self) -> Dict:
        """Get all 12 palaces with their stars."""
        self._ensure_calculated()
        return self._palaces
    
    def get_transformations(self) -> Dict:
        """Get the 4 transformations for the birth year."""
        self._ensure_calculated()
        return self._transformations
    
    def generate_report(self) -> Dict:
        """Full Zi Wei Dou Shu report."""
        self._ensure_calculated()
        
        life = self.get_life_palace()
        career = self._palaces.get("Career (官禄)", {})
        wealth = self._palaces.get("Wealth (财帛)", {})
        spouse = self._palaces.get("Spouse (夫妻)", {})
        
        return {
            'system': 'Zi Wei Dou Shu (Purple Star Astrology)',
            'life_palace': life,
            'career_palace': career,
            'wealth_palace': wealth,
            'spouse_palace': spouse,
            'all_palaces': self._palaces,
            'transformations': self._transformations,
            'star_positions': self._stars,
        }
