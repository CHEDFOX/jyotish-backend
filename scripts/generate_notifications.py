#!/usr/bin/env python3
"""
Jyotish Notification System
Run via cron every 3 days at midnight:
  0 0 */3 * * cd /var/www/jyotish/backend && python3 scripts/generate_notifications.py

Sends via cron every morning at 6 AM:
  0 6 * * * cd /var/www/jyotish/backend && python3 scripts/send_notifications.py
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = Path("/var/www/jyotish/backend/data")
USERS_FILE = DATA_DIR / "push_users.jsonl"
QUEUE_FILE = DATA_DIR / "notification_queue.jsonl"


def load_users():
    """Load registered push users."""
    users = []
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        users.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return users


def generate_notification(engine, target_date, language="en"):
    """Generate one notification for a specific date from chart data."""
    from app.services.jyotish_engine import JyotishEngine

    try:
        # Get dasha for target date
        dasha = engine.get_dasha_for_date(target_date)

        # Get transits for target date
        transits = engine.get_current_transits() if hasattr(engine, 'get_current_transits') else {}

        # Get moon sign
        moon_sign = engine.planets.get('Moon', {}).get('rashi_name', 'Aries')
        ascendant = engine.planets.get('Ascendant', {}).get('rashi_name', 'Aries')

        # Determine the most important event
        mahadasha = dasha.get('mahadasha', {}).get('planet', 'Jupiter')
        antardasha = dasha.get('antardasha', {}).get('planet', 'Saturn')

        # Check for dasha transitions
        ad_end = dasha.get('antardasha', {}).get('end_date', '')
        is_transition = False
        if ad_end:
            try:
                end_dt = datetime.strptime(ad_end, '%Y-%m-%d') if isinstance(ad_end, str) else ad_end
                days_to_end = (end_dt - target_date).days
                if 0 <= days_to_end <= 3:
                    is_transition = True
            except (ValueError, TypeError):
                pass

        # Planet energy words
        energy = {
            'Sun': {'en': 'confidence and authority', 'hi': 'आत्मविश्वास और अधिकार'},
            'Moon': {'en': 'emotions and intuition', 'hi': 'भावनाएं और अंतर्ज्ञान'},
            'Mars': {'en': 'action and courage', 'hi': 'कर्म और साहस'},
            'Mercury': {'en': 'communication and learning', 'hi': 'संवाद और ज्ञान'},
            'Jupiter': {'en': 'wisdom and expansion', 'hi': 'बुद्धि और विस्तार'},
            'Venus': {'en': 'love and beauty', 'hi': 'प्रेम और सौंदर्य'},
            'Saturn': {'en': 'discipline and patience', 'hi': 'अनुशासन और धैर्य'},
            'Rahu': {'en': 'ambition and transformation', 'hi': 'महत्वाकांक्षा और परिवर्तन'},
            'Ketu': {'en': 'spirituality and detachment', 'hi': 'आध्यात्मिकता और वैराग्य'},
        }

        lang = language if language in ('en', 'hi') else 'en'

        if is_transition:
            next_ad = dasha.get('antardasha', {}).get('next_planet', antardasha)
            if lang == 'en':
                body = f"A shift in your inner cycle begins — {energy.get(next_ad, {}).get('en', 'new energy')} takes center stage."
                title = "Planetary Shift"
            else:
                body = f"आपके आंतरिक चक्र में बदलाव — {energy.get(next_ad, {}).get('hi', 'नई ऊर्जा')} केंद्र में आती है।"
                title = "ग्रह परिवर्तन"
        else:
            # Daily insight based on dasha lord
            planet_energy = energy.get(antardasha, {}).get(lang, 'growth')
            weekday = target_date.strftime('%A')

            templates_en = [
                f"{weekday} carries the energy of {planet_energy}. Move with awareness.",
                f"Your current phase favors {planet_energy}. Use this {weekday} wisely.",
                f"The stars align for {planet_energy} today. Trust the rhythm.",
                f"{planet_energy} — this is your theme for {weekday}.",
            ]
            templates_hi = [
                f"{weekday} में {planet_energy} की ऊर्जा है। जागरूकता से चलें।",
                f"आपका वर्तमान चरण {planet_energy} का समर्थन करता है।",
                f"आज {planet_energy} के लिए तारे अनुकूल हैं।",
                f"{planet_energy} — आज का विषय।",
            ]

            import random
            if lang == 'en':
                body = random.choice(templates_en)
                title = "Daily Insight"
            else:
                body = random.choice(templates_hi)
                title = "दैनिक अंतर्दृष्टि"

        return {"title": title, "body": body}

    except Exception as e:
        print(f"Error generating notification: {e}", file=sys.stderr)
        return None


def generate_all():
    """Generate 3 days of notifications for all users."""
    users = load_users()
    if not users:
        print("No users registered for push notifications.")
        return

    DATA_DIR.mkdir(exist_ok=True)

    # Load existing queue
    existing = []
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Remove old sent notifications (older than 7 days)
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    existing = [e for e in existing if e.get('send_at', '') >= cutoff]

    # Existing scheduled dates per user
    scheduled = {}
    for e in existing:
        key = e.get('user_id', '') + '_' + e.get('send_at', '')
        scheduled[key] = True

    new_entries = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for user in users:
        user_id = user.get('user_id', '')
        push_token = user.get('push_token', '')
        birth = user.get('birth_details', {})
        language = user.get('language', 'en')

        if not push_token or not birth.get('year'):
            continue

        try:
            from app.services.jyotish_engine import JyotishEngine

            engine = JyotishEngine(
                datetime(
                    int(birth['year']), int(birth['month']), int(birth['day']),
                    int(birth.get('hour', 12)), int(birth.get('minute', 0))
                ),
                float(birth.get('latitude', 28.6)),
                float(birth.get('longitude', 77.2))
            )

            for day_offset in range(3):
                target = today + timedelta(days=day_offset + 1)
                date_str = target.strftime('%Y-%m-%d')
                key = user_id + '_' + date_str

                if key in scheduled:
                    continue

                notif = generate_notification(engine, target, language)
                if notif:
                    new_entries.append({
                        'user_id': user_id,
                        'push_token': push_token,
                        'send_at': date_str,
                        'title': notif['title'],
                        'body': notif['body'],
                        'sent': False,
                    })

        except Exception as e:
            print(f"Error for user {user_id}: {e}", file=sys.stderr)
            continue

    # Write all entries
    all_entries = existing + new_entries
    with open(QUEUE_FILE, 'w') as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Generated {len(new_entries)} new notifications for {len(users)} users.")
    print(f"Total queue: {len(all_entries)} entries.")


if __name__ == '__main__':
    generate_all()
