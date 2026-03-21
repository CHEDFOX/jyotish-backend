"""
JYOTISH ENGINE - TIMING ENGINE
Calculates WHEN events happen using Double Transit Theory + Dasha activation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..core.constants import (
    PLANETS, RASHI_LORDS, RASHI_NAMES,
    KENDRA_HOUSES, TRIKONA_HOUSES, DUSTHANA_HOUSES,
)

EVENT_HOUSES = {
    'marriage':     {'primary': [7], 'secondary': [2, 11], 'karaka': 'Venus'},
    'career':       {'primary': [10], 'secondary': [6, 2, 11], 'karaka': 'Saturn'},
    'promotion':    {'primary': [10, 11], 'secondary': [9, 6], 'karaka': 'Sun'},
    'job_change':   {'primary': [10], 'secondary': [3, 6, 9], 'karaka': 'Saturn'},
    'business':     {'primary': [7, 10], 'secondary': [2, 11], 'karaka': 'Mercury'},
    'childbirth':   {'primary': [5], 'secondary': [2, 11], 'karaka': 'Jupiter'},
    'education':    {'primary': [4, 5], 'secondary': [9, 2], 'karaka': 'Jupiter'},
    'foreign':      {'primary': [9, 12], 'secondary': [3, 7], 'karaka': 'Rahu'},
    'property':     {'primary': [4], 'secondary': [2, 11], 'karaka': 'Mars'},
    'health_issue': {'primary': [6, 8], 'secondary': [1, 12], 'karaka': 'Saturn'},
    'wealth':       {'primary': [2, 11], 'secondary': [5, 9], 'karaka': 'Jupiter'},
    'vehicle':      {'primary': [4], 'secondary': [11], 'karaka': 'Venus'},
    'relationship': {'primary': [7, 5], 'secondary': [11, 3], 'karaka': 'Venus'},
    'spiritual':    {'primary': [9, 12], 'secondary': [5, 8], 'karaka': 'Ketu'},
    'litigation':   {'primary': [6], 'secondary': [8, 12], 'karaka': 'Mars'},
}


class TimingEngine:
    def __init__(self, engine):
        self.engine = engine
        self.planets = engine.planets
        self.asc_rashi = engine.ascendant_rashi
        self._dasha_data = None

    @property
    def dasha_data(self):
        if self._dasha_data is None:
            self._dasha_data = self.engine.get_vimshottari_dasha()
        return self._dasha_data

    def get_house_lord(self, house: int) -> str:
        rashi = (self.asc_rashi + house - 1) % 12
        return RASHI_LORDS[rashi]

    def get_planet_house(self, planet: str) -> int:
        return self.planets.get(planet, {}).get('house', 1)

    def _house_keyword(self, house: int) -> str:
        kw = {
            1: 'Self Body Health', 2: 'Wealth Family Speech',
            3: 'Siblings Courage Communication', 4: 'Mother Home Property',
            5: 'Children Intelligence Romance', 6: 'Enemies Disease Service',
            7: 'Marriage Partner Business', 8: 'Death Transformation Inheritance',
            9: 'Father Guru Fortune Travel', 10: 'Career Status Authority',
            11: 'Gains Income Friends', 12: 'Loss Foreign Liberation',
        }
        return kw.get(house, '')

    def planet_activates_house(self, planet: str, house: int) -> Dict:
        reasons = []
        score = 0
        lord = self.get_house_lord(house)
        if planet == lord:
            reasons.append(f'Lord of house {house}')
            score = None  # removed invented weight
        if self.get_planet_house(planet) == house:
            reasons.append(f'Placed in house {house}')
            score = None  # removed invented weight
        p_house = self.get_planet_house(planet)
        aspects = PLANETS.get(planet, {}).get('aspects', [7])
        for asp in aspects:
            target = ((p_house + asp - 1) % 12) + 1
            if target == house:
                reasons.append(f'Aspects house {house}')
                score = None  # removed invented weight
                break
        karakas = PLANETS.get(planet, {}).get('karaka', [])
        house_meaning = self._house_keyword(house)
        if any(k.lower() in house_meaning.lower() for k in karakas):
            reasons.append(f'Natural karaka for house {house}')
            score = None  # removed invented weight
        return {'activates': score > 0, 'score': score, 'reasons': reasons}

    def _transit_activates_house(self, planet: str, transit_planets: Dict, target_rashi: int) -> Dict:
        t_data = transit_planets.get(planet, {})
        t_rashi = t_data.get('rashi', 0)
        if t_rashi == target_rashi:
            return {'activates': True, 'method': 'transit', 'rashi': t_rashi}
        aspects = PLANETS.get(planet, {}).get('aspects', [7])
        for asp in aspects:
            aspected = (t_rashi + asp - 1) % 12
            if aspected == target_rashi:
                return {'activates': True, 'method': 'aspect', 'rashi': t_rashi}
        return {'activates': False, 'method': None, 'rashi': t_rashi}

    def check_double_transit(self, transit_planets: Dict, house: int) -> Dict:
        target_rashi = (self.asc_rashi + house - 1) % 12
        jup = self._transit_activates_house('Jupiter', transit_planets, target_rashi)
        sat = self._transit_activates_house('Saturn', transit_planets, target_rashi)
        double = jup['activates'] and sat['activates']
        return {
            'double_transit': double, 'house': house,
            'jupiter': jup, 'saturn': sat,
            'strength': 'Strong' if double else 'Partial' if (jup['activates'] or sat['activates']) else 'None',
        }

    def predict_event_timing(self, event: str, transit_planets: Dict = None, months_ahead: int = 24) -> Dict:
        if event not in EVENT_HOUSES:
            return {'error': f'Unknown event: {event}', 'valid_events': list(EVENT_HOUSES.keys())}
        config = EVENT_HOUSES[event]
        primary_houses = config['primary']
        secondary_houses = config['secondary']
        karaka = config['karaka']
        if transit_planets is None:
            transit_planets = self.engine.ephemeris.get_current_transits()

        dasha = self.dasha_data
        maha_lord = dasha['mahadasha']['lord']
        antar_lord = dasha['antardasha']['lord']

        maha_activation = max(self.planet_activates_house(maha_lord, h)['score'] for h in primary_houses)
        antar_activation = max(self.planet_activates_house(antar_lord, h)['score'] for h in primary_houses)
        dasha_score = maha_activation + antar_activation
        dasha_promise = dasha_score >= 3

        dt_results = [self.check_double_transit(transit_planets, h) for h in primary_houses]
        any_double = any(d['double_transit'] for d in dt_results)
        any_partial = any(d['strength'] == 'Partial' for d in dt_results)

        karaka_house = self.get_planet_house(karaka)
        karaka_strong = karaka_house in KENDRA_HOUSES + TRIKONA_HOUSES and karaka_house not in DUSTHANA_HOUSES

        probability = None  # removed — use classical_rules
        factors = []

        # Pre-compute karaka data (used in both promise and negative checks)
        karaka_data = self.planets.get(karaka, {})
        karaka_rashi = karaka_data.get('rashi', 0)
        karaka_retro = karaka_data.get('retrograde', False)
        karaka_planet_info = PLANETS.get(karaka, {})

        # ═══ INHERENT CHART PROMISE (separate from timing) ═══
        # Does the chart fundamentally support this event?
        promise_score = 0.0

        # Check primary house lord strength
        for h in primary_houses:
            lord = self.get_house_lord(h)
            lord_h = self.get_planet_house(lord)
            lord_data = self.planets.get(lord, {})
            lord_rashi = lord_data.get('rashi', 0)
            lord_info = PLANETS.get(lord, {})

            # Lord in kendra (1,4,7,10) or trikona (1,5,9) = strong promise
            if lord_h in [1, 4, 5, 7, 9, 10]:
                promise_score = None  # removed invented weight.15
                factors.append(f'House {h} lord {lord} well-placed in house {lord_h} — inherent promise')
            # Lord in own sign or exalted
            if lord_rashi == lord_info.get('exalted') or lord_rashi in lord_info.get('owns', []):
                promise_score = None  # removed invented weight.10
                factors.append(f'House {h} lord {lord} in strong dignity')

        # Check if primary house is clean (no malefics)
        for h in primary_houses:
            occupants = [p for p in self.planets if self.get_planet_house(p) == h]
            malefics = [p for p in occupants if p in ('Saturn', 'Rahu', 'Ketu', 'Mars')]
            benefics = [p for p in occupants if p in ('Jupiter', 'Venus', 'Mercury')]
            if not malefics and (not occupants or benefics):
                promise_score = None  # removed invented weight.05
            if benefics and not malefics:
                promise_score = None  # removed invented weight.05
                factors.append(f'House {h} has benefic influence')

        # Karaka in good dignity adds promise
        if karaka_rashi == karaka_planet_info.get('exalted') or karaka_rashi in karaka_planet_info.get('owns', []):
            promise_score = None  # removed invented weight.10
            factors.append(f'{karaka} in strong dignity — event is promised')

        promise_score = min(promise_score, 0.30)
        probability += promise_score

        # ═══ TIMING FACTORS (is it happening now?) ═══
        if dasha_promise:
            probability += 0.35
            factors.append(f'Dasha activates: {maha_lord}/{antar_lord} (score: {dasha_score})')
        else:
            factors.append(f'Dasha weak for {event}: {maha_lord}/{antar_lord} (score: {dasha_score})')

        if any_double:
            probability += 0.30
            factors.append('Double transit active on primary house')
        elif any_partial:
            probability += 0.15
            factors.append('Partial transit (Jupiter or Saturn, not both)')

        if karaka_strong:
            probability += 0.15
            factors.append(f'Karaka {karaka} well-placed in house {karaka_house}')
        else:
            factors.append(f'Karaka {karaka} in house {karaka_house} (not ideal)')

        sec_score = sum(1 for h in secondary_houses if self.check_double_transit(transit_planets, h)['double_transit'])
        if sec_score > 0:
            probability += 0.10 * min(sec_score, 2)
            factors.append(f'{sec_score} secondary house(s) also activated')

        yogas = self.engine.get_yogas()
        relevant_yogas = self._find_relevant_yogas(event, yogas)
        if relevant_yogas:
            probability += 0.10
            factors.append(f'Supporting yogas: {", ".join(relevant_yogas[:3])}')

        # ═══════════════════════════════════════════════════════════
        # NEGATIVE FACTORS (reduce probability for afflictions)
        # ═══════════════════════════════════════════════════════════

        # 1. AGE CONTEXT — some events become unlikely with age
        try:
            birth_year = self.engine.birth_local.year
            current_age = datetime.now().year - birth_year

            if event == 'marriage':
                if current_age > 60: probability *= 0.2; factors.append(f'Age {current_age}: marriage very unlikely at this stage')
                elif current_age > 45: probability *= 0.5; factors.append(f'Age {current_age}: late marriage factor')
            elif event == 'childbirth':
                if current_age > 50: probability *= 0.1; factors.append(f'Age {current_age}: childbirth extremely unlikely')
                elif current_age > 40: probability *= 0.4; factors.append(f'Age {current_age}: late childbirth factor')
            elif event == 'education':
                if current_age > 45: probability *= 0.3; factors.append(f'Age {current_age}: formal education unlikely')
        except Exception:
            pass

        # 2. KARAKA AFFLICTION — retrograde/combust/debilitated karaka weakens event

        # Retrograde karaka in its own signification house = DENIAL/heavy delay
        # NOTE: Rahu and Ketu are ALWAYS retrograde — don't penalize them
        if karaka_retro and karaka not in ('Rahu', 'Ketu'):
            if karaka_house in primary_houses:
                # In primary house AND retrograde = strong denial (e.g., Jupiter retro in 5th = no children for Modi)
                probability *= 0.3
                factors.append(f'{karaka} RETROGRADE in primary house {karaka_house} — strong denial/heavy delay')
            else:
                # Retrograde but NOT in primary house = just delays, not denial
                # Softer penalty — many people have retrograde Jupiter and still have children
                probability *= 0.85
                factors.append(f'{karaka} retrograde — some delays in {event}')

        # Debilitated karaka
        if karaka_rashi == karaka_planet_info.get('debilitated'):
            probability *= 0.5
            factors.append(f'{karaka} debilitated — weak signification for {event}')

        # Karaka conjunct Saturn = delay/denial
        sat_house = self.get_planet_house('Saturn')
        if sat_house == karaka_house and karaka != 'Saturn':
            probability *= 0.6
            factors.append(f'{karaka} conjunct Saturn — delays/restrictions for {event}')

        # Karaka conjunct Ketu = detachment from the signification
        ketu_house = self.get_planet_house('Ketu')
        if ketu_house == karaka_house and karaka != 'Ketu':
            probability *= 0.5
            factors.append(f'{karaka} conjunct Ketu — detachment from {event} matters')

        # 3. PRIMARY HOUSE AFFLICTION — malefics in primary house reduce probability
        for h in primary_houses:
            occupants = [p for p in self.planets if self.get_planet_house(p) == h]
            malefics_in_house = [p for p in occupants if p in ('Saturn', 'Rahu', 'Ketu', 'Mars')]
            if len(malefics_in_house) >= 2:
                probability *= 0.5
                factors.append(f'House {h} heavily afflicted by {", ".join(malefics_in_house)}')
            elif 'Ketu' in malefics_in_house and event not in ('spiritual', 'foreign'):
                probability *= 0.7
                factors.append(f'Ketu in house {h} — detachment from {event}')

        # 4. PRIMARY HOUSE LORD IN DUSTHANA — lord in 6/8/12 weakens house
        # EXCEPTION: For spiritual/foreign events, lord in 12th is POSITIVE
        for h in primary_houses:
            lord = self.get_house_lord(h)
            lord_h = self.get_planet_house(lord)
            if lord_h in DUSTHANA_HOUSES:
                # Lord in 12th is GOOD for spiritual and foreign events
                if lord_h == 12 and event in ('spiritual', 'foreign'):
                    probability += 0.05
                    factors.append(f'House {h} lord {lord} in 12th — supports {event} journey')
                # Lord in own house (e.g., 12th lord in 12th) is neutral, not bad
                elif lord_h == h:
                    factors.append(f'House {h} lord {lord} in own house — neutral')
                # Lord in 8th for spiritual = transformation = positive
                elif lord_h == 8 and event == 'spiritual':
                    factors.append(f'House {h} lord {lord} in 8th — deep transformation')
                else:
                    probability *= 0.6
                    factors.append(f'House {h} lord {lord} in dusthana house {lord_h}')

        # 5. SPIRITUAL BOOST — 12th house stellium or Ketu in 12th
        if event == 'spiritual':
            h12_occupants = [p for p in self.planets if self.get_planet_house(p) == 12]
            has_ketu_12 = 'Ketu' in h12_occupants
            has_spiritual_stellium = len(h12_occupants) >= 3

            if has_spiritual_stellium and has_ketu_12:
                probability += 0.40
                factors.append(f'Stellium in 12th WITH Ketu ({", ".join(h12_occupants)}) — powerful spiritual destiny')
            elif has_spiritual_stellium:
                probability += 0.25
                factors.append(f'Stellium in 12th house ({", ".join(h12_occupants)}) — spiritual energy')
            elif has_ketu_12:
                probability += 0.20
                factors.append('Ketu in 12th — moksha karaka in moksha house')
            elif len(h12_occupants) >= 2:
                # 2 planets in 12th without Ketu — very mild spiritual tint
                # Many people have Sun+Mercury in 12th (they're often together) — doesn't make them spiritual seekers
                has_sun_merc_only = set(h12_occupants) <= {'Sun', 'Mercury'}
                if has_sun_merc_only:
                    probability += 0.05
                    factors.append(f'{", ".join(h12_occupants)} in 12th — slight introspective tendency')
                else:
                    probability += 0.10
                    factors.append(f'{", ".join(h12_occupants)} in 12th — mild spiritual inclination')
            # Jupiter retrograde = past-life spiritual wisdom
            jup_retro = self.planets.get('Jupiter', {}).get('retrograde', False)
            if jup_retro:
                probability += 0.10
                factors.append('Jupiter retrograde — past-life spiritual knowledge')

        # 6. MARRIAGE DENIAL PATTERNS
        if event == 'marriage':
            venus_house = self.get_planet_house('Venus')
            # Venus + Saturn conjunction = delayed/denied marriage
            if venus_house == sat_house:
                probability *= 0.4
                factors.append('Venus conjunct Saturn — marriage heavily delayed or denied')
            # Venus + Ketu = detachment from relationships
            if venus_house == ketu_house:
                probability *= 0.5
                factors.append('Venus conjunct Ketu — detachment from romantic love')
            # 7th lord in 12th = spouse from far or loss of marriage
            lord7 = self.get_house_lord(7)
            lord7_h = self.get_planet_house(lord7)
            if lord7_h == 12:
                probability *= 0.6
                factors.append(f'7th lord {lord7} in 12th — marriage may not materialize conventionally')

        # 7. CHILDREN DENIAL PATTERNS
        if event == 'childbirth':
            jup_house = self.get_planet_house('Jupiter')
            jup_retro = self.planets.get('Jupiter', {}).get('retrograde', False)
            # Jupiter retrograde in 5th = strong denial of children
            if jup_retro and jup_house == 5:
                probability *= 0.2
                factors.append('Jupiter RETROGRADE in 5th house — strong denial of children')
            # 5th lord Saturn = delay in children
            lord5 = self.get_house_lord(5)
            if lord5 == 'Saturn':
                probability *= 0.6
                factors.append('Saturn rules 5th house — significant delays in children')
            # 5th lord in dusthana
            lord5_h = self.get_planet_house(lord5)
            if lord5_h in [6, 8, 12]:
                probability *= 0.5
                factors.append(f'5th lord {lord5} in dusthana house {lord5_h}')

        # 8. CAREER STRENGTH BOOST
        if event in ('career', 'promotion'):
            sun_house = self.get_planet_house('Sun')
            lord10 = self.get_house_lord(10)
            lord10_h = self.get_planet_house(lord10)

            # 10th lord in kendra (1,4,7,10) = strong career
            if lord10_h in KENDRA_HOUSES:
                probability += 0.10
                factors.append(f'10th lord {lord10} in kendra house {lord10_h} — strong career foundation')
            # 10th lord in trikona (1,5,9) = fortunate career
            elif lord10_h in TRIKONA_HOUSES:
                probability += 0.08
                factors.append(f'10th lord {lord10} in trikona house {lord10_h} — fortunate career')
            # 10th lord in 2nd = public speech, wealth through career
            elif lord10_h == 2:
                probability += 0.08
                factors.append(f'10th lord {lord10} in 2nd — career through speech/public influence')

            # Sun in strong house = authority
            if sun_house in [1, 10, 9, 11]:
                probability += 0.05
                factors.append(f'Sun in house {sun_house} — leadership and authority')

            # Mars conjunct 10th lord = aggressive career success
            mars_h = self.get_planet_house('Mars')
            if mars_h == lord10_h:
                probability += 0.08
                factors.append(f'Mars with 10th lord — driven, powerful career energy')

            # Multiple planets supporting 10th house = very strong career
            planets_supporting_10 = []
            for p in self.planets:
                activation = self.planet_activates_house(p, 10)
                if activation['score'] >= 2:
                    planets_supporting_10.append(p)
            if len(planets_supporting_10) >= 3:
                probability += 0.10
                factors.append(f'{len(planets_supporting_10)} planets support career house — very strong career')

        probability = max(0.05, min(probability, 0.95))
        confidence = 'High' if probability >= 0.65 else 'Moderate' if probability >= 0.40 else 'Low'
        window = self._estimate_window(probability, dasha_promise, any_double, months_ahead)

        return {
            'event': event, 'probability': round(probability, 2),
            'confidence': confidence, 'window': window,
            'current_dasha': f"{maha_lord}/{antar_lord}",
            'dasha_promise': dasha_promise, 'double_transit': any_double,
            'karaka_strong': karaka_strong, 'factors': factors,
            'primary_houses': primary_houses, 'relevant_yogas': relevant_yogas,
        }

    def _find_relevant_yogas(self, event: str, yogas_data: Dict) -> List[str]:
        m = {
            'marriage': ['raja', 'dhana', 'chandra'], 'career': ['raja', 'mahapurusha', 'dhana'],
            'promotion': ['raja', 'surya'], 'wealth': ['dhana', 'raja'],
            'childbirth': ['chandra', 'deity'], 'education': ['surya', 'deity'],
            'spiritual': ['sanyasa', 'deity'], 'health_issue': ['arishta', 'dosha'],
        }
        cats = m.get(event, ['raja', 'dhana'])
        result = []
        for cat in cats:
            for y in yogas_data.get('yogas', {}).get(cat, []):
                if not y.get('is_negative', False):
                    result.append(y['name'])
        return result[:5]

    def _estimate_window(self, prob: float, dasha_ok: bool, double_transit: bool, months: int) -> Dict:
        now = datetime.now()
        if prob >= 0.65 and dasha_ok and double_transit:
            return {
                'start': now.strftime('%Y-%m-%d'),
                'end': (now + timedelta(days=180)).strftime('%Y-%m-%d'),
                'description': 'Within next 6 months — conditions converging now',
            }
        elif prob >= 0.40 and dasha_ok:
            return {
                'start': now.strftime('%Y-%m-%d'),
                'end': (now + timedelta(days=365)).strftime('%Y-%m-%d'),
                'description': 'Within next 12 months — dasha supports, waiting for transit trigger',
            }
        elif prob >= 0.25:
            return {
                'start': (now + timedelta(days=180)).strftime('%Y-%m-%d'),
                'end': (now + timedelta(days=months * 30)).strftime('%Y-%m-%d'),
                'description': f'Within {months} months — partial support, needs stronger activation',
            }
        else:
            return {
                'start': None, 'end': None,
                'description': 'Not strongly indicated in current period',
            }

    def scan_all_events(self, transit_planets: Dict = None) -> Dict:
        if transit_planets is None:
            transit_planets = self.engine.ephemeris.get_current_transits()
        results = {}
        for event in EVENT_HOUSES:
            results[event] = self.predict_event_timing(event, transit_planets)
        ranked = sorted(results.items(), key=lambda x: x[1]['probability'], reverse=True)
        return {
            'predictions': results,
            'top_3': [
                {'event': e, 'probability': r['probability'], 'confidence': r['confidence'],
                 'window': r['window']['description']}
                for e, r in ranked[:3]
            ],
            'current_dasha': self.dasha_data.get('dasha_string', ''),
            'scan_date': datetime.now().strftime('%Y-%m-%d'),
        }

    def get_period_analysis(self, months: int = 3, transit_planets: Dict = None) -> Dict:
        if transit_planets is None:
            transit_planets = self.engine.ephemeris.get_current_transits()
        dasha = self.dasha_data
        maha_lord = dasha['mahadasha']['lord']
        antar_lord = dasha['antardasha']['lord']

        activated_houses = []
        for h in range(1, 13):
            ms = self.planet_activates_house(maha_lord, h)['score']
            ans = self.planet_activates_house(antar_lord, h)['score']
            total = ms + ans
            if total >= 2:
                activated_houses.append({'house': h, 'score': total, 'meaning': self._house_keyword(h)})
        activated_houses.sort(key=lambda x: x['score'], reverse=True)

        dt_houses = [h for h in range(1, 13) if self.check_double_transit(transit_planets, h)['double_transit']]
        convergence = [ah for ah in activated_houses if ah['house'] in dt_houses]

        themes = []
        for ah in activated_houses[:3]:
            h = ah['house']
            themes.append({
                'house': h, 'meaning': ah['meaning'],
                'strength': 'Very Active' if h in dt_houses else 'Active',
                'dasha_score': ah['score'], 'transit_support': h in dt_houses,
            })

        summary = f'{maha_lord}/{antar_lord} dasha'
        active = [t for t in themes if t['strength'] == 'Very Active']
        if active:
            areas = ', '.join(t['meaning'] for t in active)
            summary += f' with strong activation in: {areas}. Events likely.'
        elif themes:
            areas = ', '.join(t['meaning'] for t in themes[:2])
            summary += f' focusing on: {areas}. Moderate activity.'
        else:
            summary += ' — general period, no strong activation.'

        return {
            'period': f'Next {months} months', 'dasha': f'{maha_lord}/{antar_lord}',
            'dominant_themes': themes, 'convergence_houses': [c['house'] for c in convergence],
            'double_transit_houses': dt_houses, 'summary': summary,
        }


def create_timing_engine(engine) -> TimingEngine:
    return TimingEngine(engine)
