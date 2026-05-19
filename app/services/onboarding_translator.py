"""
Backend-driven content for the onboarding screens.

Holds the canonical English baselines (birth + auth). For any other language,
asks the LLM to translate while keeping the poetic register intact. Results
are cached to disk so we generate each (screen, language) pair at most once
per copy revision.

Cache layout:
  data/cache/onboarding_birth/<lang>.json
  data/cache/onboarding_auth/<lang>.json
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings


BIRTH_BASELINE = {
    "combinedTitle":    "When Did You Arrive\nOn Earth?",
    "placeTitle":       "Where Did You Take\nYour First Breath?",
    "placePlaceholder": "Search city",
    "continue":         "CONTINUE",
    "labels": {
        "day":    "DAY",
        "month":  "MONTH",
        "year":   "YEAR",
        "hour":   "HOUR",
        "minute": "MINUTE",
    },
}

AUTH_BASELINE = {
    "title":            "Where the stars\nknow your name.",
    "subtitle":         "Begin where you left off,\nor begin again.",
    "emailPlaceholder": "your@email.com",
    "continue":         "CONTINUE",
    "divider":          "or",
    "apple":            "Continue with Apple",
    "google":           "Continue with Google",
    "verifyTitle":      "Check your inbox.",
    "verifyBody":       "A link to your sky has been sent.",
    "verifyResend":     "Resend",
    "errorGeneric":     "Something dimmed in the signal. Try again.",
    "terms":            "By continuing you agree to our Terms and Privacy.",
}

_CACHE_ROOT = Path(__file__).resolve().parents[2] / "data" / "cache"

_SCREENS = {
    "birth": {
        "baseline": BIRTH_BASELINE,
        "cache_dir": _CACHE_ROOT / "onboarding_birth",
        "register_hint": "poetic, minimal, soft — titles for a Vedic astrology app",
    },
    "auth": {
        "baseline": AUTH_BASELINE,
        "cache_dir": _CACHE_ROOT / "onboarding_auth",
        "register_hint": "poetic but inviting — first screen the user sees after the splash; trust + warmth",
    },
}

for cfg in _SCREENS.values():
    try:
        cfg["cache_dir"].mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

_memory_caches: dict = {key: {"en": cfg["baseline"]} for key, cfg in _SCREENS.items()}
_locks: dict = {}


def _safe_lang(language):
    return "".join(c for c in (language or "en") if c.isalnum() or c in "-_").lower() or "en"


def _normalize(obj, schema):
    if isinstance(schema, dict):
        if not isinstance(obj, dict):
            return None
        out = {}
        for k, sub in schema.items():
            if k not in obj:
                return None
            cleaned = _normalize(obj[k], sub)
            if cleaned is None:
                return None
            out[k] = cleaned
        return out
    if obj is None:
        return None
    return str(obj)


def _load_from_disk(screen, language):
    path = _SCREENS[screen]["cache_dir"] / f"{_safe_lang(language)}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return _normalize(json.load(f), _SCREENS[screen]["baseline"])
    except Exception:
        return None


def _save_to_disk(screen, language, content):
    try:
        path = _SCREENS[screen]["cache_dir"] / f"{_safe_lang(language)}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _build_prompt(screen, target_language_name):
    cfg = _SCREENS[screen]
    baseline_json = json.dumps(cfg["baseline"], ensure_ascii=False, indent=2)
    return (
        f"Translate this onboarding UI copy into {target_language_name}.\n\n"
        f"Register: {cfg['register_hint']}.\n"
        "Preserve the exact JSON shape and keys. Where '\\n' appears in a "
        "string, the translation must keep a '\\n' at a visually balanced "
        "break so the line splits nicely. Keep short labels short. Keep "
        "uppercase ACTION words uppercase if the script supports caps; "
        "otherwise use the natural emphatic short form. Do NOT translate "
        "an email-format placeholder like 'your@email.com'; keep the literal "
        "string.\n\n"
        "Return ONLY the translated JSON object. No prose, no markdown fences.\n\n"
        f"English baseline:\n{baseline_json}"
    )


async def _translate_via_llm(screen, language_code, language_name):
    if not getattr(settings, "OPENROUTER_API_KEY", None):
        return None
    prompt = _build_prompt(screen, language_name)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": "You translate UI copy. Output only valid JSON. No prose."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 700,
                    "response_format": {"type": "json_object"},
                },
            )
            if r.status_code != 200:
                print(f"[onboarding_translator] {screen} HTTP {r.status_code} for {language_code}")
                return None
            data = r.json()
            raw = data["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.lower().startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            return _normalize(json.loads(raw), _SCREENS[screen]["baseline"])
    except Exception as e:
        print(f"[onboarding_translator] {screen} error for {language_code}: {e}")
        return None


async def _get_screen_content(screen, language_code, language_name):
    lang = _safe_lang(language_code)
    cache = _memory_caches[screen]
    if lang in cache:
        return cache[lang]
    disk = _load_from_disk(screen, lang)
    if disk:
        cache[lang] = disk
        return disk
    lock = _locks.setdefault(f"{screen}:{lang}", asyncio.Lock())
    async with lock:
        if lang in cache:
            return cache[lang]
        disk = _load_from_disk(screen, lang)
        if disk:
            cache[lang] = disk
            return disk
        generated = await _translate_via_llm(screen, lang, language_name or lang)
        if generated:
            cache[lang] = generated
            _save_to_disk(screen, lang, generated)
            return generated
    return _SCREENS[screen]["baseline"]


async def get_birth_content(language_code, language_name):
    return await _get_screen_content("birth", language_code, language_name)


async def get_auth_content(language_code, language_name):
    return await _get_screen_content("auth", language_code, language_name)
