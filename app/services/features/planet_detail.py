"""
PLANET DETAIL — Deep single-planet reading.

Returns:
  - Calculated data: position, dignity, strength, house, nakshatra, dasha status, transits
  - LLM-written interpretation: significance + current effects on user

Called by: POST /planet-detail { planet, kundli_data }
"""

from datetime import datetime
from typing import Dict, Optional
from .education import (
    get_planet_edu, get_house_ed, get_planet_in_house,
    get_dignity_ed
)


PLANET_ORDER = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

# ── Rich archetype / mythology / role data per planet ──
PLANET_LORE = {
    'Sun': {
        'deity': 'Surya',
        'archetype': 'The King',
        'element': 'Fire',
        'mythology': 'Surya rides a chariot of seven horses across the sky — each horse a day of the week. In Vedic tradition, he is the Atmakaraka of the universe, the soul of all beings. His father is Kashyapa, his sons include Yama (death) and Shani (Saturn). The Gayatri Mantra is addressed to him.',
        'role_in_astrology': 'The Sun represents the soul (Atma), the ego, willpower, and the father. He is the king of the planetary cabinet — where he sits, he demands authority. He rules Leo, is exalted in Aries, and debilitated in Libra. Planets too close to him become combust — their significations get absorbed into his light. The Sun gives government positions, leadership roles, and self-confidence. His dasha brings visibility and recognition but also ego confrontations.',
        'body_parts': 'Heart, bones, right eye, spine, stomach',
        'rules': 'Leo',
        'exalts_in': 'Aries',
        'debilitates_in': 'Libra',
        'friends': 'Moon, Mars, Jupiter',
        'enemies': 'Venus, Saturn',
    },
    'Moon': {
        'deity': 'Chandra',
        'archetype': 'The Queen',
        'element': 'Water',
        'mythology': 'Chandra was born from the churning of the cosmic ocean (Samudra Manthan). He married 27 daughters of Daksha — these are the 27 Nakshatras. He favored Rohini above all, and was cursed by Daksha to wane. Shiva placed him on his head, giving him the cycle of waxing and waning. His waxing phase brings prosperity, his waning phase brings introspection.',
        'role_in_astrology': 'The Moon rules the mind (Manas), emotions, mother, and public perception. In Jyotish, the Moon sign is more important than the Sun sign — your Rashi is your Moon sign, not your Sun sign. The Moon determines your emotional nature, mental patterns, and how you relate to the world. A strong Moon gives emotional stability, intuition, and popularity. A weak Moon creates anxiety, mood swings, and sleep disturbances. The Moon is the fastest graha and changes sign every 2.5 days.',
        'body_parts': 'Mind, blood, chest, left eye, lungs, fluids',
        'rules': 'Cancer',
        'exalts_in': 'Taurus',
        'debilitates_in': 'Scorpio',
        'friends': 'Sun, Mercury',
        'enemies': 'None (no permanent enemies)',
    },
    'Mars': {
        'deity': 'Mangala / Kartikeya',
        'archetype': 'The Commander',
        'element': 'Fire',
        'mythology': 'Mars is Kartikeya — the six-headed war god, born from Shiva\'s third eye to destroy the demon Tarakasura. He rides a peacock and commands the army of the gods. In some Puranas he is Bhoomi-putra — son of the Earth herself. He is the eternal bachelor, the warrior who fights not for glory but for dharma.',
        'role_in_astrology': 'Mars governs courage, energy, siblings, property, and physical strength. He is the natural karaka for the 3rd and 6th houses. Mars in the 1st, 4th, 7th, 8th, or 12th house creates Manglik dosha — a consideration in marriage matching. He rules Aries and Scorpio and is the Yogakaraka (best planet) for Cancer and Leo ascendants. A strong Mars gives property, athletic ability, and decisive action. A weak Mars brings suppressed anger, accidents, and blood disorders.',
        'body_parts': 'Blood, muscles, bone marrow, head, genitals',
        'rules': 'Aries, Scorpio',
        'exalts_in': 'Capricorn',
        'debilitates_in': 'Cancer',
        'friends': 'Sun, Moon, Jupiter',
        'enemies': 'Mercury',
    },
    'Mercury': {
        'deity': 'Budha',
        'archetype': 'The Prince',
        'element': 'Earth',
        'mythology': 'Budha is the son of Chandra (Moon) and Tara (wife of Jupiter). His very birth was scandalous — born from an affair, he was initially rejected. But his intelligence was so extraordinary that he earned his place among the nine grahas. He is the eternal student, the diplomat, the one who can speak to all sides.',
        'role_in_astrology': 'Mercury governs intelligence, speech, commerce, writing, and nervous system. He is the only planet considered a natural benefic when alone and a natural malefic when associated with malefics — a true chameleon. He rules Gemini and Virgo. Mercury is the karaka for education, business, and communication. When retrograde, communications misfire and contracts go wrong. A strong Mercury gives wit, eloquence, and commercial success. Mercury is frequently combust because he never moves far from the Sun.',
        'body_parts': 'Skin, nervous system, tongue, hands, lungs',
        'rules': 'Gemini, Virgo',
        'exalts_in': 'Virgo',
        'debilitates_in': 'Pisces',
        'friends': 'Sun, Venus',
        'enemies': 'Moon',
    },
    'Jupiter': {
        'deity': 'Brihaspati / Guru',
        'archetype': 'The Guru',
        'element': 'Ether (Akasha)',
        'mythology': 'Brihaspati is the guru of the Devas — the divine teacher who guides the gods through every cosmic battle. He is the keeper of sacred knowledge, the one who knows all mantras. In the Rig Veda he is called the "lord of sacred speech." When Jupiter is strong, the right teachers appear at the right time. When he is weak, one follows false gurus.',
        'role_in_astrology': 'Jupiter is the greatest benefic in Vedic astrology. He governs wisdom, expansion, children, dharma, wealth, and spiritual growth. He rules Sagittarius and Pisces. Jupiter is the karaka for the 2nd (wealth), 5th (children, intelligence), 9th (fortune, guru), and 11th (gains) houses. His transit through your Moon sign and adjacent signs creates the 12-year cycle of fortune. Jupiter\'s dasha brings growth, marriage, children, and religious inclination. He protects wherever he aspects — his 5th, 7th, and 9th aspects are considered divine shields.',
        'body_parts': 'Liver, fat, hips, thighs, ears',
        'rules': 'Sagittarius, Pisces',
        'exalts_in': 'Cancer',
        'debilitates_in': 'Capricorn',
        'friends': 'Sun, Moon, Mars',
        'enemies': 'Mercury, Venus',
    },
    'Venus': {
        'deity': 'Shukra / Shukracharya',
        'archetype': 'The Minister',
        'element': 'Water',
        'mythology': 'Shukracharya is the guru of the Asuras — the demons. He possesses the Sanjeevani Vidya, the knowledge to bring the dead back to life. He lost one eye in a conflict with Vishnu\'s Vamana avatar. Despite being the teacher of demons, Shukra represents the highest refinement of beauty, love, and creative expression. He teaches that desire itself is not the enemy — unconscious desire is.',
        'role_in_astrology': 'Venus governs love, marriage, beauty, luxury, art, vehicles, and the reproductive system. He rules Taurus and Libra. Venus is the karaka for the 7th house (spouse, partnership). A strong Venus gives charm, artistic talent, luxury, and a beautiful marriage. A weak Venus creates relationship problems, lack of refinement, and reproductive health issues. Venus and Jupiter never agree — Jupiter expands through wisdom, Venus through pleasure. Venus is combust for significant portions of the year, which is why love is often complicated.',
        'body_parts': 'Reproductive system, kidneys, face, throat, eyes',
        'rules': 'Taurus, Libra',
        'exalts_in': 'Pisces',
        'debilitates_in': 'Virgo',
        'friends': 'Mercury, Saturn',
        'enemies': 'Sun, Moon',
    },
    'Saturn': {
        'deity': 'Shani',
        'archetype': 'The Judge',
        'element': 'Air',
        'mythology': 'Shani is the son of Surya (Sun) and Chhaya (Shadow). His gaze is so powerful that when he looked at baby Ganesha, the child\'s head fell off. He even afflicted his own father. But Shani is not cruel — he is just. He delivers the exact karma you have earned. The 7.5-year Sade Sati (Saturn transit over your Moon) is the most feared period in Jyotish, but also the most transformative. Hanuman is his only friend — devotion to Hanuman is said to pacify Saturn.',
        'role_in_astrology': 'Saturn governs discipline, karma, longevity, chronic illness, delays, servants, and hard labor. He rules Capricorn and Aquarius. Saturn is the karaka for the 6th (disease, enemies), 8th (longevity, hidden matters), and 12th (loss, moksha) houses. He is the slowest visible planet, spending 2.5 years in each sign. His dasha lasts 19 years — the longest test of endurance. A strong Saturn gives unshakeable discipline, political power, and longevity. A weak Saturn brings depression, chronic pain, and karmic debt. Saturn rewards patience and punishes shortcuts.',
        'body_parts': 'Bones, joints, teeth, legs, chronic conditions',
        'rules': 'Capricorn, Aquarius',
        'exalts_in': 'Libra',
        'debilitates_in': 'Aries',
        'friends': 'Mercury, Venus',
        'enemies': 'Sun, Moon, Mars',
    },
    'Rahu': {
        'deity': 'Rahu (Shadow planet)',
        'archetype': 'The Shadow',
        'element': 'None (shadow)',
        'mythology': 'During the Samudra Manthan, the demon Svarbhanu disguised himself as a deva and drank the nectar of immortality. Vishnu\'s Sudarshana Chakra severed his head — but the nectar had already passed his throat. The head became Rahu, the body became Ketu. Rahu swallows the Sun during eclipses as eternal revenge. He is the mouth that is never satisfied, the hunger that defines ambition.',
        'role_in_astrology': 'Rahu is not a physical planet but the north node of the Moon — where the Moon\'s orbit crosses the ecliptic going north. He has no sign of his own but acts like Saturn. Rahu amplifies whatever he touches — in a good house, he magnifies fortune; in a bad house, he magnifies trouble. He governs obsession, foreign connections, technology, unconventional paths, sudden events, and illusion. Rahu\'s dasha (18 years) is the most unpredictable period — it can bring extraordinary worldly success or complete delusion. Rahu represents what the soul craves in this lifetime.',
        'body_parts': 'Skin diseases, phobias, poisoning, psychosomatic illness',
        'rules': 'No own sign (co-rules Aquarius traditionally)',
        'exalts_in': 'Taurus/Gemini (disputed)',
        'debilitates_in': 'Scorpio/Sagittarius (disputed)',
        'friends': 'Venus, Saturn',
        'enemies': 'Sun, Moon, Mars',
    },
    'Ketu': {
        'deity': 'Ketu (Shadow planet)',
        'archetype': 'The Headless One',
        'element': 'None (shadow)',
        'mythology': 'Ketu is the headless body of the demon Svarbhanu. Without a head, he cannot think, plan, or desire — only feel. He represents what you have already mastered in past lives. Where Rahu is the future you crave, Ketu is the past you must release. Ketu brings sudden detachment, spiritual awakening, and psychic sensitivity. He is associated with Ganesha — the remover of obstacles — because sometimes the greatest obstacle is attachment itself.',
        'role_in_astrology': 'Ketu is the south node of the Moon. He acts like Mars — sharp, sudden, and surgical. Ketu dissolves whatever he touches: in the 7th house, he detaches from relationships; in the 2nd, he detaches from wealth; in the 12th, he grants moksha. Ketu\'s dasha (7 years) brings spiritual breakthroughs but also confusion about identity and purpose. A strong Ketu gives extraordinary intuition, spiritual gifts, and the ability to let go. A weak Ketu brings aimlessness, identity crisis, and unexplained losses. Ketu in the 12th house is considered the highest moksha placement.',
        'body_parts': 'Spine, nervous system, mysterious/undiagnosable conditions',
        'rules': 'No own sign (co-rules Scorpio traditionally)',
        'exalts_in': 'Scorpio/Sagittarius (disputed)',
        'debilitates_in': 'Taurus/Gemini (disputed)',
        'friends': 'Mars, Jupiter',
        'enemies': 'Sun, Moon',
    },
}


