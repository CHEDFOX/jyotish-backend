"""
JYOTISH ORACLE — SYNTHESIS ENGINE
Intelligence layer between calculation and LLM.
Finds cross-system convergences, writes human observations.
DeepSeek polishes tone only — it no longer invents meaning.
"""

from datetime import datetime
from typing import Dict, List, Optional


# ── YOGINI DASHA INTERPRETATION ───────────────────────────────────────────────
YOGINI_THEMES = {
    'Mangala':  {'planet':'Moon',    'nature':'Auspicious',   'duration':'1 year',  'themes':'Emotional fulfilment, mother\'s blessing, public recognition, new beginnings', 'warning':None},
    'Pingala':  {'planet':'Sun',     'nature':'Mixed',        'duration':'2 years', 'themes':'Authority comes forward but ego conflicts and government dealings require care', 'warning':'Father or authority figures may cause tension'},
    'Dhanya':   {'planet':'Jupiter', 'nature':'Auspicious',   'duration':'3 years', 'themes':'Wealth, wisdom, spiritual growth, children, teachers, expansion in all areas', 'warning':None},
    'Bhramari': {'planet':'Mars',    'nature':'Inauspicious', 'duration':'4 years', 'themes':'Physical energy high but conflicts, accidents, and disputes arise. Surgery possible.', 'warning':'Avoid aggression — channel Mars energy into discipline'},
    'Bhadrika': {'planet':'Mercury', 'nature':'Auspicious',   'duration':'5 years', 'themes':'Communication, education, business, skill development, writing, siblings prosper', 'warning':None},
    'Ulka':     {'planet':'Saturn',  'nature':'Inauspicious', 'duration':'6 years', 'themes':'Hard work, delays, obstacles, service, discipline — refinement through difficulty', 'warning':'Health and vitality need attention. Saturn demands patience.'},
    'Siddha':   {'planet':'Venus',   'nature':'Auspicious',   'duration':'7 years', 'themes':'Love, beauty, luxury, creative success, relationships flourish, material comforts', 'warning':None},
    'Sankata':  {'planet':'Rahu',    'nature':'Inauspicious', 'duration':'8 years', 'themes':'Foreign connections, sudden disruptions, unconventional paths, karmic acceleration', 'warning':'Illusions and confusion — seek clarity before major decisions'},
}

# ── NARAYANA DASHA HOUSE THEMES ───────────────────────────────────────────────
NARAYANA_HOUSE_THEMES = {
    1:  'Self-realisation period. Identity, health, and personality come to the foreground.',
    2:  'Wealth accumulation period. Family matters, speech, and financial decisions dominate.',
    3:  'Courage and communication period. Siblings, short journeys, skill development.',
    4:  'Home and mother period. Property, emotional foundations, inner peace sought.',
    5:  'Creative and intelligence period. Children, romance, education, speculation.',
    6:  'Challenge and service period. Health requires attention. Enemies and debts surface.',
    7:  'Partnership period. Marriage, business alliances, and foreign connections activate.',
    8:  'Transformation period. Hidden matters surface. Research, inheritance, deep change.',
    9:  'Fortune and dharma period. Father, teachers, long journeys, spiritual seeking.',
    10: 'Career and authority period. Professional rise, public reputation, government dealings.',
    11: 'Gains and aspirations period. Income expands. Friends, social networks, desires fulfilled.',
    12: 'Liberation and loss period. Foreign travel, spiritual retreat, hidden expenditure.',
}

# ── ASHTOTTARI DASHA THEMES ───────────────────────────────────────────────────
ASHTOTTARI_THEMES = {
    'Sun':     'Authority, government, father, health of heart/eyes. Leadership tested.',
    'Moon':    'Mind, mother, public life, emotional shifts. Intuition peaks.',
    'Mars':    'Energy, disputes, surgery risk, property. Physical courage required.',
    'Mercury': 'Business, communication, education, siblings. Intellectual peak.',
    'Saturn':  'Delays, hard work, service, karma clearing. Discipline rewarded.',
    'Jupiter': 'Wisdom, wealth, children, spirituality. Expansion in dharmic pursuits.',
    'Rahu':    'Foreign matters, confusion, karmic encounters. Unconventional path.',
    'Venus':   'Love, luxury, creativity, relationships. Material and emotional comfort.',
}

