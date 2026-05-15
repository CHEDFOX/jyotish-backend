"""
PORTRAITS — Per-system, topic-sharded user memory.

Storage: data/portraits/<user_hash>/<system>/<topic>.json
Each (system, topic) gets its own packet. BPHS, KP, Western, Chinese, Mandala
keep separate memories — they have different vocabularies and methods.

API:
  load_portrait_block(birth_data, primary, secondary, system) → str
  update_user_portraits(birth_data, user_msg, oracle_reply, settings, system)
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

import httpx


PORTRAIT_DIR = Path("/var/www/jyotish/backend/data/portraits")
PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)

SUGGESTED_TOPICS = [
    "marriage", "career", "wealth", "health", "spirituality",
    "timing", "remedies", "compatibility", "travel", "family",
    "personality", "general",
]

ALWAYS_LOAD = {"personality"}

_TOPIC_ALIASES = {
    "love": "marriage", "relationship": "marriage", "spouse": "marriage",
    "partner": "marriage", "dating": "marriage",
    "job": "career", "work": "career", "profession": "career",
    "money": "wealth", "finance": "wealth", "investment": "wealth",
    "disease": "health", "illness": "health", "body": "health",
    "soul": "spirituality", "past_life": "spirituality",
    "dasha": "timing", "period": "timing", "phase": "timing",
    "remedy": "remedies", "mantra": "remedies", "gemstone": "remedies",
    "synastry": "compatibility", "match": "compatibility",
    "location": "travel", "city": "travel", "move": "travel",
}

_locks: Dict[str, Lock] = {}
_lock_lock = Lock()


def _topic_lock(user_hash: str, system: str, topic: str) -> Lock:
    key = f"{user_hash}:{system}:{topic}"
    with _lock_lock:
        if key not in _locks:
            _locks[key] = Lock()
        return _locks[key]


def _user_hash(birth_data: Dict) -> str:
    key = (
        f"{birth_data.get('year', 0)}-{birth_data.get('month', 0)}-"
        f"{birth_data.get('day', 0)}-{birth_data.get('hour', 0)}-"
        f"{birth_data.get('minute', 0)}-"
        f"{birth_data.get('lat', 0):.2f}-{birth_data.get('lng', 0):.2f}"
    )
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_")) or "general"


def normalize_topic(t: Optional[str]) -> str:
    t = _safe_name(t or "")
    if not t:
        return "general"
    return _TOPIC_ALIASES.get(t, t)


def _system_dir(user_hash: str, system: str) -> Path:
    d = PORTRAIT_DIR / user_hash / _safe_name(system)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _packet_path(user_hash: str, system: str, topic: str) -> Path:
    return _system_dir(user_hash, system) / f"{_safe_name(topic)}.json"


def _read_packet(user_hash: str, system: str, topic: str) -> Dict:
    p = _packet_path(user_hash, system, topic)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _write_packet(user_hash: str, system: str, topic: str, packet: Dict):
    p = _packet_path(user_hash, system, topic)
    try:
        p.write_text(json.dumps(packet, ensure_ascii=False, indent=None))
    except Exception as e:
        print(f"[Portraits] Write failed for {user_hash}/{system}/{topic}: {e}")


def _list_existing(user_hash: str, system: str) -> Dict[str, str]:
    sys_dir = PORTRAIT_DIR / user_hash / _safe_name(system)
    if not sys_dir.exists():
        return {}
    out = {}
    for f in sys_dir.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            portrait = (d.get("portrait") or "").strip()
            if portrait:
                out[f.stem] = portrait
        except Exception:
            pass
    return out


# ═══════════════════════════════════════════════════════════════
# READ — used by pipeline to inject context
# ═══════════════════════════════════════════════════════════════

def load_portrait_block(birth_data: Dict, primary: str,
                        secondary: Optional[str] = None,
                        system: str = "bphs") -> str:
    if not birth_data:
        return ""
    uh = _user_hash(birth_data)

    topics_to_load = {normalize_topic(primary)}
    if secondary:
        topics_to_load.add(normalize_topic(secondary))
    topics_to_load.update(ALWAYS_LOAD)

    blocks = []
    for topic in sorted(topics_to_load):
        packet = _read_packet(uh, system, topic)
        portrait = (packet.get("portrait") or "").strip()
        if portrait:
            blocks.append(f"[{topic.upper()}] {portrait}")

    if not blocks:
        return ""

    return (
        "WHAT YOU KNOW ABOUT THIS PERSON (use naturally — never announce "
        "'we discussed' or 'last time', just speak as someone who already knows them):\n"
        + "\n".join(blocks)
    )


def get_user_stats(birth_data: Dict, system: str = "bphs") -> Dict:
    if not birth_data:
        return {}
    uh = _user_hash(birth_data)
    existing = _list_existing(uh, system)
    return {"user_hash": uh, "system": system,
            "topics": list(existing.keys()), "topic_count": len(existing)}


# ═══════════════════════════════════════════════════════════════
# WRITE — LLM picks which packet(s) to update or create
# ═══════════════════════════════════════════════════════════════

UPDATE_PROMPT = """You maintain shorthand portraits of this client. One file per topic, within the {system} astrology system.

