"""
ORACLE — USER MEMORY (v2)
Stores per-user Oracle history as a single JSON file.
Keyed by birth data hash. Never exposed to user.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from threading import Lock

MEMORY_DIR = Path("/var/www/jyotish/backend/data/memory")
MAX_OBSERVATIONS = 30
MAX_HOOKS = 15
MAX_REMEDIES = 10
MEMORY_TTL_DAYS = 180


class UserMemory:

    def __init__(self):
        self._lock = Lock()
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def _user_key(self, birth_data: Dict) -> str:
        if not birth_data:
            return None
        raw = (
            f"{birth_data.get('year', 0)}:"
            f"{birth_data.get('month', 0)}:"
            f"{birth_data.get('day', 0)}:"
            f"{birth_data.get('hour', 0)}:"
            f"{birth_data.get('minute', 0)}:"
            f"{birth_data.get('lat', 0):.2f}:"
            f"{birth_data.get('lng', 0):.2f}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _user_file(self, user_key: str) -> Path:
        return MEMORY_DIR / f"{user_key}.json"

    def _load(self, user_key: str) -> Dict:
        filepath = self._user_file(user_key)
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def _save(self, user_key: str, data: Dict):
        filepath = self._user_file(user_key)
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=None)
        except Exception as e:
            print(f"[Memory] Save error: {e}")

    # ─── RECALL: format memory for Oracle prompt ───

    def recall_formatted(self, birth_data: Dict) -> str:
        user_key = self._user_key(birth_data)
        if not user_key:
            return ""

        with self._lock:
            data = self._load(user_key)

        if not data:
            return ""

        lines = []

        # Topics already covered
        topics = data.get("topics", {})
        if topics:
            topic_list = sorted(topics.keys(), key=lambda t: topics[t].get("count", 0), reverse=True)
            lines.append("TOPICS ALREADY DISCUSSED: " + ", ".join(topic_list))

        # Observations already made (these are the key facts)
        observations = data.get("observations", [])
        if observations:
            recent = observations[-15:]
            lines.append("OBSERVATIONS ALREADY MADE (do NOT repeat these — find completely new angles):")
            for obs in recent:
                lines.append(f"  - {obs}")

        # Remedies already given
        remedies = data.get("remedies", [])
        if remedies:
            lines.append("REMEDIES ALREADY GIVEN (suggest DIFFERENT ones):")
            for r in remedies[-5:]:
                lines.append(f"  - {r}")

        # Hooks already used
        hooks = data.get("hooks", [])
        if hooks:
            lines.append("HOOKS ALREADY USED (NEVER repeat any of these):")
            for h in hooks[-8:]:
                lines.append(f"  - {h}")

        # Emotional patterns
        emotions = data.get("emotions", [])
        if emotions:
            from collections import Counter
            emotion_counts = Counter(e.get("emotion", "") for e in emotions if e.get("emotion"))
            if emotion_counts:
                top = emotion_counts.most_common(1)[0][0]
                lines.append(f"USER EMOTIONAL PATTERN: tends toward {top}")

        # Session depth
        sessions = data.get("sessions_count", 0)
        total_msgs = data.get("total_messages", 0)
        if sessions > 2:
            lines.append(f"RETURNING USER: {sessions} sessions, {total_msgs} messages. They trust you deeply. Reveal things you would only tell someone who keeps coming back.")
        elif sessions == 2:
            lines.append("SECOND SESSION: They came back. Go deeper than last time. Reference what you already know without explicitly saying 'last time'.")
        elif total_msgs > 1:
            lines.append("CONTINUING CONVERSATION: Find a new angle. Do not open the same way.")

        # Recurring topics
        recurring = data.get("recurring", [])
        if recurring:
            lines.append(f"RECURRING CONCERN: {', '.join(recurring)} — they keep asking about this. Address the UNDERLYING anxiety, not just the surface question.")

        return "\n".join(lines)

    # ─── STORE: extract and save after Oracle responds ───

    def store(self, birth_data: Dict, user_message: str,
              oracle_response: str, hook: str, intent: Dict):
        user_key = self._user_key(birth_data)
        if not user_key:
            return

        with self._lock:
            data = self._load(user_key)
            now = datetime.now()

            if data is None:
                data = {
                    "user_key": user_key,
                    "created_at": now.isoformat(),
                    "last_seen": now.isoformat(),
                    "sessions_count": 1,
                    "total_messages": 0,
                    "topics": {},
                    "observations": [],
                    "hooks": [],
                    "remedies": [],
                    "emotions": [],
                    "recurring": [],
                    "language": intent.get("language", "english"),
                }

            # Update metadata
            data["last_seen"] = now.isoformat()
            data["total_messages"] = data.get("total_messages", 0) + 1
            data["_last_message_at"] = now.isoformat()

            # Track session (new session if last message was > 30 min ago)
            last_msg = data.get("_last_message_at", "")
            if last_msg:
                try:
                    last_dt = datetime.fromisoformat(last_msg)
                    if (now - last_dt) > timedelta(minutes=30):
                        data["sessions_count"] = data.get("sessions_count", 0) + 1
                except Exception:
                    pass

            # Track topic
            topic = intent.get("primary", intent.get("primary_intent", "general"))
            if topic:
                if topic not in data["topics"]:
                    data["topics"][topic] = {"count": 0}
                data["topics"][topic]["count"] = data["topics"][topic].get("count", 0) + 1
                data["topics"][topic]["last"] = now.isoformat()

                # Detect recurring concern (asked 3+ times)
                if data["topics"][topic]["count"] >= 3 and topic not in data.get("recurring", []):
                    data.setdefault("recurring", []).append(topic)

            # Extract and store observations (key facts from response)
            new_obs = self._extract_observations(oracle_response)
            existing_obs = data.get("observations", [])
            for obs in new_obs:
                if obs not in existing_obs:
                    existing_obs.append(obs)
            data["observations"] = existing_obs[-MAX_OBSERVATIONS:]

            # Store hook
            if hook and hook.strip():
                hooks = data.get("hooks", [])
                if hook not in hooks:
                    hooks.append(hook.strip())
                data["hooks"] = hooks[-MAX_HOOKS:]

            # Extract and store remedy
            remedy = self._extract_remedy(oracle_response)
            if remedy:
                remedies = data.get("remedies", [])
                if remedy not in remedies:
                    remedies.append(remedy)
                data["remedies"] = remedies[-MAX_REMEDIES:]

            # Track emotion
            emotion = intent.get("emotion", intent.get("tone", "neutral"))
            if emotion and emotion != "neutral":
                data.setdefault("emotions", []).append({
                    "emotion": emotion,
                    "ts": now.strftime("%Y-%m-%d"),
                })
                data["emotions"] = data["emotions"][-20:]

            self._save(user_key, data)

    def _extract_observations(self, response: str) -> list:
        if not response:
            return []
        observations = []
        sentences = response.replace("\n", " ").split(". ")
        for sent in sentences:
            sent = sent.strip().rstrip(".")
            if len(sent) < 20 or len(sent) > 180:
                continue
            # Skip filler sentences
            filler = ["i understand", "i can sense", "let me", "here is",
                       "i see that", "this is a"]
            if any(sent.lower().startswith(f) for f in filler):
                continue
            # Keep sentences with substance
            substance = [
                "window", "period", "year", "month", "partner", "spouse",
                "marriage", "career", "wealth", "health", "energy",
                "strong", "weak", "promised", "delayed", "blocked",
                "planet", "remedy", "practice", "gemstone",
                "2025", "2026", "2027", "2028", "2029", "2030",
                "2031", "2032", "2033", "2034", "2035", "2036",
                "confirms", "indicates", "reveals", "hints",
                "artistic", "beautiful", "unexpected", "lasting",
            ]
            if any(kw in sent.lower() for kw in substance):
                observations.append(sent)
        return observations[:4]

    def _extract_remedy(self, response: str) -> str:
        if not response:
            return ""
        keywords = [
            "wear ", "chant ", "light ", "fast on", "practice ",
            "gemstone", "sapphire", "pearl", "ruby", "emerald",
            "coral", "hessonite", "ghee lamp", "meditation", "mantra",
        ]
        for sent in response.replace("\n", " ").split(". "):
            if any(kw in sent.lower() for kw in keywords):
                return sent.strip()[:200]
        return ""


_memory = UserMemory()


def recall_user_memory(birth_data: Dict) -> str:
    return _memory.recall_formatted(birth_data)


def store_user_memory(birth_data: Dict, user_message: str,
                      oracle_response: str, hook: str, intent: Dict):
    _memory.store(birth_data, user_message, oracle_response, hook, intent)


def cleanup_old_memories():
    cutoff = datetime.now() - timedelta(days=MEMORY_TTL_DAYS)
    try:
        for f in MEMORY_DIR.glob("*.json"):
            data = json.loads(f.read_text())
            last = datetime.fromisoformat(data.get("last_seen", "2000-01-01"))
            if last < cutoff:
                f.unlink()
    except Exception:
        pass