# ── NAKSHATRA + DASHA CLASSICAL COMBINATIONS ─────────────────────────────────
NAKSHATRA_DASHA_COMBINATIONS = {
    ('Rohini', 'Jupiter'):           'Rohini Moon in Jupiter dasha — classical texts describe this as the period when what you build becomes permanent. Not merely successful — permanent.',
    ('Rohini', 'Venus'):             'Rohini Moon in Venus dasha — material abundance and sensory beauty reach their peak. This is the dasha Rohini was born for.',
    ('Ashwini', 'Ketu'):             'Ashwini Moon in Ketu dasha — the healer archetype fully activates. Spiritual gifts surface suddenly.',
    ('Ashwini', 'Mars'):             'Ashwini Moon in Mars dasha — speed and initiative at their peak. What took years now takes months.',
    ('Magha', 'Sun'):                'Magha Moon in Sun dasha — ancestral power fully awakened. Leadership and recognition from past karma.',
    ('Magha', 'Jupiter'):            'Magha Moon in Jupiter dasha — the king archetype and the priest archetype combined. Rare authority.',
    ('Mula', 'Ketu'):                'Mula Moon in Ketu dasha — the most searching period of the life. What was hidden in the roots now surfaces completely.',
    ('Mula', 'Jupiter'):             'Mula Moon in Jupiter dasha — destruction of the false and construction of the true. Painful but liberating.',
    ('Pushya', 'Saturn'):            'Pushya Moon in Saturn dasha — the nourisher learning discipline. Slow but exceptional growth.',
    ('Pushya', 'Jupiter'):           'Pushya Moon in Jupiter dasha — the most nourishing period possible. Abundance in all four directions.',
    ('Punarvasu', 'Jupiter'):        'Punarvasu Moon in Jupiter dasha — the return to grace. What was lost is found. What was broken is restored.',
    ('Revati', 'Mercury'):           'Revati Moon in Mercury dasha — the final journey\'s intelligence. Communication about deep matters reaches its peak.',
    ('Uttara Phalguni', 'Sun'):      'Uttara Phalguni Moon in Sun dasha — marriage and career both peak simultaneously. The covenant period.',
    ('Swati', 'Rahu'):               'Swati Moon in Rahu dasha — the wind and the fog together. Freedom through confusion. Important to stay grounded.',
    ('Chitra', 'Mars'):              'Chitra Moon in Mars dasha — creative fire at maximum. Build something beautiful now.',
    ('Anuradha', 'Saturn'):          'Anuradha Moon in Saturn dasha — friendship tested and deepened. Devotion rewarded through hardship.',
    ('Jyeshtha', 'Mercury'):         'Jyeshtha Moon in Mercury dasha — elder wisdom expressed through sharp intellect. Authority through knowledge.',
    ('Uttara Ashadha', 'Sun'):       'Uttara Ashadha Moon in Sun dasha — invincible victory period. The chart\'s own guarantee of success.',
    ('Shravana', 'Moon'):            'Shravana Moon in Moon dasha — the deep listener at their most receptive. Spiritual teachings arrive now.',
    ('Dhanishta', 'Mars'):           'Dhanishta Moon in Mars dasha — wealth through action. Physical effort rewarded generously.',
    ('Purva Bhadrapada', 'Jupiter'): 'Purva Bhadrapada Moon in Jupiter dasha — the fierce initiation through wisdom. Transformation with grace.',
    ('Uttara Bhadrapada', 'Saturn'): 'Uttara Bhadrapada Moon in Saturn dasha — cosmic law made personal. Karma resolving with depth.',
    ('Hasta', 'Moon'):               'Hasta Moon in Moon dasha — craftsmanship and healing at their finest. The hands know what the mind cannot explain.',
    ('Ardra', 'Rahu'):               'Ardra Moon in Rahu dasha — the storm within a storm. Intense transformation. What survives is real.',
    ('Bharani', 'Venus'):            'Bharani Moon in Venus dasha — the bearer carries beauty now. Creative and sensual life fully activated.',
    ('Krittika', 'Sun'):             'Krittika Moon in Sun dasha — the fire of purification. Burn away the false. What remains is gold.',
    ('Vishakha', 'Jupiter'):         'Vishakha Moon in Jupiter dasha — the goal is in sight. Patient effort finally rewarded with arrival.',
    ('Bharani', 'Moon'):     'Bharani Moon in Moon dasha — the bearer of life at full emotional capacity. Creative force and feeling both peak. Deep experiences of love, loss, and rebirth.',
    ('Bharani', 'Sun'):      'Bharani Moon in Sun dasha — creative authority at its peak. Recognition through bold original expression.',
    ('Bharani', 'Mars'):     'Bharani Moon in Mars dasha — fierce creative energy. What is carried must now be transformed through action.',
    ('Bharani', 'Rahu'):     'Bharani Moon in Rahu dasha — intense karmic experiences. Foreign, unconventional, deeply transformative.',
    ('Bharani', 'Jupiter'):  'Bharani Moon in Jupiter dasha — wisdom applied to deep creative work. Expansion through inner transformation.',
    ('Bharani', 'Saturn'):   'Bharani Moon in Saturn dasha — the weight of what is carried becomes conscious. Discipline applied to deep matters.',
    ('Bharani', 'Mercury'):  'Bharani Moon in Mercury dasha — deep creative intelligence expressed through words and skill.',
    ('Bharani', 'Ketu'):     'Bharani Moon in Ketu dasha — past life creative karma surfaces. Detachment from what was previously carried.',
}