def _safe(fn, default=None):
    try:
        result = fn()
        return result if result is not None else default
    except Exception:
        return default


def build_planet_detail(engine, planet_name: str, language: str = 'en') -> Dict:
    """
    Build comprehensive data packet for a single planet.
    Returns structured data for frontend + a briefing string for LLM.
    """
    if planet_name not in PLANET_ORDER:
        return {'error': f'Unknown planet: {planet_name}'}

    # ── Core planet data ──
    planet_dict = engine.planets if isinstance(getattr(engine, 'planets', None), dict) else {}
    pl = planet_dict.get(planet_name, {})
    if not isinstance(pl, dict): pl = {}

    # ── Shadbala strength ──
    sb_complete = _safe(engine.get_shadbala_complete, {}) or {}
    if not isinstance(sb_complete, dict): sb_complete = {}
    sb_planets = sb_complete.get('planets', {})
    if not isinstance(sb_planets, dict): sb_planets = {}
    sb = sb_planets.get(planet_name, {})
    if not isinstance(sb, dict): sb = {}

    # ── Dignity ──
    dignity_data = _safe(engine.get_planetary_dignity, {}) or {}
    if not isinstance(dignity_data, dict): dignity_data = {}
    dignity_planets = dignity_data.get('planets', {})
    if not isinstance(dignity_planets, dict): dignity_planets = {}
    dg = dignity_planets.get(planet_name, {})
    if not isinstance(dg, dict): dg = {}

    # ── Dasha info ──
    dasha_data = _safe(engine.get_vimshottari_dasha, {}) or {}
    if not isinstance(dasha_data, dict): dasha_data = {}
    maha = dasha_data.get('mahadasha', {})
    if not isinstance(maha, dict): maha = {}
    antar = dasha_data.get('antardasha', {})
    if not isinstance(antar, dict): antar = {}
    current_maha = maha.get('lord', '')
    current_antar = antar.get('lord', '')
    dasha_string = dasha_data.get('dasha_string', '')
    is_dasha_lord = planet_name in (current_maha, current_antar)

    maha_start = maha.get('start', '')
    maha_end = maha.get('end', '')
    antar_start = antar.get('start', '')
    antar_end = antar.get('end', '')

    # ── Transits ──
    transit_data = _safe(engine.get_current_transits, {}) or {}
    if not isinstance(transit_data, dict): transit_data = {}
    transit_planet = transit_data.get(planet_name, {})
    if not isinstance(transit_planet, dict): transit_planet = {}
    transit_sign = transit_planet.get('rashi_name', '')
    transit_nak = transit_planet.get('nakshatra_name', '')
    transit_retro = transit_planet.get('retrograde', False)

    # ── Yogas involving this planet ──
    yoga_data = _safe(engine.get_yogas, {}) or {}
    if not isinstance(yoga_data, dict): yoga_data = {}
    all_yogas = yoga_data.get('yogas', [])
    if not isinstance(all_yogas, list): all_yogas = []
    planet_yogas = []
    for y in all_yogas:
        if not isinstance(y, dict): continue
        participants = y.get('planets', [])
        if isinstance(participants, list) and planet_name in participants:
            planet_yogas.append({
                'name': y.get('name', ''),
                'type': y.get('type', ''),
                'effect': str(y.get('effect', ''))[:120],
            })
        elif isinstance(participants, str) and planet_name in participants:
            planet_yogas.append({
                'name': y.get('name', ''),
                'type': y.get('type', ''),
                'effect': str(y.get('effect', ''))[:120],
            })

    # ── Aspects on this planet ──
    aspect_data = _safe(engine.get_planetary_aspects, {}) or {}
    if not isinstance(aspect_data, dict): aspect_data = {}
    aspects_list = aspect_data.get('aspects', [])
    if not isinstance(aspects_list, list): aspects_list = []
    planet_aspects = []
    for a in aspects_list:
        if not isinstance(a, dict): continue
        if a.get('aspecting') == planet_name or a.get('aspected') == planet_name:
            planet_aspects.append({
                'from': a.get('aspecting', ''),
                'to': a.get('aspected', ''),
                'type': a.get('aspect_type', ''),
                'nature': a.get('nature', ''),
            })

    # ── Combustion ──
    comb = dg.get('combustion', {})
    if not isinstance(comb, dict): comb = {}
    is_combust = comb.get('is_combust', False)

    # ── Retrograde ──
    is_retro = pl.get('is_retrograde', False) or pl.get('retrograde', False)

    # ── Nakshatra info ──
    nak_name = pl.get('nakshatra_name', '')
    nak_pada = pl.get('nakshatra_pada', pl.get('pada', 0))

    # ── House info ──
    house = dg.get('house', pl.get('house', 0))
    sign = pl.get('rashi_name', '')
    degree = round(pl.get('longitude', 0) % 30, 2) if pl.get('longitude') else 0

    # ── Dignity label ──
    dignity_type = dg.get('dignity_type', 'neutral_sign')

    # ── Strength percentage ──
    strength_pct = sb.get('percentage', 50)
    strength_grade = sb.get('grade', 'Average')

    # ── Status ──
    if is_combust:
        status = 'COMBUST'
    elif strength_grade == 'Strong':
        status = 'STRONG'
    elif strength_grade == 'Weak':
        status = 'WEAK'
    else:
        status = strength_grade.upper() if isinstance(strength_grade, str) else 'AVERAGE'

    # ── Educational content ──
    edu = get_planet_edu(planet_name, language)
    house_ed = get_house_ed(house, language)
    house_text = get_planet_in_house(planet_name, house, language)
    dignity_ed = get_dignity_ed(dignity_type, language)

    if is_combust:
        dignity_ed = ('Combust', 'Too close to the Sun — light absorbed. Significations hidden temporarily.')

    strength_text = edu.get('strong', '') if strength_pct > 55 else edu.get('weak', '')

    # ── Modifiers ──
    modifiers = []
    if is_combust:
        modifiers.append('Combust')
    if is_retro:
        modifiers.append('Retrograde')
    if is_dasha_lord:
        modifiers.append('Dasha Active')

    # ── Build briefing for LLM ──
    lore = PLANET_LORE.get(planet_name, {})

    briefing_lines = [
        f"PLANET: {planet_name}",
        f"Deity: {lore.get('deity', '')} | Archetype: {lore.get('archetype', '')}",
        f"Rules: {lore.get('rules', '')} | Exalted in: {lore.get('exalts_in', '')} | Debilitated in: {lore.get('debilitates_in', '')}",
        f"Sign: {sign} | House: H{house} | Degree: {degree}°",
        f"Nakshatra: {nak_name} (Pada {nak_pada})",
        f"Dignity: {dignity_type} | Strength: {strength_pct}% ({strength_grade})",
    ]
    if is_combust:
        briefing_lines.append("STATUS: COMBUST (too close to Sun)")
    if is_retro:
        briefing_lines.append("STATUS: RETROGRADE")
    if is_dasha_lord:
        briefing_lines.append(f"DASHA: Currently active — {dasha_string}")
    else:
        briefing_lines.append(f"Current dasha: {dasha_string} (this planet is NOT the active period lord)")

    if transit_sign:
        briefing_lines.append(f"TRANSIT: Currently in {transit_sign} ({transit_nak}){' RETROGRADE' if transit_retro else ''}")

    if planet_yogas:
        yoga_names = ', '.join(y['name'] for y in planet_yogas[:4])
        briefing_lines.append(f"YOGAS: {yoga_names}")

    if planet_aspects:
        asp_strs = [f"{a['from']}→{a['to']} ({a['nature']})" for a in planet_aspects[:4]]
        briefing_lines.append(f"ASPECTS: {'; '.join(asp_strs)}")

    briefing_lines.append(f"House meaning: {house_ed[1] if house_ed else ''}")
    briefing_lines.append(f"Planet in this house: {house_text}")
    briefing_lines.append(f"Mythology: {lore.get('mythology', '')}")
    briefing_lines.append(f"Role: {lore.get('role_in_astrology', '')}")

    briefing = '\n'.join(briefing_lines)

    # ── Structured response ──
    return {
        'planet': planet_name,
        'sign': sign,
        'house': house,
        'degree': degree,
        'nakshatra': nak_name,
        'nakshatra_pada': nak_pada,
        'strength': strength_pct,
        'strength_grade': strength_grade,
        'status': status,
        'dignity_type': dignity_type,
        'dignity_label': dignity_ed[0] if dignity_ed else '',
        'dignity_text': dignity_ed[1] if dignity_ed else '',
        'is_combust': is_combust,
        'is_retrograde': is_retro,
        'is_dasha_lord': is_dasha_lord,
        'dasha_string': dasha_string,
        'modifiers': modifiers,
        'transit_sign': transit_sign,
        'transit_nakshatra': transit_nak,
        'transit_retrograde': transit_retro,
        'yogas': planet_yogas[:5],
        'aspects': planet_aspects[:5],
        'edu': {
            'significance': edu.get('significance', ''),
            'nature': edu.get('nature', ''),
            'strength_text': strength_text,
            'day': edu.get('day', ''),
            'gem': edu.get('gem', ''),
            'color': edu.get('color', ''),
        },
        'lore': {
            'deity': lore.get('deity', ''),
            'archetype': lore.get('archetype', ''),
            'element': lore.get('element', ''),
            'mythology': lore.get('mythology', ''),
            'role_in_astrology': lore.get('role_in_astrology', ''),
            'body_parts': lore.get('body_parts', ''),
            'rules': lore.get('rules', ''),
            'exalts_in': lore.get('exalts_in', ''),
            'debilitates_in': lore.get('debilitates_in', ''),
            'friends': lore.get('friends', ''),
            'enemies': lore.get('enemies', ''),
        },
        'house_name': house_ed[0] if house_ed else '',
        'house_meaning': house_ed[1] if house_ed else '',
        'house_text': house_text,
        'briefing': briefing,
    }


