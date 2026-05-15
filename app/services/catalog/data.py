"""
CATALOG — Single source of truth for what the frontend renders.

Section types:
  - "reading" / "chart" / "compat" / "numerology" / "special":
        Section has an `endpoint`. Frontend fetches it to get the data.
  - "content":
        Section has NO endpoint. The `content` dict is the data. Frontend
        renders it directly. Use for promo banners, editorial cards, event
        alerts, scheduled announcements, etc.

Time windows: start_date / end_date are ISO 8601 strings in UTC.
A section is hidden outside [start_date, end_date]. Either or both can be None.

Editing: this file is the live config. Edit SECTIONS, bump CATALOG_UPDATED_AT,
restart. (Frontend uses updated_at for SWR cache invalidation.)
Future: migrate to a small admin UI backed by a JSON table — same shape.

How to add a content tile:

    _section(
        id="diwali_2026",
        endpoint=None,
        group="daily",
        position=5,
        feature_kind="content",
        tile_type="banner",
        start_date="2026-10-25T00:00:00Z",
        end_date="2026-11-05T23:59:59Z",
        content={
            "title": "Diwali Muhurat",
            "body": "Lakshmi puja window: 6:42pm – 8:14pm",
            "image_url": "https://...",
            "action_label": "View muhurat",
            "action_type": "open_section",   # open_url | open_section | none
            "action_target": "panchanga",
        },
    ),
"""

from typing import List, Dict, Optional


CATALOG_VERSION = 4
CATALOG_UPDATED_AT = "2026-05-15T11:30:00Z"


GROUPS: List[Dict] = [
    {"id": "daily",          "position": 1, "i18n_key": "group.daily"},
    {"id": "charts",         "position": 2, "i18n_key": "group.charts"},
    {"id": "stories",        "position": 3, "i18n_key": "group.stories"},
    {"id": "numerology",     "position": 4, "i18n_key": "group.numerology"},
    {"id": "compatibility",  "position": 5, "i18n_key": "group.compatibility"},
    {"id": "special",        "position": 6, "i18n_key": "group.special"},
]


def _section(
    *,
    id: str,
    group: str,
    position: int,
    endpoint: Optional[str] = None,
    method: Optional[str] = "POST",
    feature_kind: str = "reading",
    tile_type: str = "card",
    requires: Optional[List[str]] = None,
    cache_ttl_seconds: int = 86400,
    i18n_key: Optional[str] = None,
    visible: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_app_version: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    content: Optional[Dict] = None,
) -> Dict:
    """Build a section entry. For content tiles set feature_kind='content'
    and pass `content={...}` with no endpoint."""
    if feature_kind == "content":
        endpoint = None
        method = None
    return {
        "id": id,
        "group": group,
        "position": position,
        "endpoint": endpoint,
        "method": method,
        "feature_kind": feature_kind,
        "tile_type": tile_type,
        "requires": requires if requires is not None else (["kundli"] if endpoint else []),
        "cache_ttl_seconds": cache_ttl_seconds,
        "i18n_key": i18n_key or f"section.{id}",
        "visible": visible,
        "start_date": start_date,
        "end_date": end_date,
        "min_app_version": min_app_version,
        "platforms": platforms,
        "content": content,
    }