EXISTING PORTRAITS:
{existing_block}

NEW EXCHANGE:
USER: {user_message}
ORACLE: {oracle_response}

Decide where this fits:
- Continues an existing topic above → update that portrait.
- New topic → create one. Prefer a name from: {topic_list}.
- Cross-cutting personality observations → also update 'personality'.

Each portrait stays under 500 chars, dense shorthand. Match the format of the existing portraits.
If none exist yet, use this format:
S{{n}}|{{Mmm-yy}}|{{topic}}|{system}
Ask: subtopic(count,status)
Pred: event timeframe(status)
Rem: remedy(status)
Tone: what-works
Open: unresolved threads
Avoid: already-said

Return ONLY valid JSON:
{{"updates": [{{"topic": "career", "action": "update", "portrait": "..."}}]}}

Typically 1-2 updates. No prose, no markdown."""


async def update_user_portraits(
    birth_data: Dict,
    user_message: str,
    oracle_response: str,
    settings,
    system: str = "bphs",
):
    if not birth_data or not user_message or not oracle_response:
        return

    uh = _user_hash(birth_data)
    existing = _list_existing(uh, system)

    if existing:
        existing_block = "\n\n".join(f"[{t}]\n{p}" for t, p in existing.items())
    else:
        existing_block = "(no existing portraits yet for this system)"

    prompt = (UPDATE_PROMPT
              .replace("{system}", system)
              .replace("{existing_block}", existing_block)
              .replace("{user_message}", user_message[:400])
              .replace("{oracle_response}", oracle_response[:1000])
              .replace("{topic_list}", ", ".join(SUGGESTED_TOPICS)))

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content":
                            "Write dense shorthand portraits matching the format of the existing ones. 500 chars max each."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=25.0,
            )
        if resp.status_code != 200:
            return

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            s, e = cleaned.find('{'), cleaned.rfind('}')
            if s >= 0 and e > s:
                try:
                    parsed = json.loads(cleaned[s:e+1])
                except Exception:
                    return
            else:
                return
    except Exception as e:
        print(f"[Portraits] LLM failed: {e}")
        return

    updates = parsed.get("updates", []) if isinstance(parsed, dict) else []
    if not isinstance(updates, list):
        return

    now = datetime.now().isoformat()
    for u in updates:
        if not isinstance(u, dict):
            continue
        topic = normalize_topic(u.get("topic", ""))
        portrait_text = (u.get("portrait") or "").strip()[:500]
        if not topic or not portrait_text:
            continue
        action = u.get("action", "update")

        lock = _topic_lock(uh, system, topic)
        with lock:
            packet = _read_packet(uh, system, topic)
            if not packet:
                packet = {
                    "topic": topic, "system": system, "user_hash": uh,
                    "created_at": now, "message_count": 0,
                }
            packet["portrait"] = portrait_text
            packet["updated_at"] = now
            packet["message_count"] = packet.get("message_count", 0) + 1
            packet["last_action"] = action
            _write_packet(uh, system, topic, packet)
