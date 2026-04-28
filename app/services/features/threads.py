"""
FEATURE THREADS — linear journey through all 13 features.
No dynamic routing (which caused 3-feature loops).
Clean chain: each feature always leads to the next in sequence.
"""

CHAIN = [
    'daily-vibe',
    'power-hours',
    'planet-strength',
    'soul-profile',
    'rare-traits',
    'personal-deities',
    'danger-radar',
    'year-map',
    'cosmic-novel',
    'money-calendar',
    'festivals',
    'ideal-partner',
]

# Sentence fragments — the FIRST HALF of a sentence whose
# SECOND HALF is the next feature's anchor + line.
FRAGMENTS = {
    'daily-vibe':       'and the hour this opens into —',
    'power-hours':      'and the planet behind it —',
    'planet-strength':  'and the soul it shapes —',
    'soul-profile':     'something in you is rare —',
    'rare-traits':      'and the form that protects it —',
    'personal-deities': 'because the sky is watching —',
    'danger-radar':     'and the map this year draws —',
    'year-map':         'and the story running beneath —',
    'cosmic-novel':     'a story that pays, when it pays —',
    'money-calendar':   'and the days the sky remembers —',
    'festivals':        'and the hand reaching across —',
    'ideal-partner':    'and tomorrow begins —',
}


def pick_thread(feature_id: str, context: dict = None) -> dict:
    """Always returns the next feature in the linear chain + its fragment."""
    try:
        idx = CHAIN.index(feature_id)
        next_idx = (idx + 1) % len(CHAIN)
    except ValueError:
        next_idx = 0

    next_f = CHAIN[next_idx]
    fragment = FRAGMENTS.get(feature_id, 'and what comes next —')

    return {
        'next_feature': next_f,
        'fragment': fragment,
    }