# ── D9 NAVAMSA PLANET THEMES ─────────────────────────────────────────────────
D9_PLANET_THEMES = {
    ('Venus', 'Pisces'):     'Exalted Venus in D9 — very strong marriage potential. Soul deeply devoted. Spouse is artistic, sensitive.',
    ('Venus', 'Taurus'):     'Venus in own sign D9 — sensual, devoted marriage. Spouse is artistic, stable, comfort-giving.',
    ('Venus', 'Libra'):      'Venus in own sign D9 — balanced, harmonious marriage. Partnership is central to the soul path.',
    ('Jupiter', 'Cancer'):   'Exalted Jupiter in D9 — profound wisdom, exceptional spouse, spiritual depth in marriage.',
    ('Jupiter', 'Sagittarius'): 'Jupiter own sign D9 — marriage is dharmic. Spouse is teacher or guide. Expansive partnership.',
    ('Jupiter', 'Pisces'):   'Jupiter own sign D9 — spiritual marriage. Spouse has deep empathy and intuitive wisdom.',
    ('Moon', 'Taurus'):      'Exalted Moon in D9 — exceptionally strong emotional nature. Spouse is nurturing, stable, devoted.',
    ('Saturn', 'Libra'):     'Exalted Saturn in D9 — marriage through discipline and commitment. Spouse is responsible, mature.',
    ('Mars', 'Capricorn'):   'Exalted Mars in D9 — spouse is ambitious, achieving. Soul path requires disciplined action.',
    ('Mercury', 'Virgo'):    'Mercury own D9 — communicative soul. Spouse is intelligent, analytical, skill-oriented.',
    ('Sun', 'Aries'):        'Sun exalted D9 — strong soul authority. Spouse has leadership quality. Career and soul path aligned.',
}

# ── D10 PLANET THEMES ────────────────────────────────────────────────────────
D10_PLANET_THEMES = {
    'Sun':     'Career in government, leadership, administration, or public authority.',
    'Moon':    'Career connected to public, masses, hospitality, food, or caregiving.',
    'Mars':    'Career in military, engineering, surgery, sports, or competitive fields.',
    'Mercury': 'Career in communication, trade, writing, teaching, or technology.',
    'Jupiter': 'Career in education, law, finance, counselling, or spiritual guidance.',
    'Venus':   'Career in arts, luxury, beauty, fashion, entertainment, or diplomacy.',
    'Saturn':  'Career through discipline and service — law, labour, real estate, politics.',
    'Rahu':    'Unconventional career path — foreign connections, technology, innovation.',
    'Ketu':    'Spiritual or research-oriented career — healing, metaphysics, investigation.',
}


