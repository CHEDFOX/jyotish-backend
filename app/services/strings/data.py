"""
STRINGS — UI labels per language.

Edit STRINGS to add/change copy. Bump STRINGS_VERSION when shape changes
(forces frontend re-fetch). Edit STRINGS_UPDATED_AT for content-only changes.

Missing keys fall back to English. Missing language → English.

How to add a language: copy the "en" dict, translate values, add it under
a new ISO code key.
"""

from typing import Dict


STRINGS_VERSION = 1
STRINGS_UPDATED_AT = "2026-05-15T12:00:00Z"

SUPPORTED_LANGUAGES = ["en", "hi"]


STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        # Groups
        "group.daily":         "Daily",
        "group.charts":        "Charts",
        "group.stories":       "Stories",
        "group.numerology":    "Numerology",
        "group.compatibility": "Compatibility",
        "group.special":       "Special",

        # Sections — daily
        "section.today_sky":    "Today's Sky",
        "section.today_deep":   "Deep Today",
        "section.the_word":     "Word of the Day",
        "section.time_reading": "This Moment",
        "section.panchanga":    "Panchanga",

        # Sections — charts
        "section.chart_overview": "Birth Chart",
        "section.core_chart":     "The Wheel",

        # Sections — stories
        "section.past_life":    "Past Life",
        "section.life_story":   "Life Story",
        "section.the_zoo":      "Your Animals",
        "section.four_pillars": "Four Pillars",
        "section.blunt_seer":   "Blunt Seer",

        # Sections — numerology
        "section.core_numbers":    "Your Numbers",
        "section.business_name":   "Business Name",
        "section.mobile_number":   "Mobile Number",
        "section.name_correction": "Name Correction",

        # Sections — compatibility
        "section.compatibility_hook": "Love Pattern",
        "section.match":              "Match",
        "section.compatibility_deep": "Deep Compatibility",

        # Sections — special
        "section.kp_horary":    "Ask a Question",

        # Sections — content tile examples
        "section.welcome_card": "Welcome",

        # Actions
        "action.read":    "Read",
        "action.open":    "Open",
        "action.dive":    "Dive in",
        "action.try":     "Try it",
        "action.next":    "Next",
        "action.back":    "Back",
        "action.cancel":  "Cancel",
        "action.save":    "Save",
        "action.share":   "Share",
        "action.retry":   "Retry",
        "action.more":    "Read more",

        # Common UI
        "common.loading":  "Loading…",
        "common.error":    "Something went wrong",
        "common.offline":  "You're offline",
        "common.empty":    "Nothing here yet",

        # Forms (for form tile_type)
        "form.partner_name":      "Partner's name",
        "form.partner_dob":       "Partner's date of birth",
        "form.partner_time":      "Partner's birth time",
        "form.partner_place":     "Partner's birth place",
        "form.business_name":     "Business name",
        "form.mobile_number":     "Mobile number",
        "form.your_name":         "Your name",
        "form.question":          "Your question",
        "form.submit":            "Submit",
        "form.optional":          "Optional",
        "form.required":          "Required",

        # Navigation
        "nav.home":     "Home",
        "nav.chat":     "Chat",
        "nav.profile":  "Profile",
        "nav.settings": "Settings",
    },

    # Hindi — translate values, keep keys identical
    "hi": {
        "group.daily":         "रोज़",
        "group.charts":        "कुंडली",
        "group.stories":       "कहानियाँ",
        "group.numerology":    "अंक ज्योतिष",
        "group.compatibility": "मेल",
        "group.special":       "विशेष",

        "section.today_sky":    "आज का आकाश",
        "section.today_deep":   "गहरा आज",
        "section.the_word":     "आज का शब्द",
        "section.time_reading": "अभी का क्षण",
        "section.panchanga":    "पंचांग",

        "section.chart_overview": "जन्म कुंडली",
        "section.core_chart":     "चक्र",

        "section.past_life":    "पूर्व जन्म",
        "section.life_story":   "जीवन कथा",
        "section.the_zoo":      "आपके पशु",
        "section.four_pillars": "चार स्तंभ",
        "section.blunt_seer":   "स्पष्ट दर्शी",

        "section.core_numbers":    "आपके अंक",
        "section.business_name":   "व्यवसाय का नाम",
        "section.mobile_number":   "मोबाइल नंबर",
        "section.name_correction": "नाम सुधार",

        "section.compatibility_hook": "प्रेम का स्वरूप",
        "section.match":              "मेल",
        "section.compatibility_deep": "गहरी अनुकूलता",

        "section.kp_horary":    "प्रश्न पूछें",

        "section.welcome_card": "स्वागत",

        "action.read":    "पढ़ें",
        "action.open":    "खोलें",
        "action.dive":    "अंदर जाएँ",
        "action.try":     "आज़माएँ",
        "action.next":    "अगला",
        "action.back":    "पीछे",
        "action.cancel":  "रद्द करें",
        "action.save":    "सहेजें",
        "action.share":   "साझा करें",
        "action.retry":   "पुनः प्रयास",
        "action.more":    "और पढ़ें",

        "common.loading":  "लोड हो रहा है…",
        "common.error":    "कुछ गलत हुआ",
        "common.offline":  "आप ऑफ़लाइन हैं",
        "common.empty":    "अभी कुछ नहीं",

        "form.partner_name":      "साथी का नाम",
        "form.partner_dob":       "साथी की जन्म तिथि",
        "form.partner_time":      "साथी का जन्म समय",
        "form.partner_place":     "साथी का जन्म स्थान",
        "form.business_name":     "व्यवसाय का नाम",
        "form.mobile_number":     "मोबाइल नंबर",
        "form.your_name":         "आपका नाम",
        "form.question":          "आपका प्रश्न",
        "form.submit":            "भेजें",
        "form.optional":          "वैकल्पिक",
        "form.required":          "आवश्यक",

        "nav.home":     "होम",
        "nav.chat":     "चैट",
        "nav.profile":  "प्रोफ़ाइल",
        "nav.settings": "सेटिंग्स",
    },
}
