"""
ORACLE — DATA ASSEMBLER
Fires only the methods needed for this question.
Catches errors gracefully. Compresses to ~500 words.
"""

from typing import Dict, List
from datetime import datetime


class DataAssembler:
    def __init__(self, engine):
        self.engine = engine
        self._cache = {}

    def _safe_call(self, method_name: str, *args) -> Dict:
        """Call engine method safely with caching."""
        cache_key = f"{method_name}:{str(args)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Handle method:arg format (e.g., 'predict_event:marriage')
            if ':' in method_name:
                parts = method_name.split(':')
                method = getattr(self.engine, parts[0], None)
                if method:
                    result = method(parts[1])
                else:
                    return {'error': f'Method {parts[0]} not found'}
            else:
                method = getattr(self.engine, method_name, None)
                if method:
                    result = method(*args) if args else method()
                else:
                    return {'error': f'Method {method_name} not found'}

            self._cache[cache_key] = result
            return result
        except Exception as e:
            return {'error': str(e)[:100]}

    def assemble(self, intent: Dict) -> Dict:
        """Run all methods for this intent and assemble data."""
        methods = intent.get('methods', [])
        entities = intent.get('entities', {})
        time_ctx = intent.get('time_context', None)
        primary = intent.get('primary_intent', 'general_chat')

        raw_data = {}

        # ALWAYS fire classical_rules for life event topics — this is the PRIMARY system
        life_events = {
            'marriage': 'marriage', 'career': 'career', 'wealth': 'wealth',
            'health': 'health_issue', 'children': 'childbirth', 'education': 'education',
            'travel': 'foreign', 'property': 'property', 'spiritual': 'spiritual',
            'business': 'business', 'love': 'love', 'longevity': 'longevity',
            'legal': 'career', 'daily': None, 'overview': None,
        }
        
        if primary in life_events and life_events[primary] is not None:
            event = life_events[primary]
            classical_method = f'get_classical_analysis:{event}'
            if classical_method not in methods:
                methods.insert(0, classical_method)
            # Always include dasha
            if 'get_vimshottari_dasha' not in methods:
                methods.append('get_vimshottari_dasha')

            # Wire in ALL BPHS modules we built
            # Dasha effects interpretation
            try:
                from ..predictions.dasha_effects import get_current_dasha_interpretation
                dasha_interp = get_current_dasha_interpretation(self.engine)
                if dasha_interp and 'error' not in dasha_interp:
                    raw_data['dasha_interpretation'] = dasha_interp
            except Exception:
                pass

            # Longevity — only for health/longevity questions
            if event in ('health_issue', 'longevity', 'health'):
                try:
                    from ..predictions.longevity_calc import calculate_longevity
                    longevity = calculate_longevity(self.engine)
                    if longevity:
                        raw_data['longevity'] = longevity
                except Exception:
                    pass

            # Special lagnas — for wealth questions
            if event in ('wealth', 'career', 'business'):
                try:
                    from ..predictions.special_lagnas import get_special_lagna_effects
                    special = get_special_lagna_effects(self.engine)
                    if special:
                        raw_data['special_lagnas'] = special
                except Exception:
                    pass

            # Daridra yogas — for wealth questions
            if event in ('wealth', 'business', 'career'):
                try:
                    from ..predictions.daridra_yogas import check_daridra_yogas
                    daridra = check_daridra_yogas(self.engine)
                    if daridra:
                        raw_data['daridra_yogas'] = daridra
                except Exception:
                    pass

            # Upapada — for marriage/love questions
            if event in ('marriage', 'love'):
                try:
                    from ..predictions.upapada import calculate_upapada
                    upa = calculate_upapada(self.engine)
                    if upa:
                        raw_data['upapada'] = upa
                except Exception:
                    pass

        # Fire each method
        for method_name in methods:
            # Handle special cases with entities
            if method_name == 'find_muhurta' and ':' in method_name:
                parts = method_name.split(':')
                result = self._safe_call(parts[0], parts[1])
            elif method_name == 'query_month' and time_ctx and time_ctx.get('type') == 'month':
                val = time_ctx['value']
                if isinstance(val, dict):
                    result = self._safe_call('query_month', val['year'], val['month'])
                else:
                    result = self._safe_call(method_name)
            elif method_name == 'query_time' and entities.get('date'):
                result = self._safe_call('query_time', entities['date'])
            elif method_name == 'get_varshaphal' and entities.get('year'):
                result = self._safe_call('get_varshaphal', entities['year'])
            elif method_name == 'query_year_detailed' and entities.get('year'):
                result = self._safe_call('query_year_detailed', entities['year'])
            elif method_name == 'get_annual_prediction' and entities.get('year'):
                result = self._safe_call('get_annual_prediction', entities['year'])
            elif method_name == 'explain_past_event' and entities.get('date') and entities.get('event_type'):
                result = self._safe_call('explain_past_event', entities['date'], entities['event_type'])
            elif method_name == 'analyze_hour' and entities.get('time'):
                tomorrow = entities.get('date', datetime.now().strftime('%Y-%m-%d'))
                result = self._safe_call('analyze_hour', f"{tomorrow} {entities['time']}")
            elif method_name == 'compare_locations' and entities.get('city'):
                result = self._safe_call('compare_locations')
            elif method_name == 'analyze_location' and entities.get('city'):
                result = self._safe_call('analyze_location', entities['city'])
            elif method_name == 'get_baby_names' and entities.get('gender'):
                result = self._safe_call('get_baby_names', entities['gender'])
            elif method_name == 'get_numerology' and entities.get('name'):
                result = self._safe_call('get_numerology', entities['name'])
            elif method_name == 'cast_prashna':
                topic = self._infer_prashna_topic(intent)
                result = self._safe_call('cast_prashna', topic)
            else:
                result = self._safe_call(method_name)

            if result:
                if isinstance(result, dict) and result.get('error'):
                    continue
                raw_data[method_name] = result

        # Compress into structured packet
        packet = self._compress(primary, raw_data, intent)
        return packet

    def _infer_prashna_topic(self, intent: Dict) -> str:
        """Infer prashna topic from question context."""
        msg = intent.get('original_message', '').lower()
        if any(w in msg for w in ['job', 'career', 'naukri', 'work']): return 'job'
        if any(w in msg for w in ['marry', 'marriage', 'shaadi', 'relationship']): return 'marriage'
        if any(w in msg for w in ['travel', 'abroad', 'move']): return 'travel'
        if any(w in msg for w in ['health', 'medical', 'surgery']): return 'health'
        if any(w in msg for w in ['business', 'start', 'invest']): return 'business'
        if any(w in msg for w in ['buy', 'property', 'house', 'car']): return 'property'
        if any(w in msg for w in ['exam', 'study', 'education']): return 'exam'
        return 'general'

    def _compress(self, primary_intent: str, raw_data: Dict, intent: Dict) -> Dict:
        """Compress raw data into a focused packet for the Oracle."""
        packet = {
            'intent': primary_intent,
            'tone': intent.get('emotional_tone', 'warm'),
            'is_worried': intent.get('is_worried', False),
            'sections': [],
        }

        # Build sections based on intent type
        for method_name, data in raw_data.items():
            section = self._extract_key_info(method_name, data)
            if section:
                packet['sections'].append(section)

        # Build summary text for Oracle
        packet['oracle_briefing'] = self._build_briefing(primary_intent, packet['sections'], intent)

        return packet


    def _extract_key_info(self, method_name: str, data: Dict) -> Dict:
        """Extract only the most important info from each method result."""
        if 'predict_event' in method_name:
            # Only pass FACTUAL timing data — no invented probability scores
            window = data.get('window', {})
            dasha = data.get('current_dasha', {})
            dt = data.get('double_transit', {})
            factors = data.get('positive_factors', [])
            neg = data.get('negative_factors', [])
            
            lines = [f"Event: {data.get('event')}"]
            if isinstance(dasha, dict):
                lines.append(f"Current Dasha: {dasha.get('mahadasha', '')} - {dasha.get('antardasha', '')}")
            elif isinstance(dasha, str):
                lines.append(f"Current Dasha: {dasha}")
            if isinstance(window, dict) and window.get('description'):
                lines.append(f"Time Window: {window['description']}")
            elif isinstance(window, str):
                lines.append(f"Time Window: {window}")
            if isinstance(dt, dict):
                lines.append(f"Jupiter transit: {dt.get('jupiter', 'unknown')}")
                lines.append(f"Saturn transit: {dt.get('saturn', 'unknown')}")
            elif isinstance(dt, str):
                lines.append(f"Double Transit: {dt}")
            if factors:
                lines.append(f"Supporting factors: {', '.join(str(f)[:50] for f in factors[:3])}")
            if neg:
                lines.append(f"Challenging factors: {', '.join(str(f)[:50] for f in neg[:3])}")
            return {
                'source': 'Timing (Dasha + Transit)',
                'data': '; '.join(lines),
            }

        if 'get_classical_analysis' in method_name:
            if isinstance(data, dict) and 'events' in data:
                # Full life reading
                events = data['events']
                lines = []
                for ev, info in events.items():
                    lines.append(f'{ev}: {info["summary"]}')
                return {
                    'source': 'Classical Rules (BPHS/Phaladeepika)',
                    'data': '\n'.join(lines),
                }
            else:
                # Single event — pass the raw textual rules to Oracle
                lines = [f'VERDICT: {data.get("summary", "Unknown")}']
                lines.append(f'Rules fired: {data.get("rules_fired", 0)}')
                for r in data.get('supports', []):
                    lines.append(f'  SUPPORTS: {r["text"]} [{r["source"]}]')
                for r in data.get('opposes', []):
                    lines.append(f'  OPPOSES: {r["text"]} [{r["source"]}]')
                for r in data.get('denies', []):
                    lines.append(f'  DENIES: {r["text"]} [{r["source"]}]')
                return {
                    'source': 'Classical Rules (BPHS/Phaladeepika)',
                    'data': '\n'.join(lines),
                }

        if 'kp_event_analysis' in method_name:
            # KP has its own defined system (Krishnamurti Paddhati) — keep its structure
            return {
                'source': 'KP System (Krishnamurti)',
                'data': f"Cusp Sub Lord: {data.get('cusp_sub_lord')}, "
                        f"Significators: {data.get('significators', '')}, "
                        f"Star Lord: {data.get('star_lord', '')}, "
                        f"Description: {data.get('description', '')[:100]}",
            }

        if method_name == 'get_navamsa_analysis':
            return {
                'source': 'Navamsa (D9)',
                'data': f"Marriage Strength: {data.get('marriage_strength')}, "
                        f"Spouse: {data.get('spouse_description')}, "
                        f"Venus: House {data.get('venus_placement', {}).get('house', '')}, "
                        f"Vargottama: {data.get('vargottama_planets')}",
            }

        if method_name == 'get_nadi_reading':
            kp = data.get('key_predictions', {})
            all_hints = []
            for area, hints in kp.items():
                for h in hints[:1]:
                    all_hints.append(f"{area}: {h[:80]}")
            return {
                'source': 'Nadi',
                'data': '; '.join(all_hints[:4]),
            }

        if 'validate_event' in method_name:
            return {
                'source': 'Cross-Validation',
                'data': f"Systems checked: {data.get('systems_checked')}, "
                        f"Agreeing: {data.get('systems_agreeing')}, "
                        f"Details: {'; '.join(data.get('agreements', [])[:3])}",
            }

        if method_name == 'get_yogas':
            summary = data.get('summary', {})
            return {
                'source': 'Yogas',
                'data': f"Total: {summary.get('total_yogas')}, Positive: {summary.get('positive_yogas')}, "
                        f"Negative: {summary.get('negative_yogas')}, Strong: {summary.get('strong_yogas')}",
            }

        if method_name == 'get_remedies':
            s = data.get('summary', {})
            gems = data.get('gemstone_recommendations', [])
            gem_str = gems[0]['gemstone'] if gems else 'None'
            mantra = s.get('primary_mantra', '')
            return {
                'source': 'Remedies',
                'data': f"Primary gemstone: {gem_str}, Primary mantra: {mantra[:50]}, "
                        f"Most needed: {s.get('most_needed_remedy')}",
            }

        if method_name == 'get_chart_strength':
            # Pass shadbala-based strengths without invented overall score
            strengths = data.get('planet_strengths', {})
            return {
                'source': 'Chart Strength (Shadbala)',
                'data': f"Strong planets: {data.get('strong_planets', [])}, "
                        f"Weak planets: {data.get('weak_planets', [])}",
            }

        if method_name == 'get_personality':
            moon = data.get('moon_sign', {})
            asc = data.get('ascendant', {})
            return {
                'source': 'Personality',
                'data': f"Moon: {moon.get('sign', '')} ({moon.get('traits', '')[:60]}), "
                        f"Ascendant: {asc.get('sign', '')} ({asc.get('traits', '')[:60]})",
            }

        if method_name == 'get_career_aptitude':
            # Pass career indicators without invented percentages
            top3 = data.get('top_3', [])
            lord10 = data.get('tenth_lord', '')
            occ10 = data.get('tenth_house_planets', [])
            fields = ', '.join(t.get('field', '') for t in top3)
            reasons = '; '.join(t.get('reason', '')[:60] for t in top3 if t.get('reason'))
            return {
                'source': 'Career Indicators',
                'data': f"Indicated fields: {fields}. 10th lord: {lord10}. "
                        f"Planets in 10th: {occ10}. Reasons: {reasons}",
            }

        if method_name == 'get_medical_report':
            longevity = data.get('longevity', {})
            vulns = data.get('health_vulnerabilities', [])
            vuln_texts = [v.get('source', '') + ': ' + v.get('description', '')[:50] for v in vulns[:3]]
            return {
                'source': 'Medical (Ayurvedic indicators)',
                'data': f"8th lord: {longevity.get('eighth_lord', '')}, "
                        f"Saturn strength: {longevity.get('saturn_strength', '')}, "
                        f"Vulnerabilities: {'; '.join(vuln_texts) if vuln_texts else 'None identified'}",
            }

        if method_name == 'get_realtime_dashboard':
            return {
                'source': 'Real-time',
                'data': f"Dasha: {data.get('dasha')}, Hora: {data.get('current_hora')}, "
                        f"Choghadiya: {data.get('choghadiya', {}).get('name', '')} ({data.get('choghadiya', {}).get('nature', '')}), "
                        f"Lucky color: {data.get('lucky_color')}, Advice: {data.get('quick_advice', '')}",
            }

        if method_name == 'get_varshaphal':
            overall = data.get('overall', {})
            yl = data.get('year_lord', {})
            return {
                'source': 'Varshaphal',
                'data': f"Year: {data.get('year')}, Rating: {overall.get('rating')} (Score: {overall.get('score')}), "
                        f"Year Lord: {yl.get('planet')} ({yl.get('strength')}), "
                        f"Summary: {overall.get('summary', '')[:80]}",
            }

        if 'query_time' in method_name or 'query_month' in method_name or 'query_year' in method_name:
            if 'months' in data:
                return {
                    'source': 'Year Analysis (Dasha + Transit)',
                    'data': f"Active Dasha: {data.get('active_dasha', '')}, "
                            f"Key transits: {data.get('key_transits', '')}, "
                            f"Best period: {data.get('best_month', {}).get('month', '')}, "
                            f"Challenging period: {data.get('worst_month', {}).get('month', '')}",
                }
            return {
                'source': 'Time Analysis (Dasha + Transit)',
                'data': f"Dasha: {data.get('dasha', '')}, "
                        f"Themes: {data.get('themes', [])[:3]}, "
                        f"Overall: {data.get('overall', '')}",
            }

        if method_name == 'get_transit_deep':
            ss = data.get('sade_sati', {})
            return {
                'source': 'Transit Deep',
                'data': f"Sade Sati: {ss.get('phase', 'Not Active')}, "
                        f"Retrogrades: {len(data.get('retrogrades', []))}",
            }

        if method_name == 'cast_prashna':
            answer = data.get('answer', {})
            return {
                'source': 'Prashna (Horary)',
                'data': f"Answer: {answer.get('answer', '')}, Confidence: {answer.get('confidence', '')}, "
                        f"Moon: {data.get('moon_analysis', {}).get('rashi_name', '')} ({data.get('moon_analysis', {}).get('strength', '')}), "
                        f"Summary: {data.get('summary', '')}",
            }

        if method_name == 'get_vastu':
            ld = data.get('lucky_directions', {})
            return {
                'source': 'Vastu',
                'data': f"Primary: {ld.get('primary_lucky')}, Career: {ld.get('career_direction')}, "
                        f"Wealth: {ld.get('wealth_direction')}, Sleep: {data.get('sleeping', {}).get('head_direction', '')}",
            }

        if method_name == 'get_chakra_analysis':
            return {
                'source': 'Chakra',
                'data': f"Blocked: {data.get('blocked_chakras', [])}, Focus: {data.get('primary_focus', '')}",
            }

        # Dasha interpretation
        if 'dasha_interpretation' in method_name:
            maha = data.get('mahadasha', {})
            return {
                'source': 'Dasha Interpretation (BPHS Ch.45-50)',
                'data': f"Current period: {data.get('dasha_string', '')}. "
                        f"Mahadasha theme: {maha.get('text', '')}. "
                        f"Active life themes: {', '.join(data.get('combined_themes', [])[:3])}",
            }

        # Longevity
        if 'longevity' in method_name and 'category' in str(data):
            return {
                'source': 'Longevity (BPHS Ch.40 Three-Pair)',
                'data': f"Category: {data.get('category', '').upper()} ({data.get('years', '')}). "
                        f"{data.get('description', '')}",
            }

        # Special lagnas
        if 'special_lagnas' in method_name:
            return {
                'source': 'Special Lagnas (BPHS Ch.5)',
                'data': f"{data.get('wealth_indicator', '')}. {data.get('power_indicator', '')}",
            }

        # Daridra yogas
        if 'daridra' in method_name:
            if isinstance(data, list):
                texts = [y.get('text', '') for y in data if y.get('nature') != 'neutral']
                if texts:
                    return {
                        'source': 'Poverty Yogas (BPHS Ch.42)',
                        'data': '; '.join(texts[:2]),
                    }
            return None

        # Upapada
        if 'upapada' in method_name:
            return {
                'source': 'Upapada Lagna (BPHS Ch.30)',
                'data': f"Upapada in {data.get('upapada_sign_name', '')} (H{data.get('upapada_house', '')}). "
                        f"Lord: {data.get('upapada_lord', '')}. "
                        f"Planets in Upapada: {data.get('planets_in_upapada', [])}. "
                        f"2nd from Upapada: {data.get('second_sign_name', '')} with {data.get('planets_in_2nd_from_upa', [])}",
            }

        # Handle list results
        if isinstance(data, list):
            if data:
                items = [str(d.get('name', d))[:50] if isinstance(d, dict) else str(d)[:50] for d in data[:5]]
                return {'source': method_name, 'data': '; '.join(items)}
            return None

        # Generic fallback — just return summary if available
        if isinstance(data, dict):
            summary = data.get('summary', data.get('verdict', data.get('overall', '')))
            if summary:
                s = str(summary)[:150]
                return {'source': method_name, 'data': s}

        return None

    def _build_briefing(self, intent, sections, intent_data):
        # Build clean brief matching the example format in the persona
        supports = []
        opposes = []
        denials = []
        navamsa_info = ''
        chakra_info = ''
        dasha_info = ''
        upapada_info = ''
        longevity_info = ''
        personality_info = ''

        for section in sections:
            source = section.get('source', '')
            data = section.get('data', '')

            if 'Classical Rules' in source:
                for line in data.split(chr(10)):
                    if 'SUPPORTS:' in line and chr(8594) in line:
                        supports.append(line.split(chr(8594))[1].split('[')[0].strip())
                    elif 'OPPOSES:' in line and chr(8594) in line:
                        opposes.append(line.split(chr(8594))[1].split('[')[0].strip())
                    elif 'DENIES:' in line and chr(8594) in line:
                        denials.append(line.split(chr(8594))[1].split('[')[0].strip())
            elif 'Navamsa' in source:
                navamsa_info = data
            elif 'Chakra' in source:
                chakra_info = data
            elif 'Dasha Interpretation' in source:
                dasha_info = data
            elif 'Upapada' in source:
                upapada_info = data
            elif 'Longevity' in source:
                longevity_info = data
            elif 'Personality' in source:
                personality_info = data

        s, o, d = len(supports), len(opposes), len(denials)
        if d >= 1 and o > s:
            verdict = 'Difficult area — ' + str(d) + ' blocking pattern(s), ' + str(o) + ' challenges vs ' + str(s) + ' supports'
        elif d >= 1:
            verdict = 'Conflicted — both promise (' + str(s) + ' supports) and serious challenge (' + str(o) + ' opposing, ' + str(d) + ' denial)'
        elif s >= 5 and o <= 2:
            verdict = 'Strong — ' + str(s) + ' positive indicators clearly favor this'
        elif s > o:
            verdict = 'Favorable — ' + str(s) + ' positive vs ' + str(o) + ' challenging'
        elif o > s and o >= 3:
            verdict = 'Challenged — ' + str(o) + ' difficulties vs ' + str(s) + ' supports'
        else:
            verdict = 'Balanced — ' + str(s) + ' positive, ' + str(o) + ' negative'

        facts = []
        asc_name = self.engine.ascendant.get('rashi_name', '')
        moon_name = self.engine.planets.get('Moon', {}).get('rashi_name', '')
        facts.append(asc_name + ' rising with Moon in ' + moon_name)

        for effect in supports[:2]:
            clean = self._clean_effect(effect)
            if clean:
                facts.append(clean)

        for effect in opposes[:2]:
            clean = self._clean_effect(effect)
            if clean:
                facts.append(clean)

        for effect in denials[:1]:
            clean = self._clean_effect(effect)
            if clean:
                facts.append('Warning: ' + clean)

        if navamsa_info:
            if 'Strong' in navamsa_info:
                facts.append('Soul-level chart confirms this positively')
            if 'Spouse:' in navamsa_info:
                try:
                    desc = navamsa_info.split('Spouse:')[1].split(',')[:2]
                    facts.append('Partner tends to be ' + ', '.join(d.strip() for d in desc).lower())
                except Exception:
                    pass

        if chakra_info and 'Blocked' in chakra_info:
            try:
                blocked = chakra_info.split('[')[1].split(']')[0]
                parts = [b.strip().strip("'") for b in blocked.split(',')]
                for p in parts[:1]:
                    if 'Sacral' in p: facts.append('Sexual/creative energy center is blocked')
                    elif 'Heart' in p: facts.append('Heart energy center blocked — emotional connections harder')
                    elif 'Throat' in p: facts.append('Communication energy blocked')
                    elif 'Solar' in p: facts.append('Confidence center blocked')
                    else: facts.append(p + ' energy center blocked')
            except Exception:
                pass

        if upapada_info and intent in ('marriage', 'love'):
            if 'Ketu' in upapada_info:
                facts.append('Spiritual detachment energy around marriage')

        if longevity_info and intent in ('health', 'health_issue', 'longevity'):
            if 'LONG' in longevity_info.upper(): facts.append('Long life indicated')
            elif 'MEDIUM' in longevity_info.upper(): facts.append('Moderate longevity — healthy habits matter')

        if dasha_info:
            try:
                period = dasha_info.split('Current period:')[1].split('.')[0].strip()
                theme = dasha_info.split('theme:')[1].split('.')[0].strip()
                facts.append('Current period: ' + period + ' — ' + theme)
            except Exception:
                pass

        mood_line = ''
        try:
            from ..predictions.dasha_psychology import get_psychological_state
            psych = get_psychological_state(self.engine)
            if psych and 'error' not in psych:
                mood_line = psych.get('current_mood', '').split(':')[-1].strip()
        except Exception:
            pass

        hook = self._suggest_hook(intent, chakra_info, navamsa_info, supports)

        worried = intent_data.get('is_worried', False)
        user_mood = 'Worried, needs empathy first' if worried else (mood_line if mood_line else 'Curious, be direct')

        brief = 'DATA:\n'
        brief += 'TOPIC: ' + intent.upper() + '\n'
        brief += 'VERDICT: ' + verdict + '\n'
        brief += 'KEY FACTS: ' + '. '.join(facts) + '.\n'
        brief += 'USER MOOD: ' + user_mood + '\n'
        if hook:
            brief += 'HOOK DIRECTION: ' + hook
        # Generate FULL response — LLM only adds hook
        try:
            from .response_writer import write_full_response
            briefing_data = {
                'verdict': verdict,
                'facts': facts,
                'hook': hook,
                'mood': user_mood,
                'topic': intent,
            }
            response_text = write_full_response(intent, briefing_data)
            brief += '\nRESPONSE (output this EXACTLY, then add hook):\n' + response_text
            brief += '\n\nKEY FACTS FOR HOOK: ' + '. '.join(facts[:4])
            brief += '\nHOOK DIRECTION: ' + hook
        except Exception:
            pass

        return brief

    def _clean_effect(self, effect):
        if not effect:
            return ''
        replacements = {
            'wife destroyed': 'marriage may face severe challenges',
            'wife will be sickly': 'partner may face health issues',
            'loss of wife': 'risk of separation or loss in marriage',
            'wife sickly/marriage suffers': 'marriage faces health-related challenges',
            'Ugly face': 'physical appearance challenges',
            'Eats unwholesome food': 'dietary habits need attention',
            'without learning, humiliated': 'education and reputation face challenges',
            'Fallen from position': 'career setbacks possible',
            'devoid of strength': 'weakened energy',
            'Troubled by enemies': 'faces opposition from others',
            'Short-tempered but courageous': 'strong-willed with quick temper',
        }
        clean = effect
        for old, new in replacements.items():
            clean = clean.replace(old, new)
        return clean

    def _suggest_hook(self, intent, chakra, navamsa, supports):
        if chakra and 'Sacral' in chakra:
            return 'Tease the blocked sexual energy and mention a specific mantra exists for it'
        if chakra and 'Heart' in chakra:
            return 'Tease the blocked heart energy and a practice to open it'
        if intent in ('marriage', 'love') and navamsa:
            return 'Tease what their ideal partner looks like from the soul chart'
        if intent in ('wealth', 'business') and len(supports) >= 3:
            return 'Tease the specific timing when wealth peaks'
        if intent == 'career':
            return 'Tease a hidden talent or specific career direction'
        if intent == 'health':
            return 'Tease a specific gemstone or daily practice for health'
        if intent in ('foreign', 'travel'):
            return 'Tease the specific timing window for travel'
        return 'Tease a specific mantra or timing from the chart'



def assemble_data(engine, intent: Dict) -> Dict:
    """Quick access function."""
    assembler = DataAssembler(engine)
    return assembler.assemble(intent)