class SynthesisEngine:
    def __init__(self, engine):
        self.engine = engine
        self.planets = engine.planets
        self.asc_rashi = engine.ascendant_rashi

    def synthesize(self, topic: str, raw_data: Dict, intent_data: Dict) -> Dict:
        observations = []
        timing_chain = {}
        dasha_enrichment = {}
        varga_enrichment = {}

        try:
            obs = self._find_dominant_planet()
            if obs: observations.append(obs)
        except Exception: pass

        try:
            obs = self._find_chart_contradiction(topic)
            if obs: observations.append(obs)
        except Exception: pass

        try:
            timing_chain = self._build_timing_chain(topic, raw_data)
            if timing_chain.get('observation'): observations.append(timing_chain['observation'])
        except Exception: pass

        try:
            obs = self._nakshatra_dasha_reading()
            if obs: observations.append(obs)
        except Exception: pass

        try:
            obs = self._find_unusual_feature()
            if obs: observations.append(obs)
        except Exception: pass

        try:
            dasha_enrichment = self._enrich_dashas()
        except Exception: pass

        try:
            varga_enrichment = self._enrich_vargas()
        except Exception: pass

        return {
            'observations': observations,
            'timing_chain': timing_chain,
            'dasha_enrichment': dasha_enrichment,
            'varga_enrichment': varga_enrichment,
            'synthesis_text': self._format(observations),
        }

    def _find_dominant_planet(self) -> Optional[str]:
        scores = {}

        try:
            vimsho = self.engine.get_vimshopaka()
            ranked = sorted(vimsho.values(), key=lambda x: x.get('vimshopaka', 0), reverse=True)
            if ranked: scores[ranked[0]['planet']] = scores.get(ranked[0]['planet'], 0) + 1
        except Exception: pass

        try:
            dasha = self.engine.get_vimshottari_dasha()
            ml = dasha.get('mahadasha', {}).get('lord', '')
            if ml: scores[ml] = scores.get(ml, 0) + 1
        except Exception: pass

        try:
            moon_lon = self.planets.get('Moon', {}).get('longitude', 0)
            from ..core.constants import NAKSHATRA_LORDS
            nak_lord = NAKSHATRA_LORDS[int(moon_lon / (360/27)) % 27]
            if nak_lord: scores[nak_lord] = scores.get(nak_lord, 0) + 1
        except Exception: pass

        try:
            nav = self.engine.get_navamsa_analysis()
            for p in nav.get('vargottama_planets', []):
                if p and isinstance(p, str):
                    scores[p] = scores.get(p, 0) + 1
        except Exception: pass

        try:
            moon_lon = self.planets.get('Moon', {}).get('longitude', 0)
            from ..core.constants import NAKSHATRA_LORDS
            nak_lord = NAKSHATRA_LORDS[int(moon_lon / (360/27)) % 27]
            if nak_lord:
                scores[nak_lord] = scores.get(nak_lord, 0) + 1
        except Exception: pass

        try:
            karakas = self.engine.get_jaimini_karakas()
            ak = karakas.get('Atmakaraka', karakas.get('atmakaraka', {})).get('planet', '')
            if ak: scores[ak] = scores.get(ak, 0) + 1
        except Exception: pass

        if not scores: return None
        top = max(scores, key=scores.get)
        count = scores[top]
        if count < 2: return None

        systems = []
        try:
            vimsho = self.engine.get_vimshopaka()
            ranked = sorted(vimsho.values(), key=lambda x: x.get('vimshopaka', 0), reverse=True)
            if ranked and ranked[0]['planet'] == top:
                systems.append(f"strongest in composite strength ({ranked[0].get('vimshopaka',0)}/20)")
        except Exception: pass
        try:
            dasha = self.engine.get_vimshottari_dasha()
            if dasha.get('mahadasha',{}).get('lord') == top:
                systems.append("running your current life chapter as Mahadasha lord")
        except Exception: pass
        try:
            nav = self.engine.get_navamsa_analysis()
            if top in nav.get('vargottama_planets', []):
                systems.append("same sign in birth and soul chart (vargottama)")
        except Exception: pass
        try:
            karakas = self.engine.get_jaimini_karakas()
            ak_data = karakas.get('Atmakaraka', karakas.get('atmakaraka', {}))
            if ak_data.get('planet') == top:
                systems.append("your Atmakaraka — the soul's chosen planet")
        except Exception: pass

        # Also check if top planet is nakshatra lord of Moon
        try:
            moon_lon = self.planets.get('Moon', {}).get('longitude', 0)
            from ..core.constants import NAKSHATRA_LORDS, NAKSHATRA_NAMES
            nak_idx = int(moon_lon / (360/27)) % 27
            nak_lord = NAKSHATRA_LORDS[nak_idx]
            nak_name = NAKSHATRA_NAMES[nak_idx]
            if nak_lord == top:
                systems.append(f"ruling the Moon's birth nakshatra ({nak_name})")
        except Exception: pass

        if len(systems) >= 2:
            return (
                f"CONVERGENCE: {top} dominates across {count} independent systems — "
                f"{', '.join(systems)}. When multiple classical systems point to the same planet, "
                f"the tradition considers this the chart's defining force."
            )
        elif len(systems) == 1 and count >= 2:
            return (
                f"DOMINANT PLANET: {top} appears in {count} independent systems "
                f"({systems[0]}). This planet shapes the chart's central story."
            )
        return None

    def _find_chart_contradiction(self, topic: str) -> Optional[str]:
        try:
            from ..core.constants import DUSTHANA_HOUSES
        except ImportError:
            DUSTHANA_HOUSES = [6, 8, 12]
        from ..core.constants import RASHI_LORDS
        topic_map = {
            'marriage':(7,'Venus'), 'wealth':(2,'Jupiter'), 'career':(10,'Saturn'),
            'children':(5,'Jupiter'), 'health':(1,'Sun'), 'education':(5,'Mercury'),
            'property':(4,'Mars'), 'spiritual':(9,'Ketu'), 'love':(5,'Venus'),
            'business':(7,'Mercury'), 'general':(1,'Sun'),
        }
        house, karaka = topic_map.get(topic, (1,'Sun'))
        lord = RASHI_LORDS[(self.asc_rashi + house - 1) % 12]
        lord_house = self.planets.get(lord, {}).get('house', 0)
        lord_dignity = str(self.planets.get(lord, {}).get('dignity', '')).lower()
        karaka_data = self.planets.get(karaka, {})
        karaka_house = karaka_data.get('house', 0)
        karaka_retro = karaka_data.get('retrograde', False)
        karaka_retro = karaka_data.get('retrograde', False)
        karaka_dignity = str(karaka_data.get('dignity', '')).lower()

        lord_strong = lord_house in [1,2,4,5,7,9,10,11] and 'debilitated' not in lord_dignity
        lord_in_dusthana = lord_house in DUSTHANA_HOUSES
        karaka_weak = karaka_retro or 'debilitated' in karaka_dignity or karaka_house in DUSTHANA_HOUSES

        sat_h = self.planets.get('Saturn',{}).get('house',0)
        rahu_h = self.planets.get('Rahu',{}).get('house',0)
        ketu_h = self.planets.get('Ketu',{}).get('house',0)
        malefic_on_house = house in [sat_h, rahu_h, ketu_h]

        # Case: lord itself in dusthana — this IS the contradiction
        if lord_in_dusthana and lord == karaka:
            dusthana_meanings = {6:'enemies and obstacles', 8:'hidden transformations', 12:'loss and dissolution'}
            meaning = dusthana_meanings.get(lord_house, 'a challenging house')
            return (
                f"CONTRADICTION: {lord} is both the {house}th house lord AND the natural karaka for {topic} — "
                f"but it sits in the {lord_house}th house ({meaning}). "
                f"The planet that should deliver {topic} carries its own obstruction within it. "
                f"Classical texts: this creates a complex, delayed, but ultimately transformative experience of {topic}."
            )

        if lord_in_dusthana:
            dusthana_meanings = {6:'enemies and service', 8:'transformation and hidden matters', 12:'loss and liberation'}
            meaning = dusthana_meanings.get(lord_house, 'a challenging house')
            return (
                f"TENSION: The {house}th house lord {lord} sits in the {lord_house}th house ({meaning}). "
                f"The energy meant to deliver {topic} is redirected through difficulty. "
                f"Classical texts: the promise exists but the path runs through challenge first."
            )

        if lord_strong and karaka_weak:
            reason = []
            if karaka_retro: reason.append(f'{karaka} is retrograde')
            if 'debilitated' in karaka_dignity: reason.append(f'{karaka} is debilitated')
            if karaka_house in DUSTHANA_HOUSES: reason.append(f'{karaka} sits in the {karaka_house}th house')
            if reason:
                return (
                    f"CONTRADICTION: The {house}th house lord {lord} is well-placed — "
                    f"the chart promises {topic}. But {', '.join(reason)} "
                    f"creates the tension you may already feel. "
                    f"This is the classical pattern of the chart that holds the promise but tests the timing."
                )

        if lord_strong and malefic_on_house:
            malefic = 'Saturn' if sat_h==house else ('Rahu' if rahu_h==house else 'Ketu')
            meanings = {
                'Saturn': 'delays and disciplines the experience',
                'Rahu':   'creates confusion and unconventional routes',
                'Ketu':   'brings detachment — possible disconnection from the outcome',
            }
            return (
                f"TENSION: Strong {house}th house foundation but {malefic} sits there — "
                f"{meanings.get(malefic, 'afflicts the house')}. "
                f"The promise is real. The path is more layered than expected."
            )
        return None

    def _build_timing_chain(self, topic: str, raw_data: Dict) -> Dict:
        chain = {}

        try:
            dasha = self.engine.get_vimshottari_dasha()
            chain['mahadasha'] = dasha.get('mahadasha',{}).get('lord','')
            chain['antardasha'] = dasha.get('antardasha',{}).get('lord','')
            chain['antardasha_end'] = str(dasha.get('antardasha',{}).get('end',''))[:10]
        except Exception: pass

        try:
            prat = self.engine.get_pratyantar_dasha()
            cp = prat.get('current_pratyantar', {})
            chain['pratyantar'] = cp.get('lord','')
            chain['pratyantar_end'] = cp.get('end','')
        except Exception: pass

        try:
            chara = self.engine.get_chara_dasha()
            chain['chara_sign'] = chara.get('current_dasha',{}).get('sign','')
        except Exception: pass

        try:
            yogini = self.engine.get_yogini_dasha()
            ym = yogini.get('mahadasha',{})
            chain['yogini'] = ym.get('yogini','')
            chain['yogini_planet'] = ym.get('planet','')
            chain['yogini_nature'] = ym.get('nature','')
        except Exception: pass

        try:
            topic_to_kp = {
                'marriage':'marriage','career':'career','wealth':'wealth',
                'children':'children','education':'education','property':'property',
                'travel':'foreign','business':'business','health':'health',
                'legal':'legal','spiritual':'spiritual','love':'love',
            }
            kp_event = topic_to_kp.get(topic, 'general')
            kp = self.engine.kp_event_analysis(kp_event)
            chain['kp_verdict'] = kp.get('verdict','')
            chain['kp_confidence'] = kp.get('confidence',0)
            chain['kp_csl'] = kp.get('cusp_sub_lord', '')
            kpv = self.engine.kp_verify_event(kp_event)
            chain['kp_rp_verdict'] = kpv.get('rp_verdict', '')
            chain['kp_rp_match'] = len(kpv.get('matching_rp', []))
        except Exception: pass

        try:
            sandhi = self.engine.get_dasha_sandhi()
            chain['in_sandhi'] = sandhi.get('in_sandhi', False)
            if sandhi.get('in_sandhi'):
                details = sandhi.get('sandhi_details',[])
                chain['sandhi_description'] = details[0].get('description','') if details else ''
        except Exception: pass

        return {'chain': chain, 'observation': self._timing_obs(chain, topic)}

    def _timing_obs(self, chain: Dict, topic: str) -> Optional[str]:
        parts = []
        maha = chain.get('mahadasha','')
        antar = chain.get('antardasha','')
        prat = chain.get('pratyantar','')
        prat_end = chain.get('pratyantar_end','')
        kp = chain.get('kp_verdict','')
        kp_rp = chain.get('kp_rp_verdict','')
        yogini = chain.get('yogini','')
        yogini_planet = chain.get('yogini_planet','')
        yogini_nature = chain.get('yogini_nature','')
        in_sandhi = chain.get('in_sandhi', False)
        sandhi_desc = chain.get('sandhi_description','')

        if in_sandhi and sandhi_desc:
            parts.append(
                f"DASHA JUNCTION: {sandhi_desc}. "
                f"This transition period requires care — classical texts call it Dasha Chidra. "
                f"Major decisions should wait until the new dasha stabilises."
            )

        if kp and 'PROMISED' in kp.upper():
            note = f"KP Cuspal Sub Lord confirms: {topic} is PROMISED in this chart."
            if kp_rp and 'CONFIRMED' in kp_rp.upper():
                note += f" Ruling Planets also confirm ({kp_rp})."
            parts.append(note)
        elif kp and 'DENIED' in kp.upper():
            parts.append(
                f"KP analysis: {topic} is not indicated by the Cuspal Sub Lord. "
                f"The event cannot manifest until the CSL changes."
            )

        if prat and prat_end:
            parts.append(
                f"Pratyantar dasha {maha}/{antar}/{prat} runs until {prat_end} — "
                f"this is the week-level timing window."
            )

        if yogini_planet and maha:
            if yogini_planet == maha:
                parts.append(
                    f"Yogini cross-check: Both Vimshottari ({maha}) and Yogini ({yogini}, planet: {yogini_planet}) "
                    f"point to the same planet — two independent systems agreeing is the classical marker of a significant period."
                )
            elif yogini_nature == 'Inauspicious' and maha in ('Saturn','Rahu','Ketu','Mars'):
                parts.append(
                    f"Dual pressure: Vimshottari {maha} and Yogini {yogini} ({yogini_nature}) both challenging. "
                    f"The soul is in deep refinement."
                )
            elif yogini_nature == 'Auspicious' and maha in ('Jupiter','Venus','Mercury','Moon'):
                parts.append(
                    f"Dual benefic: Vimshottari {maha} and Yogini {yogini} (Auspicious) both favourable — classically doubly blessed."
                )

        return ' | '.join(parts) if parts else None

    def _nakshatra_dasha_reading(self) -> Optional[str]:
        try:
            moon_lon = self.planets.get('Moon',{}).get('longitude',0)
            from ..core.constants import NAKSHATRA_NAMES
            nak_name = NAKSHATRA_NAMES[int(moon_lon / (360/27)) % 27]
            dasha = self.engine.get_vimshottari_dasha()
            maha_lord = dasha.get('mahadasha',{}).get('lord','')
            reading = NAKSHATRA_DASHA_COMBINATIONS.get((nak_name, maha_lord))
            if reading:
                return f"NAKSHATRA-DASHA: {reading}"
        except Exception: pass
        return None

    def _find_unusual_feature(self) -> Optional[str]:
        unusual = []

        try:
            karakas = self.engine.get_jaimini_karakas()
            ak = karakas.get('atmakaraka',{})
            amk = karakas.get('amatyakaraka',{})
            ak_p = ak.get('planet','')
            amk_p = amk.get('planet','')
            ak_lon = self.planets.get(ak_p,{}).get('longitude',-1)
            amk_lon = self.planets.get(amk_p,{}).get('longitude',-1)
            if ak_lon >= 0 and amk_lon >= 0:
                from ..core.constants import NAKSHATRA_NAMES
                ak_nak = int(ak_lon/(360/27)) % 27
                amk_nak = int(amk_lon/(360/27)) % 27
                if ak_nak == amk_nak:
                    unusual.append(
                        f"RARE: Atmakaraka ({ak_p}) and Amatyakaraka ({amk_p}) occupy the same nakshatra "
                        f"({NAKSHATRA_NAMES[ak_nak]}). Classical Jaimini: your soul's purpose and life's career are one and the same. "
                        f"You are meant to do the work your soul came for."
                    )
        except Exception: pass

        try:
            nav = self.engine.get_navamsa_analysis()
            for p in nav.get('vargottama_planets',[]):
                p_house = self.planets.get(p,{}).get('house',0)
                if p_house in [1,4,7,10]:
                    unusual.append(
                        f"POWERFUL: {p} is Vargottama (same sign in birth and soul chart) AND angular (H{p_house}). "
                        f"Classical texts: this planet delivers its results fully and permanently."
                    )
        except Exception: pass

        try:
            house_counts = {}
            for p, data in self.planets.items():
                h = data.get('house',0)
                if h:
                    house_counts.setdefault(h,[]).append(p)
            for h, ps in house_counts.items():
                if len(ps) >= 4:
                    unusual.append(
                        f"STELLIUM: {', '.join(ps)} all gather in your {h}th house — "
                        f"four or more planets in one house is extremely rare. This house dominates the entire life story."
                    )
                    break
        except Exception: pass

        try:
            yogas = self.engine.get_yogas()
            yoga_list = []
            for cat in yogas.get('yogas',{}).values():
                if isinstance(cat, list): yoga_list.extend(cat)
            for y in yoga_list:
                if 'Parivartana' in y.get('name',''):
                    unusual.append(
                        f"MUTUAL EXCHANGE: {y.get('name','')} — {y.get('description','')}. "
                        f"These two planets act as if they occupy each other's positions simultaneously. Double strength for both."
                    )
                    break
        except Exception: pass

        return unusual[0] if unusual else None

    def _enrich_dashas(self) -> Dict:
        enrichment = {}

        try:
            yogini = self.engine.get_yogini_dasha()
            yogi_name = yogini.get('mahadasha',{}).get('yogini','')
            if yogi_name in YOGINI_THEMES:
                info = YOGINI_THEMES[yogi_name]
                enrichment['yogini'] = {
                    'reading': (
                        f"Yogini dasha {yogi_name} ({info['nature']}, {info['duration']}): {info['themes']}."
                        + (f" Note: {info['warning']}" if info.get('warning') else '')
                    )
                }
        except Exception: pass

        try:
            narayana = self.engine.get_narayana_dasha()
            house = narayana.get('current_dasha',{}).get('house',0)
            if house and house in NARAYANA_HOUSE_THEMES:
                enrichment['narayana'] = {'reading': f"Narayana dasha H{house}: {NARAYANA_HOUSE_THEMES[house]}"}
        except Exception: pass

        try:
            rahu_house = self.planets.get('Rahu',{}).get('house',0)
            if rahu_house in [1,4,5,7,9,10]:
                from ..dashas.ashtottari import AshtottariDasha
                moon_lon = self.planets.get('Moon',{}).get('longitude',0)
                ash = AshtottariDasha(moon_lon, self.engine.birth_dt)
                lord = ash.get_current_dasha().get('mahadasha',{}).get('lord','')
                if lord in ASHTOTTARI_THEMES:
                    enrichment['ashtottari'] = {'reading': f"Ashtottari dasha ({lord}): {ASHTOTTARI_THEMES[lord]}"}
        except Exception: pass

        return enrichment

    def _enrich_vargas(self) -> Dict:
        enrichment = {}
        try:
            from ..core.constants import RASHI_NAMES
            nav = self.engine.get_navamsa_analysis()
            v_rashi = nav.get('venus_placement',{}).get('rashi',None)
            if v_rashi is not None:
                sign = RASHI_NAMES[v_rashi]
                reading = D9_PLANET_THEMES.get(('Venus', sign))
                if reading:
                    enrichment['d9_venus'] = {'reading': f"D9 Venus in {sign}: {reading}"}
            spouse = nav.get('spouse_description','')
            if spouse:
                enrichment['d9_spouse'] = {'reading': f"D9 spouse: {spouse}"}
        except Exception: pass

        try:
            from ..core.constants import RASHI_LORDS, RASHI_NAMES
            lord10 = RASHI_LORDS[(self.asc_rashi + 9) % 12]
            theme = D10_PLANET_THEMES.get(lord10,'')
            if theme:
                enrichment['d10'] = {'reading': f"D10 career ({lord10}): {theme}"}
        except Exception: pass

        return enrichment

    def _format(self, observations: List[str]) -> str:
        if not observations: return ''
        lines = ['SYNTHESIS (cross-system analysis):']
        for i, obs in enumerate(observations, 1):
            lines.append(f"{i}. {obs}")
        return '\n'.join(lines)


