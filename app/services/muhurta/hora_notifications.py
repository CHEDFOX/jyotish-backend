"""
HORA-AWARE NOTIFICATIONS
Generates context-aware push notification content based on:
  1. Current planetary hora (which planet rules this hour)
  2. What that planet means for THIS specific user's chart
  3. What the user has been asking about (from memory)

Called by the notification cron job, not by the API directly.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

HORA_SEQUENCE = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

# Day lord (0=Monday)
DAY_LORDS = {
    0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter",
    4: "Venus", 5: "Saturn", 6: "Sun",
}

HORA_DURATIONS_MINUTES = 60  # Each hora is approximately 1 hour

PLANET_ACTIVITIES = {
    "Sun": {
        "best_for": "leadership decisions, meeting authority figures, government work, father-related matters",
        "avoid": "starting partnerships, being submissive, night activities",
        "energy": "confident, authoritative, visible",
        "notification_templates": [
            "This hour favors bold decisions. Step into your authority.",
            "The next 60 minutes carry Sun energy. Ideal for career moves.",
            "Right now favors leadership. Make that call you have been avoiding.",
            "Sun hora active. Government, authority, and visibility are amplified.",
        ],
    },
    "Moon": {
        "best_for": "emotional conversations, nurturing, travel, public dealings, mother",
        "avoid": "confrontation, aggressive decisions, legal matters",
        "energy": "receptive, intuitive, flowing",
        "notification_templates": [
            "Moon hora active. Trust your intuition right now.",
            "The next hour favors emotional conversations and connecting.",
            "Your intuitive sense is strongest right now. Listen to it.",
            "Moon energy is flowing. Good for travel and public matters.",
        ],
    },
    "Mars": {
        "best_for": "exercise, competition, surgery, property deals, courage",
        "avoid": "peace negotiations, delicate conversations, lending money",
        "energy": "aggressive, driven, physical",
        "notification_templates": [
            "Mars hora. Channel this energy into action, not arguments.",
            "High-energy hour ahead. Great for exercise and bold moves.",
            "Mars is ruling this hour. Property and competition favored.",
            "The next 60 minutes reward courage. Take the first step.",
        ],
    },
    "Mercury": {
        "best_for": "communication, writing, business deals, learning, trading",
        "avoid": "long-term commitments, emotional decisions, rest",
        "energy": "quick, analytical, communicative",
        "notification_templates": [
            "Mercury hora. Perfect for writing, calls, and business.",
            "Your communication is sharpest right now. Send that message.",
            "The next hour favors intellect. Study, trade, negotiate.",
            "Mercury energy active. Quick decisions work in your favor.",
        ],
    },
    "Jupiter": {
        "best_for": "spiritual practice, teaching, legal matters, children, finance",
        "avoid": "shortcuts, deception, trivial matters",
        "energy": "expansive, wise, fortunate",
        "notification_templates": [
            "Jupiter hora. The most auspicious hour of the day.",
            "Luck peaks in this hour. Start something meaningful.",
            "Jupiter energy active. Teaching, learning, and wisdom flow.",
            "The next 60 minutes carry grace. Use them wisely.",
        ],
    },
    "Venus": {
        "best_for": "love conversations, art, shopping, beauty, reconciliation",
        "avoid": "austerity, harsh words, arguments with partner",
        "energy": "harmonious, beautiful, pleasurable",
        "notification_templates": [
            "Venus hora. Love, beauty, and harmony are amplified.",
            "The next hour favors romance and reconciliation.",
            "Venus is active. Art, music, and beauty flow naturally.",
            "Perfect moment for that conversation about the heart.",
        ],
    },
    "Saturn": {
        "best_for": "discipline, long-term planning, organization, serving others",
        "avoid": "new beginnings, celebrations, taking risks",
        "energy": "structured, patient, grounding",
        "notification_templates": [
            "Saturn hora. Focus on structure and discipline.",
            "The next hour rewards patience and planning.",
            "Saturn energy active. Organize, plan, and build slowly.",
            "Use this hour for the hard work others avoid.",
        ],
    },
}


def get_current_hora(latitude: float = 28.6139, longitude: float = 77.209) -> Dict:
    """
    Calculate which planetary hora is currently active.
    Uses simplified equal-hour system (each hora = 1 hour).
    Day starts at sunrise (approximated as 6:00 AM local).
    """
    now = datetime.now()
    day_lord = DAY_LORDS[now.weekday()]

    # Find hora lord starting from day lord at sunrise
    # Approximate sunrise at 6:00 AM
    sunrise_hour = 6
    hours_since_sunrise = now.hour - sunrise_hour
    if hours_since_sunrise < 0:
        hours_since_sunrise += 24
        # Night horas — previous day's sequence continues
        day_lord = DAY_LORDS[(now.weekday() - 1) % 7]

    # Hora sequence starts with day lord
    day_lord_index = HORA_SEQUENCE.index(day_lord)
    hora_index = (day_lord_index + hours_since_sunrise) % 7
    hora_lord = HORA_SEQUENCE[hora_index]

    # Minutes remaining in this hora
    minutes_remaining = 60 - now.minute

    return {
        "hora_lord": hora_lord,
        "day_lord": day_lord,
        "minutes_remaining": minutes_remaining,
        "hora_info": PLANET_ACTIVITIES.get(hora_lord, {}),
        "is_day": 6 <= now.hour < 18,
        "timestamp": now.isoformat(),
    }


def generate_notification(engine=None, user_topics: list = None) -> Dict:
    """
    Generate a personalized push notification based on current hora
    and optionally the user's chart + topics of interest.
    """
    import random

    hora = get_current_hora()
    hora_lord = hora["hora_lord"]
    info = hora["hora_info"]

    # Base notification from templates
    templates = info.get("notification_templates", ["Check your cosmic alignment."])
    base_message = random.choice(templates)

    # Personalize if we have chart data
    personal_note = ""
    if engine:
        try:
            planets = engine.planets
            hora_planet_data = planets.get(hora_lord, {})
            hora_house = hora_planet_data.get("house", 0)

            if hora_house:
                house_notes = {
                    1: "This energy directly touches your sense of self.",
                    2: "This connects to your finances and family.",
                    3: "Your communication and courage are activated.",
                    4: "Home and emotional peace are in focus.",
                    5: "Creativity and romance are highlighted.",
                    6: "Health and daily routine need attention.",
                    7: "Partnerships and relationships are activated.",
                    8: "Deep transformation is at play.",
                    9: "Fortune and higher learning are favored.",
                    10: "Your career and public image are in focus.",
                    11: "Gains and social connections are amplified.",
                    12: "Spiritual growth and release are highlighted.",
                }
                personal_note = house_notes.get(hora_house, "")
        except Exception:
            pass

    # Connect to user's topics if available
    topic_hook = ""
    if user_topics:
        if hora_lord == "Venus" and "marriage" in user_topics:
            topic_hook = "This is especially relevant for what you have been asking about love."
        elif hora_lord == "Jupiter" and "career" in user_topics:
            topic_hook = "This connects to the career shifts we discussed."
        elif hora_lord == "Saturn" and "career" in user_topics:
            topic_hook = "Use this structured energy for the career planning ahead."
        elif hora_lord == "Moon" and "marriage" in user_topics:
            topic_hook = "Your emotional clarity right now affects your relationship path."

    # Build final notification
    title = hora_lord + " Hora Active"
    body = base_message
    if personal_note:
        body += " " + personal_note
    if topic_hook:
        body += " " + topic_hook

    return {
        "title": title,
        "body": body,
        "hora_lord": hora_lord,
        "best_for": info.get("best_for", ""),
        "avoid": info.get("avoid", ""),
        "minutes_remaining": hora["minutes_remaining"],
        "energy": info.get("energy", ""),
    }


def get_next_favorable_hora(target_planet: str) -> Dict:
    """When is the next hora for a specific planet?"""
    now = datetime.now()
    for hours_ahead in range(1, 25):
        future = now + timedelta(hours=hours_ahead)
        day_lord = DAY_LORDS[future.weekday()]
        sunrise_hour = 6
        hours_since_sunrise = future.hour - sunrise_hour
        if hours_since_sunrise < 0:
            hours_since_sunrise += 24
            day_lord = DAY_LORDS[(future.weekday() - 1) % 7]
        day_lord_index = HORA_SEQUENCE.index(day_lord)
        hora_index = (day_lord_index + hours_since_sunrise) % 7
        if HORA_SEQUENCE[hora_index] == target_planet:
            return {
                "planet": target_planet,
                "starts_at": future.replace(minute=0, second=0).isoformat(),
                "hours_away": hours_ahead,
            }
    return {"planet": target_planet, "starts_at": "unknown", "hours_away": -1}
