"""
ORACLE — COMPLETE PIPELINE
Supports both sync and async classification.
"""

from datetime import datetime
from typing import Dict, Optional

from .intent_classifier import classify_intent, classify_intent_async
from .engine_cache import get_cached_engine, get_cache_stats
from .data_assembler import assemble_data
from .prompt_builder import build_oracle_prompt, build_system_prompt_only


class OraclePipeline:
    def __init__(self):
        self.conversation_history = []

    def process(self, user_message: str, birth_data: Dict = None,
                conversation_history: list = None) -> Dict:
        """Sync pipeline — uses sync intent classification."""
        start_time = datetime.now()

        # Step 1: Classify
        history = conversation_history or self.conversation_history
        intent = classify_intent(user_message, history)

        # Step 2-6: Same pipeline
        return self._complete_pipeline(user_message, birth_data, intent, start_time)

    async def process_async(self, user_message: str, birth_data: Dict = None,
                             conversation_history: list = None) -> Dict:
        """Async pipeline — uses AI intent classification."""
        start_time = datetime.now()

        # Step 1: Classify with AI
        history = conversation_history or self.conversation_history
        intent = await classify_intent_async(user_message, history)

        # Step 2-6: Same pipeline
        return self._complete_pipeline(user_message, birth_data, intent, start_time)

    def _complete_pipeline(self, user_message: str, birth_data: Dict,
                            intent: Dict, start_time: datetime) -> Dict:
        """Common pipeline after classification."""

        # Step 2: Get or create engine
        engine = None
        cache_hit = False

        if birth_data:
            birth_dt = datetime(
                birth_data['year'], birth_data['month'], birth_data['day'],
                birth_data.get('hour', 12), birth_data.get('minute', 0)
            )
            engine, cache_hit = get_cached_engine(
                birth_dt, birth_data['lat'], birth_data['lng']
            )

        # Step 3: Assemble data
        if engine:
            data_packet = assemble_data(engine, intent)
        else:
            data_packet = {
                'oracle_briefing': 'No birth data provided. Respond based on general astrology principles.',
                'sections': [],
                'intent': intent['primary_intent'],
                'tone': intent['emotional_tone'],
            }

        # Step 4: Build prompt
        system_prompt = build_oracle_prompt(intent, data_packet, user_message)

        # Step 5: Track history
        self.conversation_history.append(user_message)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        return {
            'system_prompt': system_prompt,
            'user_prompt': user_message,
            'intent': {
                'primary': intent['primary_intent'],
                'secondary': intent.get('secondary_intents', []),
                'confidence': intent['confidence'],
                'tone': intent['emotional_tone'],
                'emotion': intent.get('emotion', 'neutral'),
                'entities': intent.get('entities', {}),
                'time_context': intent.get('time_context'),
                'is_worried': intent.get('is_worried', False),
                'language': intent.get('language', 'english'),
                'translated': intent.get('translated', user_message),
                'classifier': intent.get('classifier', 'unknown'),
                'about_whom': intent.get('about_whom', 'self'),
                'relevant_houses': intent.get('relevant_houses', []),
                'follow_up_suggestions': intent.get('follow_up_suggestions', []),
                'cache_hit': intent.get('cache_hit', False),
            },
            'data_packet': data_packet,
            'cache_hit': cache_hit,
            'methods_fired': intent.get('methods', []),
            'processing_time_ms': round(elapsed),
        }


_pipeline = OraclePipeline()


def process_oracle_query(user_message: str, birth_data: Dict = None,
                          conversation_history: list = None) -> Dict:
    """Sync Oracle pipeline."""
    return _pipeline.process(user_message, birth_data, conversation_history)


async def process_oracle_query_async(user_message: str, birth_data: Dict = None,
                                      conversation_history: list = None) -> Dict:
    """Async Oracle pipeline (uses AI classification)."""
    return await _pipeline.process_async(user_message, birth_data, conversation_history)


def get_oracle_stats() -> Dict:
    return {'cache': get_cache_stats()}
