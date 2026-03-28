#!/usr/bin/env python3
"""
Send queued notifications via Expo Push API.
Run via cron daily at 6 AM:
  0 6 * * * cd /var/www/jyotish/backend && python3 scripts/send_notifications.py
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = Path("/var/www/jyotish/backend/data")
QUEUE_FILE = DATA_DIR / "notification_queue.jsonl"
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_notifications():
    """Send today's queued notifications."""
    if not QUEUE_FILE.exists():
        print("No queue file found.")
        return

    today = datetime.now().strftime('%Y-%m-%d')
    entries = []
    to_send = []

    with open(QUEUE_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                    if entry.get('send_at') == today and not entry.get('sent'):
                        to_send.append(entry)
                except json.JSONDecodeError:
                    pass

    if not to_send:
        print(f"No notifications to send for {today}.")
        return

    print(f"Sending {len(to_send)} notifications for {today}...")

    sent_count = 0
    for notif in to_send:
        token = notif.get('push_token', '')
        if not token:
            continue

        try:
            response = httpx.post(
                EXPO_PUSH_URL,
                json={
                    "to": token,
                    "title": notif.get('title', 'Jyotish'),
                    "body": notif.get('body', ''),
                    "sound": "default",
                    "data": {"type": "daily_insight"},
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                notif['sent'] = True
                sent_count += 1
                print(f"  Sent to {notif.get('user_id', 'unknown')}: {notif['body'][:50]}...")
            else:
                print(f"  Failed for {notif.get('user_id', 'unknown')}: {response.status_code}")

        except Exception as e:
            print(f"  Error sending to {notif.get('user_id', 'unknown')}: {e}")

    # Update queue file
    with open(QUEUE_FILE, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Done. Sent {sent_count}/{len(to_send)} notifications.")


if __name__ == '__main__':
    send_notifications()