def synthesize(engine, topic: str, raw_data: Dict, intent_data: Dict) -> Dict:
    return SynthesisEngine(engine).synthesize(topic, raw_data, intent_data)


# ── LIFE WINDOWS FINDER ───────────────────────────────────────────────────────

TOPIC_SIGNIFICATORS = {
    'marriage':  ['Venus', 'Jupiter', 'Moon', 'Rahu', 'Mercury', 'Mars'],
    'love':      ['Venus', 'Moon', 'Mars', 'Jupiter', 'Rahu'],
    'career':    ['Saturn', 'Sun', 'Mercury', 'Jupiter', 'Mars', 'Rahu'],
    'wealth':    ['Jupiter', 'Venus', 'Mercury', 'Moon', 'Mars'],
    'children':  ['Jupiter', 'Moon', 'Mars', 'Venus'],
    'spiritual': ['Ketu', 'Jupiter', 'Saturn', 'Moon', 'Rahu'],
    'property':  ['Mars', 'Moon', 'Venus', 'Saturn'],
    'education': ['Mercury', 'Jupiter', 'Sun', 'Moon'],
    'travel':    ['Rahu', 'Jupiter', 'Mercury', 'Moon', 'Saturn'],
    'health':    ['Sun', 'Mars', 'Saturn', 'Moon'],
    'business':  ['Mercury', 'Venus', 'Jupiter', 'Saturn', 'Rahu'],
    'foreign':   ['Rahu', 'Jupiter', 'Saturn', 'Mercury', 'Moon'],
    'general':   ['Jupiter', 'Venus', 'Mercury', 'Moon', 'Rahu'],
}