def build_llm_prompt(planet_data: Dict, language: str = 'en') -> str:
    """Build the system prompt for the Oracle to interpret this planet."""
    planet = planet_data['planet']
    briefing = planet_data['briefing']
    lore = planet_data.get('lore', {})

    lang_note = ''
    if language and language.lower() not in ('english', 'en'):
        lang_note = f'\nRespond in {language}.'

    today = datetime.now().strftime('%B %d, %Y')

    return f"""You are the voice of the stars — ancient, warm, mystical, true.
You are reading a single planet deeply for this person.

TODAY: {today}{lang_note}

{briefing}

Write THREE sections clearly separated by a blank line each:

SECTION 1 — "About {planet} in Vedic Astrology" (4-5 sentences):
Who is {planet}? Its mythology, its deity ({lore.get('deity', '')}), its archetype as "{lore.get('archetype', '')}".
Tell the story — why does this planet matter? What role does it play in the cosmic cabinet?
Make it vivid and memorable. This is the ancient wisdom a seeker deserves to hear.
Reference the mythology but keep it alive, not academic.

SECTION 2 — "What {planet} governs" (3-4 sentences):
What areas of life does this planet rule? Its domain, its significations.
Mention what it rules (signs, houses), what body parts, what life areas.
Educational but warm — a wise friend sharing knowledge.

SECTION 3 — "How {planet} shapes your life right now" (4-5 sentences):
Based on the chart data above — house placement, sign, dignity, dasha status, current transit.
Be SPECIFIC: reference the sign, house number, dignity type. Tell them what this means for their life NOW.
If the planet is the active dasha lord, emphasize that this is THEIR period.
If combust or retrograde, explain the practical effect.
End with one actionable insight.

Total: maximum 220 words. No headers, no bullets, no bold. Three flowing paragraphs separated by blank lines.
First paragraph is mythology and archetype. Second is what it governs. Third is personal and specific to this chart."""