SECTIONS: List[Dict] = [
    # ── DAILY ─────────────────────────────────────────────────
    _section(id="today_sky",     endpoint="/api/public/today-sky",     group="daily",  position=10, tile_type="hero",   cache_ttl_seconds=14400),
    _section(id="today_deep",    endpoint="/api/public/today-deep",    group="daily",  position=20, tile_type="card",   cache_ttl_seconds=21600),
    _section(id="the_word",      endpoint="/api/public/the-word",      group="daily",  position=30, tile_type="small",  cache_ttl_seconds=86400),
    _section(id="time_reading",  endpoint="/api/public/time-reading",  group="daily",  position=40, tile_type="card",   cache_ttl_seconds=3600),
    _section(id="panchanga",     endpoint="/api/public/panchanga",     group="daily",  position=50, tile_type="small",  cache_ttl_seconds=1800,
             method="GET", requires=["coordinates"]),

    # ── CHARTS ────────────────────────────────────────────────
    _section(id="chart_overview", endpoint="/api/public/chart-overview", group="charts", position=10, feature_kind="chart", tile_type="hero", cache_ttl_seconds=2592000),
    _section(id="core_chart",     endpoint="/api/public/core-chart",     group="charts", position=20, feature_kind="chart", tile_type="card", cache_ttl_seconds=86400),

    # ── STORIES ───────────────────────────────────────────────
    _section(id="past_life",    endpoint="/api/public/past-life",    group="stories", position=10, tile_type="hero",   cache_ttl_seconds=31536000),
    _section(id="life_story",   endpoint="/api/public/life-story",   group="stories", position=20, tile_type="card",   cache_ttl_seconds=31536000),
    _section(id="the_zoo",      endpoint="/api/public/the-zoo",      group="stories", position=30, tile_type="card",   cache_ttl_seconds=31536000),
    _section(id="four_pillars", endpoint="/api/public/four-pillars", group="stories", position=40, tile_type="card",   cache_ttl_seconds=31536000),
    _section(id="blunt_seer",   endpoint="/api/public/blunt-seer",   group="stories", position=50, tile_type="card",   cache_ttl_seconds=31536000),

    # ── NUMEROLOGY ────────────────────────────────────────────
    _section(id="core_numbers",    endpoint="/api/public/core-numbers",    group="numerology", position=10, feature_kind="numerology", tile_type="hero", cache_ttl_seconds=31536000),
    _section(id="business_name",   endpoint="/api/public/business-name",   group="numerology", position=20, feature_kind="numerology", tile_type="card", cache_ttl_seconds=86400,
             requires=["kundli", "business_name"]),
    _section(id="mobile_number",   endpoint="/api/public/mobile-number",   group="numerology", position=30, feature_kind="numerology", tile_type="card", cache_ttl_seconds=86400,
             requires=["kundli", "mobile_number"]),
    _section(id="name_correction", endpoint="/api/public/name-correction", group="numerology", position=40, feature_kind="numerology", tile_type="card", cache_ttl_seconds=86400,
             requires=["kundli", "name"]),

    # ── COMPATIBILITY ─────────────────────────────────────────
    _section(id="compatibility_hook", endpoint="/api/public/compatibility-hook", group="compatibility", position=5,  feature_kind="compat", tile_type="banner", cache_ttl_seconds=86400),
    _section(id="match",              endpoint="/api/public/match",              group="compatibility", position=10, feature_kind="compat", tile_type="hero",   cache_ttl_seconds=31536000,
             requires=["kundli", "partner"]),
    _section(id="compatibility_deep", endpoint="/api/public/compatibility-deep", group="compatibility", position=20, feature_kind="compat", tile_type="card",   cache_ttl_seconds=31536000,
             requires=["person1", "person2"]),

    # ── SPECIAL ───────────────────────────────────────────────
    _section(id="kp_horary", endpoint="/api/public/kp-horary", group="special", position=10, feature_kind="special", tile_type="card",
             cache_ttl_seconds=0, requires=["question"]),

    # ═════════════════════════════════════════════════════════
    # CONTENT TILES — backend-pushed cards, no endpoint
    # ═════════════════════════════════════════════════════════
    #
    # Add these freely. Examples below are commented out.
    # Set visible=False to hide without removing.

    _section(
        id="welcome_card",
        group="daily", position=1,
        feature_kind="content", tile_type="banner",
        content={
            "title": "Welcome",
            "body": "Your charts have been computed. Begin with Today.",
            "action_label": "Read today",
            "action_type": "open_section",
            "action_target": "today_sky",
        },
    ),

    # _section(
    #     id="diwali_muhurat_2026",
    #     group="daily", position=2,
    #     feature_kind="content", tile_type="banner",
    #     start_date="2026-10-25T00:00:00Z",
    #     end_date="2026-11-05T23:59:59Z",
    #     content={
    #         "title": "Diwali Muhurat",
    #         "body": "Lakshmi puja window: see today's panchanga",
    #         "image_url": None,
    #         "action_label": "View timings",
    #         "action_type": "open_section",
    #         "action_target": "panchanga",
    #     },
    # ),

    # _section(
    #     id="mercury_retro_alert",
    #     group="daily", position=3,
    #     feature_kind="content", tile_type="small",
    #     start_date="2026-05-10T00:00:00Z",
    #     end_date="2026-06-03T00:00:00Z",
    #     content={
    #         "title": "Mercury retrograde begins",
    #         "body": "Slow down communication; review before sending.",
    #     },
    # ),
]