DASHA_QUALITIES = {
    'Jupiter': 'expansion and wisdom — the great benefic opens doors',
    'Venus':   'beauty and fulfilment — relationships and creativity peak',
    'Moon':    'emotional depth — feeling and intuition heightened',
    'Mercury': 'intelligence and communication — sharp, strategic, connected',
    'Sun':     'authority and recognition — identity crystallises',
    'Mars':    'energy and action — bold moves rewarded',
    'Saturn':  'discipline and mastery — slow but permanent gains',
    'Rahu':    'ambition and transformation — unconventional breakthroughs',
    'Ketu':    'liberation and past-life gifts — spiritual depth',
}


class LifeWindowsFinder:
    def __init__(self, engine):
        self.engine = engine
        self.planets = engine.planets
        self.asc_rashi = engine.ascendant_rashi

    def find_windows(self, topic: str, top_n: int = 3, sort_by: str = 'chronological') -> Dict:
        significators = TOPIC_SIGNIFICATORS.get(topic, TOPIC_SIGNIFICATORS['general'])
        try:
            all_periods = self.engine.get_vimshottari_periods(120)
        except Exception:
            return {}

        from datetime import datetime as _dt
        now = _dt.now()
        windows = []

        for p in all_periods:
            lord = p.get('lord', '')
            try:
                s = p.get('start')
                e = p.get('end')
                start = s if isinstance(s, _dt) else _dt.fromisoformat(str(s)[:10])
                end   = e if isinstance(e, _dt) else _dt.fromisoformat(str(e)[:10])
            except Exception:
                continue

            # Skip past periods and beyond human lifespan
            if end <= now or start.year > 2106:
                continue

            is_current = start <= now < end

            windows.append({
                'lord':       lord,
                'start':      str(start)[:10],
                'end':        str(end)[:10],
                'start_dt':   start,
                'end_dt':     end,
                'is_current': is_current,
                'quality':    DASHA_QUALITIES.get(lord, 'significant period'),
                'years':      round((end - start).days / 365.25, 1),
                'is_sig':     lord in significators,
                'sig_rank':   (len(significators) - significators.index(lord)) if lord in significators else 0,
            })

        if not windows:
            return {}

        current = [w for w in windows if w['is_current']]
        future  = [w for w in windows if not w['is_current']]

        if sort_by == 'score':
            # Best significators first
            future_sorted = sorted(future, key=lambda x: x['sig_rank'], reverse=True)
        else:
            # Chronological — what comes next
            future_sorted = sorted(future, key=lambda x: x['start_dt'])

        top_windows = (current + future_sorted)[:top_n]

        # Build narrative
        parts = []
        for w in top_windows:
            if w['is_current']:
                parts.append(f"NOW ({w['lord']} until {w['end'][:4]}): {w['quality']}")
            else:
                age = w['start_dt'].year - 2006
                parts.append(f"{w['start'][:4]} age~{age} ({w['lord']}): {w['quality']}")

        narrative = ' | '.join(parts) + '.'

        return {'topic': topic, 'windows': top_windows, 'narrative': narrative}


