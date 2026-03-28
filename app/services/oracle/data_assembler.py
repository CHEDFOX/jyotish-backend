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

        # Classifier already tells us exactly what to calculate
        # Just ensure dasha is always included for chart questions
        needs_chart = intent.get('needs_chart', True)
        if needs_chart and 'get_vimshottari_dasha' not in methods:
            methods.append('get_vimshottari_dasha')

        if needs_chart:

            # Wire in ALL BPHS modules we built
            # Dasha effects interpretation
            try:
                from ..predictions.dasha_effects import get_current_dasha_interpretation
                dasha_interp = get_current_dasha_interpretation(self.engine)
                if dasha_interp and 'error' not in dasha_interp:
                    raw_data['dasha_interpretation'] = dasha_interp
            except Exception:
                pass

            # TIME-SPECIFIC calculations
            # Extract year and month from oracle_instruction or original message
            oracle_inst = intent.get('oracle_instruction', '')
            orig_msg = intent.get('original_message', '').lower()
            combined_text = oracle_inst + ' ' + orig_msg
            import re
            
            year_match = re.search(r'20[2-3][0-9]', combined_text)
            
            # Try to extract month
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12,
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                'diwali': 10, 'holi': 3, 'navratri': 10,
            }
            target_month = 6  # default mid-year
            for mname, mnum in month_map.items():
                if mname in combined_text.lower():
                    target_month = mnum
                    break
            
            # Try to extract day
            day_match = re.search(r'([1-9]|[12][0-9]|3[01])\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)', combined_text.lower())
            target_day = 15  # default mid-month
            if day_match:
                target_day = int(day_match.group(1))
            
            # Also check "next month", "next week", "this weekend" etc
            from datetime import datetime as dt_class, timedelta
            if 'next month' in orig_msg:
                future = dt_class.now() + timedelta(days=30)
                year_match = True  # force trigger
                target_year_val = future.year
                target_month = future.month
                target_day = 15
            elif 'next week' in orig_msg or 'next monday' in orig_msg:
                future = dt_class.now() + timedelta(days=7)
                year_match = True
                target_year_val = future.year
                target_month = future.month
                target_day = future.day
            elif 'this weekend' in orig_msg:
                days_until_sat = (5 - dt_class.now().weekday()) % 7
                future = dt_class.now() + timedelta(days=max(days_until_sat, 1))
                year_match = True
                target_year_val = future.year
                target_month = future.month
                target_day = future.day
            
            if year_match:
                if isinstance(year_match, bool):
                    target_year = target_year_val
                else:
                    target_year = int(year_match.group())
                
                # For year queries — calculate dasha at MULTIPLE points
                is_year_query = 'year' in orig_msg or str(target_year) in orig_msg
                
                if is_year_query and target_month == 6:  # Default month means full year query
                    # Calculate dasha at 4 quarters
                    try:
                        quarters = []
                        for qm in [1, 4, 7, 10]:
                            qd = self.engine.get_dasha_for_date(dt_class(target_year, qm, 15))
                            quarters.append(f"Q{(qm//3)+1}({['Jan','Apr','Jul','Oct'][[1,4,7,10].index(qm)]}): {qd.get('dasha_string', '')}")
                        raw_data['year_dasha'] = {'dasha_string': ' | '.join(quarters)}
                    except Exception:
                        pass
                    
                    # Also run classical rules for key life areas
                    for event in ['career', 'wealth', 'health', 'marriage']:
                        try:
                            cr = self.engine.get_classical_analysis(event)
                            if cr and cr.get('rules_fired', 0) > 0:
                                raw_data[f'year_{event}'] = cr
                        except Exception:
                            pass
                else:
                    # Specific date query — single dasha point
                    try:
                        target_date = dt_class(target_year, target_month, min(target_day, 28))
                        year_dasha = self.engine.get_dasha_for_date(target_date)
                        if year_dasha:
                            raw_data['year_dasha'] = year_dasha
                    except Exception:
                        pass
                
                # Varshaphal (annual prediction)
                try:
                    varshaphal = self.engine.get_varshaphal(target_year)
                    if varshaphal:
                        raw_data['varshaphal'] = varshaphal
                except Exception:
                    pass
            
            # Future transits — always useful for timing
            if 'transits' in str(intent.get('calculations', [])) or 'next' in intent.get('original_message', '').lower() or year_match:
                try:
                    future = self.engine.get_future_transits()
                    if future:
                        raw_data['future_transits'] = future
                except Exception:
                    pass

            # DELIVERY DATA — when classifier requests specific calculations
            calculations = intent.get('calculations', [])
            
            # Mantra delivery
            if 'remedies' in calculations or primary in ('mantra', 'remedies'):
                try:
                    mantra_data = self.engine.get_dynamic_mantra()
                    if mantra_data:
                        raw_data['mantra'] = mantra_data
                except Exception:
                    pass
                try:
                    remedy_data = self.engine.get_remedies()
                    if remedy_data:
                        raw_data['full_remedies'] = remedy_data
                except Exception:
                    pass

            # Numerology delivery — always fire both
            if 'numerology' in calculations or primary in ('numerology',) or 'get_numerology' in str(methods) or 'get_lucky_numbers' in str(methods):
                try:
                    lucky = self.engine.get_lucky_numbers()
                    if lucky:
                        raw_data['lucky_numbers'] = lucky
                except Exception:
                    pass
                try:
                    num_data = self.engine.get_numerology()
                    if num_data:
                        raw_data['numerology'] = num_data
                except Exception:
                    pass

            # DEFINITIVE YES/NO DATA — for specific factual questions
            msg_lower = intent.get('original_message', '').lower()
            
            # Manglik check
            if 'manglik' in msg_lower or 'mangal' in msg_lower:
                mars_h = self.engine.planets.get('Mars', {}).get('house', 0)
                is_manglik = mars_h in [1, 4, 7, 8, 12]
                raw_data['manglik'] = {
                    'is_manglik': is_manglik,
                    'mars_house': mars_h,
                    'text': f'Mars is in house {mars_h}. Manglik dosha is {"PRESENT" if is_manglik else "NOT present"}.'
                }

            # Sade Sati check
            if 'sade sati' in msg_lower or 'sadesati' in msg_lower:
                try:
                    dash = self.engine.get_realtime_dashboard()
                    raw_data['sade_sati'] = {
                        'status': dash.get('sade_sati', 'Unknown'),
                        'text': f'Sade Sati is {dash.get("sade_sati", "Unknown")}.'
                    }
                except Exception:
                    pass

            # Kaal Sarp check
            if 'kaal sarp' in msg_lower or 'kalsarp' in msg_lower or 'kal sarp' in msg_lower:
                rahu_h = self.engine.planets.get('Rahu', {}).get('house', 0)
                ketu_h = self.engine.planets.get('Ketu', {}).get('house', 0)
                all_h = [self.engine.planets[p].get('house', 0) for p in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']]
                if rahu_h < ketu_h:
                    has_ksp = all(rahu_h <= h <= ketu_h for h in all_h)
                else:
                    has_ksp = all(h >= rahu_h or h <= ketu_h for h in all_h)
                raw_data['kaal_sarp'] = {
                    'has_kaal_sarp': has_ksp,
                    'rahu_house': rahu_h,
                    'ketu_house': ketu_h,
                    'text': f'Kaal Sarp Dosh is {"PRESENT" if has_ksp else "NOT present"}. Rahu in H{rahu_h}, Ketu in H{ketu_h}.'
                }

            # Color/daily query
            if 'color' in msg_lower or 'colour' in msg_lower or 'wear today' in msg_lower:
                try:
                    cmf = self.engine.get_color_metal_food()
                    raw_data['color_today'] = cmf
                except Exception:
                    pass

            # Vastu/direction query
            if 'vastu' in msg_lower or 'direction' in msg_lower or 'facing' in msg_lower:
                try:
                    vastu = self.engine.get_vastu()
                    raw_data['vastu'] = vastu
                except Exception:
                    pass

            # Best time / peak period queries
            time_words = ['best time', 'great time', 'peak', 'best year', 'best period', 'when will things improve', 'when will my luck', 'kab achcha', 'sabse achcha']
            if any(tw in msg_lower for tw in time_words):
                try:
                    timeline = self.engine.get_life_timeline()
                    raw_data['life_timeline'] = timeline
                except Exception:
                    pass

            # Current dasha explicit query
            if 'current dasha' in msg_lower or 'my dasha' in msg_lower or 'mera dasha' in msg_lower:
                try:
                    dasha = self.engine.get_vimshottari_dasha()
                    raw_data['explicit_dasha'] = {
                        'dasha_string': dasha.get('dasha_string', ''),
                        'mahadasha': dasha.get('mahadasha', {}),
                        'antardasha': dasha.get('antardasha', {}),
                    }
                except Exception:
                    pass

            # Gemstone delivery
            if primary in ('gemstone',):
                try:
                    remedy_data = self.engine.get_remedies()
                    if remedy_data and 'gemstone_recommendations' in remedy_data:
                        raw_data['gemstone'] = remedy_data['gemstone_recommendations']
                except Exception:
                    pass

            # Chakra
            if 'chakra' in calculations:
                try:
                    chakra = self.engine.get_chakra_analysis()
                    if chakra:
                        raw_data['chakra'] = chakra
                except Exception:
                    pass

            # Longevity — only for health/longevity questions
            if primary in ('health_issue', 'longevity', 'health'):
                try:
                    from ..predictions.longevity_calc import calculate_longevity
                    longevity = calculate_longevity(self.engine)
                    if longevity:
                        raw_data['longevity'] = longevity
                except Exception:
                    pass

            # Special lagnas — for wealth questions
            if primary in ('wealth', 'career', 'business'):
                try:
                    from ..predictions.special_lagnas import get_special_lagna_effects
                    special = get_special_lagna_effects(self.engine)
                    if special:
                        raw_data['special_lagnas'] = special
                except Exception:
                    pass

            # Daridra yogas — for wealth questions
            if primary in ('wealth', 'business', 'career'):
                try:
                    from ..predictions.daridra_yogas import check_daridra_yogas
                    daridra = check_daridra_yogas(self.engine)
                    if daridra:
                        raw_data['daridra_yogas'] = daridra
                except Exception:
                    pass

            # Upapada — for marriage/love questions
            if primary in ('marriage', 'love'):
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
            highlights = data.get('highlights', [])
            if highlights:
                pos = [y for y in highlights if not y.get('is_negative', False)]
                neg = [y for y in highlights if y.get('is_negative', False)]
                yoga_lines = []
                for y in highlights:
                    yoga_lines.append(f"{y.get('name','')}: {y.get('effects','')} ({'NEGATIVE' if y.get('is_negative') else 'POSITIVE'}, {y.get('strength','')})")
                return {
                    'source': 'Yogas',
                    'data': f"Total: {len(highlights)}, Positive: {len(pos)}, Negative: {len(neg)}. " + '; '.join(yoga_lines),
                }
            return {
                'source': 'Yogas',
                'data': 'No significant yogas found.',
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


        # ── YEAR OVERVIEW HANDLERS ──
        
        if method_name.startswith('year_') and method_name != 'year_dasha':
            area = method_name.replace('year_', '')
            if isinstance(data, dict):
                summary = data.get('summary', '')
                supports = len(data.get('supports', []))
                opposes = len(data.get('opposes', []))
                top_supports = [r.get('text', '')[:60] for r in data.get('supports', [])[:2]]
                top_opposes = [r.get('text', '')[:60] for r in data.get('opposes', [])[:2]]
                lines = [f'{area.upper()}: {summary}']
                if top_supports:
                    lines.append('Supports: ' + '; '.join(top_supports))
                if top_opposes:
                    lines.append('Challenges: ' + '; '.join(top_opposes))
                return {
                    'source': f'Year {area.title()} Outlook',
                    'data': '. '.join(lines),
                }
            return None

        # ── TIME-SPECIFIC HANDLERS ──
        
        if method_name == 'year_dasha':
            if isinstance(data, dict):
                return {
                    'source': 'Year Dasha',
                    'data': f"Dasha for that period: {data.get('dasha_string', '')}",
                }
            return None

        if method_name == 'varshaphal':
            if isinstance(data, dict):
                muntha = data.get('muntha', {})
                year_lord = data.get('year_lord', '')
                return {
                    'source': 'Varshaphal (Annual)',
                    'data': f"Year lord: {year_lord}. Muntha: {muntha}. Solar return: {data.get('solar_return', '')}",
                }
            return None

        if method_name == 'future_transits':
            if isinstance(data, dict):
                transits = data.get('major_transits', {})
                lines = []
                for planet, moves in transits.items():
                    if isinstance(moves, list):
                        for m in moves[:2]:
                            if isinstance(m, dict):
                                lines.append(f"{planet}: {m.get('from_rashi','')} to {m.get('to_rashi','')} on {m.get('date','')}")
                return {
                    'source': 'Future Transits',
                    'data': '. '.join(lines[:6]),
                }
            return None

        if method_name == 'life_timeline':
            if isinstance(data, dict):
                best = data.get('best_year', {})
                worst = data.get('most_challenging', {})
                timeline = data.get('timeline', [])
                lines = []
                lines.append(f"BEST PERIOD: {best.get('year', '')} — {best.get('theme', '')}")
                lines.append(f"MOST CHALLENGING: {worst.get('year', '')} — {worst.get('theme', '')}")
                for yr in timeline[:5]:
                    lines.append(f"{yr.get('year', '')}: {yr.get('primary_theme', '')}")
                return {
                    'source': 'Life Timeline',
                    'data': '. '.join(lines),
                }
            return None

        # ── DEFINITIVE DATA HANDLERS ──
        
        if method_name == 'manglik':
            if isinstance(data, dict):
                return {'source': 'Manglik Check', 'data': data.get('text', '')}
            return None

        if method_name == 'sade_sati':
            if isinstance(data, dict):
                return {'source': 'Sade Sati', 'data': data.get('text', '')}
            return None

        if method_name == 'kaal_sarp':
            if isinstance(data, dict):
                return {'source': 'Kaal Sarp', 'data': data.get('text', '')}
            return None

        if method_name == 'color_today':
            if isinstance(data, dict):
                return {
                    'source': 'Color Today',
                    'data': f"Wear: {data.get('wear_color', '')}. Metal: {data.get('wear_metal', '')}. Eat: {data.get('eat', '')}. Dasha boost: {data.get('dasha_boost_color', '')}. Gem of day: {data.get('gem_of_the_day', '')}."
                }
            return None

        if method_name == 'vastu':
            if isinstance(data, dict):
                dirs = data.get('lucky_directions', {})
                sleeping = data.get('sleeping', {})
                return {
                    'source': 'Vastu',
                    'data': f"Primary lucky: {dirs.get('primary_lucky', '')}. Career direction: {dirs.get('career_direction', '')}. Wealth direction: {dirs.get('wealth_direction', '')}. Sleep head: {sleeping.get('head_direction', '')}. Avoid: {sleeping.get('avoid', '')}."
                }
            return None

        if method_name == 'explicit_dasha':
            if isinstance(data, dict):
                maha = data.get('mahadasha', {})
                antar = data.get('antardasha', {})
                return {
                    'source': 'Current Dasha',
                    'data': f"Full dasha: {data.get('dasha_string', '')}. Mahadasha: {maha.get('lord', '')} (ends {maha.get('end_date', '')}). Antardasha: {antar.get('lord', '')} (ends {antar.get('end_date', '')})."
                }
            return None

        # ── DELIVERY DATA HANDLERS ──
        
        if method_name == 'mantra':
            if isinstance(data, dict):
                return {
                    'source': 'Mantra',
                    'data': data,
                }
            return None

        if method_name == 'lucky_numbers':
            if isinstance(data, dict):
                return {
                    'source': 'Lucky Numbers',
                    'data': data,
                }
            return None

        if method_name == 'numerology':
            if isinstance(data, dict):
                return {
                    'source': 'Numerology',
                    'data': data,
                }
            return None

        if method_name == 'full_remedies':
            if isinstance(data, dict):
                return {
                    'source': 'Full Remedies',
                    'data': data,
                }
            return None

        if method_name == 'gemstone':
            return {
                'source': 'Gemstone',
                'data': data,
            }

        if method_name == 'chakra':
            if isinstance(data, dict):
                return {
                    'source': 'Chakra',
                    'data': data,
                }
            return None

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

        # Extract delivery data directly from sections
        delivery_data = {}
        for section in sections:
            source = section.get('source', '')
            data = section.get('data', '')
            src_lower = source.lower()
            
            if 'mantra' in src_lower and 'dynamic' not in src_lower:
                delivery_data['mantra'] = data
            elif 'lucky' in src_lower:
                delivery_data['lucky_numbers'] = data
            elif 'full remedies' in src_lower or ('remedies' in src_lower and 'gemstone' not in src_lower):
                delivery_data['remedies'] = data
            elif 'numerology' in src_lower:
                delivery_data['numerology'] = data
            elif 'gemstone' in src_lower:
                delivery_data['gemstone'] = data

        # Time-specific data
        year_dasha_info = ''
        varshaphal_info = ''
        transit_info = ''

        definitive_data = {}
        for section in sections:
            source = section.get('source', '')
            data = section.get('data', '')
            
            if 'Year Dasha' in source:
                year_dasha_info = data if isinstance(data, str) else str(data)
            elif 'Varshaphal' in source:
                varshaphal_info = data if isinstance(data, str) else str(data)
            elif 'Future Transit' in source:
                transit_info = data if isinstance(data, str) else str(data)

            # Catch-all for definitive/delivery sources not handled elsewhere
            if source in ('Manglik Check', 'Sade Sati', 'Kaal Sarp', 'Color Today', 'Vastu', 'Current Dasha'):
                if isinstance(data, str) and data:
                    definitive_data[source] = data

            # Yoga data
            if source == 'Yogas' and isinstance(data, str) and 'Total' in data:
                definitive_data['yogas'] = data

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

        # Always add accurate dasha dates
        try:
            dasha_data = self.engine.get_vimshottari_dasha()
            maha = dasha_data.get('mahadasha', {})
            antar = dasha_data.get('antardasha', {})
            from datetime import datetime as dt_class
            current_d = self.engine.get_dasha_for_date(dt_class.now())
            facts.append('DASHA DATES: Mahadasha ' + str(maha.get('lord', '')) + ' ends ' + str(maha.get('end', ''))[:10] + '. Antardasha ' + str(antar.get('lord', '')) + ' ends ' + str(antar.get('end', ''))[:10] + '. Current: ' + str(current_d.get('dasha_string', '')))
        except Exception:
            pass

        # Always add planet positions for accuracy
        try:
            placements = []
            for p in ['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn','Rahu','Ketu']:
                planet = self.engine.planets.get(p, {})
                h = planet.get('house', '?')
                r = planet.get('rashi_name', '?')
                retro = ' (R)' if planet.get('retrograde', False) else ''
                combust = ' (COMBUST)' if planet.get('combust', False) else ''
                placements.append(f'{p}:H{h}-{r}{retro}{combust}')
            facts.append('PLANET POSITIONS: ' + ', '.join(placements))
        except Exception:
            pass

        # Add nakshatra data
        try:
            nak = self.engine.get_nakshatra_profile()
            moon_nak = nak.get('moon_profile', {})
            facts.append('NAKSHATRA: Moon in ' + str(moon_nak.get('nakshatra', '')) + ' Pada ' + str(moon_nak.get('pada', '')) + ', Ruler: ' + str(moon_nak.get('ruler', '')) + ', Deity: ' + str(moon_nak.get('deity', '')) + ', Symbol: ' + str(moon_nak.get('symbol', '')))
        except Exception:
            pass

        # DIRECT injection of year outlook and varshaphal from sections
        for section in sections:
            src = section.get('source', '')
            dat = section.get('data', '')
            
            if src.startswith('year_') and src != 'year_dasha':
                area = src.replace('year_', '').upper()
                if isinstance(dat, dict):
                    facts.insert(0, area + ' OUTLOOK: ' + str(dat.get('summary', str(dat)[:100])))
                elif isinstance(dat, str):
                    facts.insert(0, area + ' OUTLOOK: ' + dat[:150])
            
            if src == 'Life Timeline':
                if isinstance(dat, str):
                    facts.insert(0, 'LIFE TIMELINE: ' + dat[:300])

            if src == 'varshaphal' or src == 'Varshaphal':
                if isinstance(dat, dict):
                    facts.insert(0, 'ANNUAL FORECAST: ' + str(dat.get('rating', '')) + '. ' + str(dat.get('summary', '')))
                elif isinstance(dat, str):
                    facts.insert(0, 'ANNUAL FORECAST: ' + dat[:150])

        # Add vargottama planets
        try:
            nav = self.engine.get_navamsa_analysis()
            vargo = nav.get('vargottama_planets', [])
            if vargo:
                facts.append('VARGOTTAMA PLANETS: ' + ', '.join(vargo) + ' (same sign in birth and navamsa chart)')
            else:
                facts.append('VARGOTTAMA: None')
        except Exception:
            pass
        # Inject definitive data
        for dk, dv in definitive_data.items():
            if isinstance(dv, str) and dv:
                facts.insert(0, "DEFINITIVE: " + dv)
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

        # Mantra data
        mantra_data = ''
        for section in sections:
            src = section.get('source', '')
            dat = section.get('data', '')
            if 'mantra' in src.lower() and 'dynamic' not in src.lower():
                mantra_data = dat

        # Lucky numbers data
        lucky_data = ''
        for section in sections:
            src = section.get('source', '')
            dat = section.get('data', '')
            if 'lucky_numbers' in src.lower():
                lucky_data = dat

        # Gemstone data
        gemstone_data = ''
        for section in sections:
            src = section.get('source', '')
            dat = section.get('data', '')
            if 'gemstone' in src.lower() or 'full_remedies' in src.lower():
                gemstone_data = dat

        # Add delivery data to facts
        if mantra_data:
            try:
                import json
                if isinstance(mantra_data, str):
                    md = json.loads(mantra_data) if mantra_data.startswith('{') else {}
                else:
                    md = mantra_data
                if isinstance(md, dict):
                    pm = md.get('primary_mantra', '')
                    pp = md.get('primary_planet', '')
                    reason = md.get('reason', '')
                    count = md.get('count', 108)
                    if pm:
                        facts.append(f'Mantra: {pm} (for {pp}, {reason}). Chant {count} times')
            except Exception:
                pass

        if lucky_data:
            try:
                import json
                if isinstance(lucky_data, str):
                    ld = json.loads(lucky_data) if lucky_data.startswith('{') else {}
                else:
                    ld = lucky_data
                if isinstance(ld, dict):
                    mulank = ld.get('mulank', '')
                    bhagyank = ld.get('bhagyank', '')
                    lucky_digits = ld.get('lucky_single_digits', [])
                    avoid = ld.get('avoid_numbers', [])
                    if lucky_digits:
                        facts.append(f'Lucky numbers: {lucky_digits}. Birth number: {mulank}. Destiny number: {bhagyank}. Avoid: {avoid}')
            except Exception:
                pass

        if gemstone_data:
            try:
                import json
                if isinstance(gemstone_data, str):
                    gd = json.loads(gemstone_data) if gemstone_data.startswith('{') else {}
                else:
                    gd = gemstone_data
                if isinstance(gd, list) and len(gd) > 0:
                    g = gd[0]
                    facts.append(f"Primary gemstone: {g.get('gemstone', '')} for {g.get('planet', '')}. Wear on {g.get('finger', '')} on {g.get('day_to_wear', '')}. Weight: {g.get('weight', '')}. Metal: {g.get('metal', '')}")
                elif isinstance(gd, dict) and 'gemstone_recommendations' in gd:
                    recs = gd['gemstone_recommendations']
                    if recs:
                        g = recs[0]
                        facts.append(f"Primary gemstone: {g.get('gemstone', '')} for {g.get('planet', '')}. Wear on {g.get('finger', '')} on {g.get('day_to_wear', '')}. Weight: {g.get('weight', '')}. Metal: {g.get('metal', '')}")
            except Exception:
                pass

        # Add time-specific data to facts — INSERT AT TOP so LLM sees them first
        if transit_info:
            facts.insert(0, 'KEY TRANSITS: ' + transit_info)
        if varshaphal_info:
            facts.insert(0, 'ANNUAL PREDICTION: ' + varshaphal_info)
        if year_dasha_info:
            facts.insert(0, 'FOR THAT PERIOD DASHA IS: ' + year_dasha_info + ' — USE THIS, not current dasha')

        hook = self._suggest_hook(intent, chakra_info, navamsa_info, supports)

        worried = intent_data.get('is_worried', False)
        user_mood = 'Worried, needs empathy first' if worried else (mood_line if mood_line else 'Curious, be direct')

        # Add delivery data to facts if present
        if delivery_data.get('mantra'):
            md = delivery_data['mantra']
            if isinstance(md, dict):
                facts.append('EXACT MANTRA: ' + md.get('primary_mantra', '') + ' (for ' + md.get('primary_planet', '') + ', ' + md.get('reason', '') + '). Chant ' + str(md.get('count', 108)) + ' times. Best time: ' + md.get('best_time', 'morning'))
                if md.get('day_mantra') and md.get('day_mantra') != md.get('primary_mantra'):
                    facts.append('DAY MANTRA: ' + md.get('day_mantra', '') + ' (for ' + md.get('day_planet', '') + ')')
            elif isinstance(md, str):
                facts.append('MANTRA DATA: ' + md[:200])

        if delivery_data.get('lucky_numbers'):
            ld = delivery_data['lucky_numbers']
            if isinstance(ld, dict):
                facts.append('EXACT LUCKY NUMBERS: ' + str(ld.get('lucky_single_digits', [])) + '. Birth number (Mulank): ' + str(ld.get('mulank', '')) + '. Destiny number (Bhagyank): ' + str(ld.get('bhagyank', '')) + '. Avoid: ' + str(ld.get('avoid_numbers', [])))
            elif isinstance(ld, str):
                facts.append('LUCKY DATA: ' + ld[:200])

        if delivery_data.get('numerology'):
            nd = delivery_data['numerology']
            if isinstance(nd, dict):
                facts.append('NUMEROLOGY: ' + nd.get('summary', ''))

        if delivery_data.get('gemstone'):
            gd = delivery_data['gemstone']
            if isinstance(gd, list) and len(gd) > 0:
                g = gd[0]
                facts.append('EXACT GEMSTONE: ' + str(g.get('gemstone', '')) + ' for ' + str(g.get('planet', '')) + '. Finger: ' + str(g.get('finger', '')) + '. Day: ' + str(g.get('day_to_wear', '')) + '. Weight: ' + str(g.get('weight', '')) + '. Metal: ' + str(g.get('metal', '')) + '. Mantra: ' + str(g.get('mantra_while_wearing', '')))
                if len(gd) > 1:
                    g2 = gd[1]
                    facts.append('SECONDARY GEMSTONE: ' + str(g2.get('gemstone', '')) + ' for ' + str(g2.get('planet', '')))

        if delivery_data.get('remedies'):
            rd = delivery_data['remedies']
            if isinstance(rd, dict):
                gems = rd.get('gemstone_recommendations', [])
                if gems and len(gems) > 0:
                    g = gems[0]
                    facts.append('EXACT GEMSTONE: ' + g.get('gemstone', '') + ' for ' + g.get('planet', '') + '. Finger: ' + g.get('finger', '') + '. Day: ' + g.get('day_to_wear', '') + '. Weight: ' + g.get('weight', '') + '. Metal: ' + g.get('metal', '') + '. Mantra while wearing: ' + g.get('mantra_while_wearing', ''))
                    if len(gems) > 1:
                        g2 = gems[1]
                        facts.append('SECONDARY GEMSTONE: ' + g2.get('gemstone', '') + ' for ' + g2.get('planet', '') + '. Finger: ' + g2.get('finger', ''))


        # ═══ BPHS ENRICHMENT — inject classical depth ═══
        try:
            # 1. Avasthas — planet states (always useful)
            avasthas = self.engine.get_avasthas()
            avastha_lines = []
            for pname, av in avasthas.items():
                bm = av.get('bala_mrita', {})
                dp = av.get('deeptadi', {})
                age = bm.get('avastha', '')
                mood = dp.get('avastha', '')
                age_desc = bm.get('description', '')
                mood_desc = dp.get('meaning', '')
                # Only report notable states (not average/neutral)
                notable = []
                if age in ('Bala', 'Mrita'):
                    notable.append(age + ' (' + age_desc + ')')
                elif age == 'Yuva':
                    notable.append('Yuva (peak strength)')
                if mood in ('Deepta', 'Swastha'):
                    notable.append(mood + ' (' + mood_desc.split(' — ')[0] + ')')
                elif mood in ('Vikala', 'Khala', 'Kopa'):
                    notable.append(mood + ' (' + mood_desc.split(' — ')[0] + ')')
                if notable:
                    avastha_lines.append(pname + ': ' + ', '.join(notable))
            if avastha_lines:
                facts.append('PLANET STATES: ' + '. '.join(avastha_lines[:5]))
        except Exception:
            pass

        try:
            # 2. Vimshopaka — definitive planet strength ranking
            vimshopaka = self.engine.get_vimshopaka()
            ranked = sorted(vimshopaka.values(), key=lambda x: x.get('vimshopaka', 0), reverse=True)
            if ranked:
                strongest = ranked[0]
                weakest = ranked[-1]
                facts.append('PLANET STRENGTH RANKING: Strongest=' + strongest['planet'] + ' (' + str(strongest['vimshopaka']) + '/20), Weakest=' + weakest['planet'] + ' (' + str(weakest['vimshopaka']) + '/20)')
        except Exception:
            pass

        try:
            # 3. Dasha Sandhi — critical for timing
            sandhi = self.engine.get_dasha_sandhi()
            if sandhi.get('in_sandhi'):
                for sd in sandhi.get('sandhi_details', []):
                    facts.insert(0, 'WARNING - DASHA SANDHI: ' + sd.get('description', '') + '. ' + sd.get('advice', ''))
        except Exception:
            pass

        try:
            # 4. Graha Yuddha — if any planets at war
            yuddha = self.engine.get_graha_yuddha()
            if yuddha.get('has_war'):
                for war in yuddha.get('wars', []):
                    facts.append('PLANETARY WAR: ' + war['planet1'] + ' vs ' + war['planet2'] + ' — ' + war['winner'] + ' wins, ' + war['loser'] + ' weakened')
        except Exception:
            pass

        try:
            # 5. Maraka — for health/longevity questions
            if intent in ('health', 'health_issue', 'longevity', 'death'):
                maraka = self.engine.get_maraka()
                facts.append('MARAKA PLANETS: ' + ', '.join(maraka.get('maraka_planets', [])) + '. Badhaka: ' + str(maraka.get('badhaka_lord', '')))
        except Exception:
            pass

        try:
            # 6. Nabhasa Yogas — for personality/life pattern questions
            if intent in ('personality', 'general', 'life', 'general_chat'):
                nabhasa = self.engine.get_nabhasa_yogas()
                for y in nabhasa.get('yogas', [])[:2]:
                    if y.get('name') != 'Samanya':
                        facts.append('PATTERN: ' + y['name'] + ' yoga — ' + y['description'])
        except Exception:
            pass

        try:
            # 7. Sannyasa — for spiritual questions
            if intent in ('spiritual', 'moksha', 'meditation', 'purpose'):
                sann = self.engine.get_sannyasa_yogas()
                for y in sann.get('yogas', [])[:2]:
                    facts.append('SPIRITUAL: ' + y['name'] + ' — ' + y['description'])
        except Exception:
            pass

        try:
            # 8. Rashi Drishti — sign aspects for key planets
            rdrishti = self.engine.get_rashi_drishti()
            asc_sign = self.engine.ascendant.get('rashi_name', '')
            for pname in ['Saturn', 'Jupiter', 'Rahu']:
                pd = rdrishti.get(pname, {})
                asp_planets = pd.get('aspects_planets', [])
                if asp_planets:
                    names = [a['planet'] for a in asp_planets[:3]]
                    facts.append(pname + ' rashi-aspects: ' + ', '.join(names))
        except Exception:
            pass


        brief = 'DATA:\n'
        brief += 'TOPIC: ' + intent.upper() + '\n'
        brief += 'VERDICT: ' + verdict + '\n'
        brief += 'KEY FACTS: ' + '. '.join(facts) + '.\n'
        brief += 'USER MOOD: ' + user_mood + '\n'
        if hook:
            brief += 'HOOK DIRECTION: ' + hook
        # Generate response skeleton — skip for delivery mode and topics with dedicated data
        is_delivery = intent_data.get('is_delivery', False)
        skip_topics = ('yogas', 'dasha', 'transit', 'numerology', 'mantra', 'gemstone', 'remedies', 'daily', 'vastu', 'personality')
        if not is_delivery and intent not in skip_topics:
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
        import random
        
        # Intent-specific hooks — deep and varied
        intent_hooks = {
            'marriage': [
                'Hint at what the soul chart reveals about their ideal partner personality',
                'Tease a specific year when marriage energy peaks in their chart',
                'Mention that the navamsa shows a surprising quality in their future spouse',
                'Hint at a compatibility factor most people overlook',
            ],
            'love': [
                'Tease what Venus placement reveals about their love pattern',
                'Hint at a timing window when new romantic energy enters their life',
                'Mention a hidden emotional pattern from their Moon placement',
            ],
            'career': [
                'Hint at a hidden talent connected to their 10th house that they havent explored',
                'Tease a specific industry or field that aligns with their chart',
                'Mention that their chart shows leadership potential activating soon',
                'Hint at a timing window for a career breakthrough',
            ],
            'wealth': [
                'Tease the specific year or transit when wealth peaks',
                'Hint at an unconventional income source their chart supports',
                'Mention a specific planet activation that triggers financial growth',
            ],
            'business': [
                'Hint at what type of business their chart naturally supports',
                'Tease a timing window for launching or expanding',
                'Mention a partnership energy that could multiply their success',
            ],
            'health': [
                'Hint at a specific gemstone that supports their weak areas',
                'Tease a daily practice tied to their ascendant for vitality',
                'Mention a chakra alignment that could shift their energy',
            ],
            'spiritual': [
                'Hint at a past life pattern visible in their chart',
                'Tease a meditation technique aligned with their nakshatra',
                'Mention that their chart shows a rare spiritual configuration',
            ],
            'children': [
                'Hint at what the 5th house reveals about their childs nature',
                'Tease a timing window for conception energy',
            ],
            'education': [
                'Hint at a subject or field their Mercury placement naturally excels in',
                'Tease a timing window for academic breakthroughs',
            ],
            'travel': [
                'Hint at specific directions or countries their chart favors',
                'Tease a transit that opens the door for permanent relocation',
            ],
            'legal': [
                'Hint at the timing when legal matters resolve favorably',
                'Tease a remedy that strengthens their 6th house advantage',
            ],
            'property': [
                'Hint at the best timing for property decisions in their chart',
                'Tease a direction (vastu) that maximizes property luck',
            ],
        }
        
        # Chakra-based hooks
        if chakra:
            if 'Sacral' in chakra:
                return 'Hint at a practice that can unblock their creative and intimate energy'
            if 'Heart' in chakra:
                return 'Tease a breathing technique tied to their Moon that opens emotional flow'
            if 'Throat' in chakra:
                return 'Hint at how their Mercury placement connects to self-expression power'
            if 'Third Eye' in chakra:
                return 'Tease an intuition practice aligned with their nakshatra'
            if 'Root' in chakra:
                return 'Hint at a grounding practice connected to their Saturn placement'
        
        # Navamsa hooks for relationship topics
        if intent in ('marriage', 'love') and navamsa:
            hooks = intent_hooks.get(intent, [])
            return random.choice(hooks) if hooks else 'Tease what the soul chart reveals about their partner'
        
        # Intent-specific
        if intent in intent_hooks:
            return random.choice(intent_hooks[intent])
        
        # Generic but varied fallbacks — NEVER just "mantra"
        generic_hooks = [
            'Hint at a specific planet activation happening in the next few months',
            'Tease a timing window where multiple positive transits converge',
            'Mention that their chart has an unusual configuration worth exploring deeper',
            'Hint at how their current dasha lord connects to an unexpected area of life',
            'Tease that their nakshatra holds a specific gift most people never discover',
            'Hint at a gemstone-planet connection that could shift their daily energy',
            'Mention a specific date range when their chart energy peaks this year',
            'Tease what their ascendant lord reveals about their life purpose',
        ]
        return random.choice(generic_hooks)



def assemble_data(engine, intent: Dict) -> Dict:
    """Quick access function."""
    assembler = DataAssembler(engine)
    return assembler.assemble(intent)
