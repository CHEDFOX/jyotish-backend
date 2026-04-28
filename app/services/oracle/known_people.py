"""
KNOWN PEOPLE STORAGE
Permanent memory of every chart a user has touched through Match Mode or Read Mode.

Each person is stored uniquely by ID, never merged by relationship label.
A user can have multiple "wives", multiple "children", multiple "friends" — 
each is its own entry.

Storage: JSON files keyed by user birth hash, in /var/www/jyotish/backend/data/known_people/
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

STORAGE_DIR = "/var/www/jyotish/backend/data/known_people"
os.makedirs(STORAGE_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# RELATIONSHIP TYPES
# ═══════════════════════════════════════════════════════════════

RELATIONSHIP_TYPES = [
    "spouse",
    "partner",
    "lover",
    "ex",
    "mother",
    "father",
    "child",
    "sibling",
    "friend",
    "colleague",
    "business_partner",
    "guru",
    "student",
    "celebrity",
    "read_only",  # Used in Read Mode when no declared relationship
    "other",
]

# Friendly labels for the frontend
RELATIONSHIP_LABELS = {
    "spouse": "Spouse",
    "partner": "Partner",
    "lover": "Lover",
    "ex": "Ex",
    "mother": "Mother",
    "father": "Father",
    "child": "Child",
    "sibling": "Sibling",
    "friend": "Friend",
    "colleague": "Colleague",
    "business_partner": "Business Partner",
    "guru": "Guru / Teacher",
    "student": "Student",
    "celebrity": "Public Figure",
    "read_only": "Read Only",
    "other": "Other",
}


# ═══════════════════════════════════════════════════════════════
# USER ID FROM BIRTH DATA
# ═══════════════════════════════════════════════════════════════

def _user_key(birth_data: Dict) -> str:
    """Generate a stable user key from birth data."""
    if not birth_data:
        return "anonymous"
    parts = [
        str(birth_data.get("year", "")),
        str(birth_data.get("month", "")),
        str(birth_data.get("day", "")),
        str(birth_data.get("hour", "")),
        str(birth_data.get("minute", "")),
        str(round(float(birth_data.get("lat", birth_data.get("latitude", 0))), 4)),
        str(round(float(birth_data.get("lng", birth_data.get("longitude", 0))), 4)),
    ]
    raw = "_".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _person_key(person_birth: Dict) -> str:
    """Generate a stable key for a person — used to detect duplicates."""
    return _user_key(person_birth)


def _storage_path(user_key: str) -> str:
    return os.path.join(STORAGE_DIR, f"{user_key}.json")


# ═══════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════

def load_known_people(birth_data: Dict) -> List[Dict]:
    """Load all known people for a user."""
    user_key = _user_key(birth_data)
    path = _storage_path(user_key)

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data.get("people", [])
    except Exception:
        return []


def save_known_people(birth_data: Dict, people: List[Dict]):
    """Save the full known people list for a user."""
    user_key = _user_key(birth_data)
    path = _storage_path(user_key)

    try:
        with open(path, "w") as f:
            json.dump({
                "user_key": user_key,
                "updated": datetime.now().isoformat(),
                "people": people,
            }, f, indent=2)
    except Exception as e:
        print(f"[KnownPeople] Save error: {e}")


def add_or_update_person(
    birth_data: Dict,
    person_name: str,
    person_birth: Dict,
    relationship_type: str,
    role_label: str = "",
    source_mode: str = "match",
) -> Dict:
    """
    Add a person to the known list, or update if they already exist.
    
    Returns the person dict with assigned ID.
    """
    people = load_known_people(birth_data)

    # Check if this person already exists (same birth data)
    person_key = _person_key(person_birth)
    existing = None
    for p in people:
        if p.get("person_key") == person_key:
            existing = p
            break

    now = datetime.now().isoformat()

    if existing:
        # Update existing — but allow new name/relationship if user provides
        if person_name:
            existing["name"] = person_name
        if relationship_type:
            existing["relationship_type"] = relationship_type
        if role_label:
            existing["role_label"] = role_label
        existing["last_referenced"] = now
        existing["mention_count"] = existing.get("mention_count", 0) + 1
        save_known_people(birth_data, people)
        return existing

    # New person
    new_id = max([p.get("id", 0) for p in people], default=0) + 1
    new_person = {
        "id": new_id,
        "name": person_name or "Unknown",
        "person_key": person_key,
        "birth_data": person_birth,
        "relationship_type": relationship_type or "other",
        "role_label": role_label or RELATIONSHIP_LABELS.get(relationship_type, "Person"),
        "added_via": source_mode,  # "match" or "read"
        "added_date": now,
        "last_referenced": now,
        "mention_count": 1,
        "conversation_summary": "",
        "is_active": True,  # User can mark past relationships as inactive
    }

    people.append(new_person)
    save_known_people(birth_data, people)
    return new_person


def get_person_by_id(birth_data: Dict, person_id: int) -> Optional[Dict]:
    """Find a known person by their ID."""
    people = load_known_people(birth_data)
    for p in people:
        if p.get("id") == person_id:
            return p
    return None


def find_people_by_name(birth_data: Dict, name: str) -> List[Dict]:
    """Find people whose name matches (case-insensitive partial)."""
    if not name:
        return []
    people = load_known_people(birth_data)
    name_lower = name.lower().strip()
    matches = []
    for p in people:
        p_name = p.get("name", "").lower()
        if name_lower in p_name or p_name in name_lower:
            matches.append(p)
    return matches


def find_people_by_relationship(birth_data: Dict, relationship: str) -> List[Dict]:
    """Find all people of a given relationship type."""
    if not relationship:
        return []
    people = load_known_people(birth_data)
    rel_lower = relationship.lower().strip()
    return [p for p in people if p.get("relationship_type", "").lower() == rel_lower]


def get_recent_people(birth_data: Dict, days: int = 30) -> List[Dict]:
    """Get people referenced in the last N days. Used by solo Oracle for cross-references."""
    people = load_known_people(birth_data)
    if not people:
        return []

    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)

    recent = []
    for p in people:
        try:
            last = datetime.fromisoformat(p.get("last_referenced", ""))
            if last >= cutoff and p.get("is_active", True):
                recent.append(p)
        except Exception:
            continue

    # Sort by most recently referenced
    recent.sort(key=lambda x: x.get("last_referenced", ""), reverse=True)
    return recent


def update_person_summary(birth_data: Dict, person_id: int, summary: str):
    """Update the conversation summary for a known person."""
    people = load_known_people(birth_data)
    for p in people:
        if p.get("id") == person_id:
            p["conversation_summary"] = summary[:500]  # Cap length
            p["last_referenced"] = datetime.now().isoformat()
            break
    save_known_people(birth_data, people)


def mark_person_inactive(birth_data: Dict, person_id: int):
    """Mark a person as inactive (e.g., past relationship). Doesn't delete."""
    people = load_known_people(birth_data)
    for p in people:
        if p.get("id") == person_id:
            p["is_active"] = False
            break
    save_known_people(birth_data, people)


def delete_person(birth_data: Dict, person_id: int):
    """Hard delete a known person."""
    people = load_known_people(birth_data)
    people = [p for p in people if p.get("id") != person_id]
    save_known_people(birth_data, people)


# ═══════════════════════════════════════════════════════════════
# CROSS-REFERENCE FOR SOLO ORACLE
# ═══════════════════════════════════════════════════════════════

def build_known_people_section(birth_data: Dict) -> str:
    """
    Build a section for the solo Oracle's briefing that lists
    recent known people. The Oracle can reference them naturally.
    """
    recent = get_recent_people(birth_data, days=30)
    if not recent:
        return ""

    lines = ["KNOWN PEOPLE IN YOUR LIFE (reference naturally if relevant):"]
    for p in recent[:6]:  # Cap at 6 most recent
        name = p.get("name", "Unknown")
        rel = p.get("role_label", p.get("relationship_type", ""))
        summary = p.get("conversation_summary", "")
        line = f"  {name} ({rel})"
        if summary:
            line += f" — last context: {summary[:100]}"
        lines.append(line)

    return "\n".join(lines)

