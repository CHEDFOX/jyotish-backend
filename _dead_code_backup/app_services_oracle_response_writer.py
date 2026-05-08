# RESPONSE WRITER
# Generates the COMPLETE response from chart data.
# LLM only adds the hook line at the end.

import random


def write_full_response(intent, briefing_data):
    verdict = briefing_data.get("verdict", "")
    facts = briefing_data.get("facts", [])
    mood = briefing_data.get("mood", "")
    is_worried = "worried" in mood.lower() if mood else False

    lines = []

    # EMPATHY LINE (only if worried)
    if is_worried:
        empathy = random.choice([
            "I understand this weighs on your mind.",
            "I can sense this has been on your mind for a while.",
            "This is clearly important to you, and I want to give you an honest answer.",
        ])
        lines.append(empathy)

    # VERDICT LINE
    v = verdict.lower()
    if "difficult" in v or "blocking" in v:
        lines.append("I have to be straightforward — this is a challenging area in your life. The patterns show real obstacles here.")
    elif "conflicted" in v:
        lines.append("This area is complicated. Your chart shows both genuine promise and real obstacles — it is possible, but not easy.")
    elif "strong" in v and ("favor" in v or "positive" in v):
        lines.append("This is one of your strongest areas. The patterns are clearly in your favor here.")
    elif "favorable" in v:
        lines.append("This area looks good for you — more working in your favor than against.")
    elif "challenged" in v:
        lines.append("This area needs your attention — there are more challenges than supports right now.")
    elif "balanced" in v:
        lines.append("This area is fairly balanced — not particularly strong or weak in your chart.")
    else:
        lines.append("Let me tell you what I see about this area of your life.")

    # DETAIL LINES (from facts)
    detail_sentences = _facts_to_sentences(facts, intent)
    lines.extend(detail_sentences[:3])

    return "\n".join(lines)


def _facts_to_sentences(facts, intent):
    sentences = []

    for fact in facts:
        if not fact:
            continue
        f = fact.lower()

        # Rising + Moon (identity)
        if "rising" in f and "moon in" in f:
            parts = fact.split(" with ")
            if len(parts) == 2:
                sentences.append("You have a " + parts[0].strip().lower() + " nature with a " + parts[1].strip().lower() + " mind — this shapes how you approach everything.")
            continue

        # Marriage facts
        if "different background" in f or "foreign" in f:
            sentences.append("Your partner is likely to come from a very different background or culture than yours — that is clearly indicated.")
        elif "beautiful" in f and "artistic" in f:
            sentences.append("When this does manifest, your partner tends to be someone beautiful and artistic.")
        elif "partner tends to be" in f:
            sentences.append(fact.rstrip(".") + " — that is what your deeper chart reveals.")
        elif "spouse lives long" in f or ("partner" in f and "longevity" in f):
            sentences.append("Your partner is likely to have good health and a long life.")
        elif "separation" in f or "severe challenge" in f:
            sentences.append("There are patterns pointing to real difficulty in sustaining this long-term — awareness and effort are key.")
        elif "spiritual" in f and "detach" in f:
            sentences.append("There is a strong spiritual pull in you that competes with settling down — this creates an inner conflict.")
        elif "delay" in f or "restriction" in f:
            sentences.append("Delays are clearly indicated here — this is not something that comes quickly or easily.")
        elif "health-related" in f and "marriage" in f:
            sentences.append("Health-related issues may create strain in your partnerships.")

        # Wealth facts
        elif "massive" in f and "wealth" in f:
            sentences.append("Your chart points to significant wealth through unconventional paths — not the typical route.")
        elif "wealth accumulation" in f:
            sentences.append("Multiple patterns support steady wealth building over your lifetime.")
        elif "very wealthy" in f:
            sentences.append("Strong prosperity indicators are present, especially through communication and family connections.")
        elif "gains from property" in f or "vehicles" in f:
            sentences.append("Property and vehicles are likely to be important sources of gains for you.")
        elif "fortune" in f and ("bold" in f or "family" in f):
            sentences.append("Fortune comes through bold, decisive action and strong family ties.")
        elif "opposition" in f or "enemies" in f:
            sentences.append("You may face competition or opposition from others, but your determination overcomes this.")

        # Health facts
        elif "long life" in f:
            sentences.append("Your longevity indicators are strong — a long, active life is supported.")
        elif "moderate longevity" in f:
            sentences.append("Your longevity is moderate — the choices you make around health genuinely matter here.")
        elif "sickly" in f or ("health" in f and "attention" in f):
            sentences.append("Your constitution needs consistent care — do not ignore what your body tells you.")

        # Chakra
        elif "sacral" in f and "blocked" in f:
            sentences.append("Your sexual and creative energy center is currently blocked, which directly explains any frustration in your intimate life.")
        elif "heart" in f and "blocked" in f:
            sentences.append("Your heart energy center is blocked right now — emotional connections feel harder than they should.")
        elif "throat" in f and "blocked" in f:
            sentences.append("Your communication energy is blocked — expressing yourself clearly feels like a struggle right now.")
        elif "confidence" in f and "blocked" in f:
            sentences.append("Your confidence center is blocked — self-doubt may be quietly holding you back.")

        # Dasha
        elif "yogakaraka" in f:
            sentences.append("The current phase of your life is actually one of the most powerful — it favors authority and fortune.")
        elif "current period" in f:
            sentences.append("The current phase of your life carries a specific energy that directly influences this.")

        # Soul chart
        elif "soul" in f and "confirms" in f:
            sentences.append("Interestingly, your deeper soul-level chart actually confirms this area positively — there is a layer of support beneath the surface.")

        # Career
        elif "leadership" in f:
            sentences.append("Leadership patterns are clearly present in your chart.")
        elif "communication" in f and "career" in f:
            sentences.append("Your career strength lies in communication and public influence.")

        # Travel
        elif "foreign land" in f or "abroad" in f:
            sentences.append("Travel to foreign lands is strongly indicated in your chart.")

        # Strong-willed
        elif "strong-willed" in f:
            sentences.append("Your strong willpower is both an asset and a challenge — it drives you forward but can create friction.")

        # Harsh speech
        elif "harsh speech" in f:
            sentences.append("Communication style may need softening — directness is a strength but can push people away.")

    # Deduplicate
    seen = set()
    unique = []
    for s in sentences:
        if s not in seen:
            unique.append(s)
            seen.add(s)

    return unique
