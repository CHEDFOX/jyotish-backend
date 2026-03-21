"""
DEPRECATED — Replaced by classical_rules.py

This module used invented weights (40/30/20/10 reference points).
All life event evaluation now uses ClassicalRules.
"""

from ..predictions.classical_rules import ClassicalRules
from typing import Dict


class PromiseCheck:
    """Redirects to ClassicalRules."""

    def __init__(self, engine):
        self.cr = ClassicalRules(engine)

    def evaluate(self, event: str) -> Dict:
        event_map = {
            'childbirth': 'children',
            'travel_foreign': 'foreign',
            'health_issue': 'health',
        }
        mapped = event_map.get(event, event)
        return self.cr.evaluate(mapped)
