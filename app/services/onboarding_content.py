"""

Onboarding content registry — serves the language picker + birth-details
screens. Everything user-facing on those screens comes from here.
"""

import asyncio
LANGUAGES = [
    # Global / lingua franca
    {"code": "en",  "name": "English",          "greeting": "Hello",          "regions": ["US","GB","AU","CA","IN","NZ","IE","ZA"]},
    {"code": "es",  "name": "Español",          "greeting": "Hola",           "regions": ["ES","MX","AR","CO","CL","PE","VE"]},
    {"code": "fr",  "name": "Français",         "greeting": "Bonjour",        "regions": ["FR","CA","BE","CH","LU","SN","CI"]},
    {"code": "ar",  "name": "العربية",          "greeting": "مرحبا",          "regions": ["SA","EG","AE","JO","LB","IQ","MA","DZ","TN"]},
    {"code": "pt",  "name": "Português",        "greeting": "Olá",            "regions": ["BR","PT","AO","MZ"]},
    {"code": "ru",  "name": "Русский",          "greeting": "Привет",         "regions": ["RU","BY","KZ"]},
    {"code": "zh",  "name": "中文",             "greeting": "你好",           "regions": ["CN","TW","SG","HK"]},
    {"code": "ja",  "name": "日本語",            "greeting": "こんにちは",      "regions": ["JP"]},
    {"code": "ko",  "name": "한국어",            "greeting": "안녕하세요",      "regions": ["KR"]},
    {"code": "de",  "name": "Deutsch",          "greeting": "Hallo",          "regions": ["DE","AT","CH"]},
    # Indian subcontinent
    {"code": "hi",  "name": "हिंदी",            "greeting": "नमस्ते",          "regions": ["IN"]},
    {"code": "bn",  "name": "বাংলা",            "greeting": "নমস্কার",         "regions": ["IN","BD"]},
    {"code": "ta",  "name": "தமிழ்",            "greeting": "வணக்கம்",        "regions": ["IN","LK","SG","MY"]},
    {"code": "te",  "name": "తెలుగు",           "greeting": "నమస్కారం",        "regions": ["IN"]},
    {"code": "mr",  "name": "मराठी",            "greeting": "नमस्कार",         "regions": ["IN"]},
    {"code": "gu",  "name": "ગુજરાતી",          "greeting": "નમસ્તે",          "regions": ["IN"]},
    {"code": "kn",  "name": "ಕನ್ನಡ",            "greeting": "ನಮಸ್ಕಾರ",         "regions": ["IN"]},
    {"code": "ml",  "name": "മലയാളം",           "greeting": "നമസ്കാരം",        "regions": ["IN"]},
    {"code": "pa",  "name": "ਪੰਜਾਬੀ",           "greeting": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ",    "regions": ["IN","PK"]},
    {"code": "or",  "name": "ଓଡ଼ିଆ",            "greeting": "ନମସ୍କାର",         "regions": ["IN"]},
    {"code": "ur",  "name": "اردو",             "greeting": "السلام علیکم",   "regions": ["PK","IN"]},
    {"code": "as",  "name": "অসমীয়া",          "greeting": "নমস্কাৰ",         "regions": ["IN"]},
    {"code": "ne",  "name": "नेपाली",           "greeting": "नमस्ते",          "regions": ["NP","IN"]},
    {"code": "si",  "name": "සිංහල",            "greeting": "ආයුබෝවන්",        "regions": ["LK"]},
    {"code": "sa",  "name": "संस्कृतम्",        "greeting": "नमस्ते",          "regions": ["IN"]},
    # European
    {"code": "it",  "name": "Italiano",         "greeting": "Ciao",           "regions": ["IT","CH","SM","VA"]},
    {"code": "nl",  "name": "Nederlands",       "greeting": "Hallo",          "regions": ["NL","BE"]},
    {"code": "sv",  "name": "Svenska",          "greeting": "Hej",            "regions": ["SE","FI"]},
    {"code": "no",  "name": "Norsk",            "greeting": "Hei",            "regions": ["NO"]},
    {"code": "da",  "name": "Dansk",            "greeting": "Hej",            "regions": ["DK"]},
    {"code": "fi",  "name": "Suomi",            "greeting": "Terve",          "regions": ["FI"]},
    {"code": "is",  "name": "Íslenska",         "greeting": "Halló",          "regions": ["IS"]},
    {"code": "pl",  "name": "Polski",           "greeting": "Cześć",          "regions": ["PL"]},
    {"code": "cs",  "name": "Čeština",          "greeting": "Ahoj",           "regions": ["CZ"]},
    {"code": "sk",  "name": "Slovenčina",       "greeting": "Ahoj",           "regions": ["SK"]},
    {"code": "hu",  "name": "Magyar",           "greeting": "Szia",           "regions": ["HU"]},
    {"code": "ro",  "name": "Română",           "greeting": "Salut",          "regions": ["RO","MD"]},
    {"code": "bg",  "name": "Български",        "greeting": "Здравей",        "regions": ["BG"]},
    {"code": "hr",  "name": "Hrvatski",         "greeting": "Bok",            "regions": ["HR"]},
    {"code": "sr",  "name": "Српски",           "greeting": "Здраво",         "regions": ["RS"]},
    {"code": "sl",  "name": "Slovenščina",      "greeting": "Zdravo",         "regions": ["SI"]},
    {"code": "et",  "name": "Eesti",            "greeting": "Tere",           "regions": ["EE"]},
    {"code": "lv",  "name": "Latviešu",         "greeting": "Sveiki",         "regions": ["LV"]},
    {"code": "lt",  "name": "Lietuvių",         "greeting": "Labas",          "regions": ["LT"]},
    {"code": "el",  "name": "Ελληνικά",         "greeting": "Γεια",           "regions": ["GR","CY"]},
    {"code": "tr",  "name": "Türkçe",           "greeting": "Merhaba",        "regions": ["TR","CY"]},
    {"code": "uk",  "name": "Українська",       "greeting": "Привіт",         "regions": ["UA"]},
    {"code": "be",  "name": "Беларуская",       "greeting": "Прывітанне",     "regions": ["BY"]},
    {"code": "ga",  "name": "Gaeilge",          "greeting": "Dia duit",       "regions": ["IE"]},
    {"code": "cy",  "name": "Cymraeg",          "greeting": "Helo",           "regions": ["GB"]},
    {"code": "eu",  "name": "Euskara",          "greeting": "Kaixo",          "regions": ["ES"]},
    {"code": "ca",  "name": "Català",           "greeting": "Hola",           "regions": ["ES","AD"]},
    {"code": "gl",  "name": "Galego",           "greeting": "Ola",            "regions": ["ES"]},
    {"code": "mt",  "name": "Malti",            "greeting": "Bonġu",          "regions": ["MT"]},
    {"code": "sq",  "name": "Shqip",            "greeting": "Përshëndetje",   "regions": ["AL","XK"]},
    {"code": "mk",  "name": "Македонски",       "greeting": "Здраво",         "regions": ["MK"]},
    # Middle East / Central Asia
    {"code": "he",  "name": "עברית",            "greeting": "שלום",           "regions": ["IL"]},
    {"code": "fa",  "name": "فارسی",            "greeting": "سلام",           "regions": ["IR","AF"]},
    {"code": "ku",  "name": "Kurdî",            "greeting": "Silav",          "regions": ["IQ","TR","IR","SY"]},
    {"code": "ps",  "name": "پښتو",             "greeting": "سلام",           "regions": ["AF","PK"]},
    {"code": "az",  "name": "Azərbaycan",       "greeting": "Salam",          "regions": ["AZ"]},
    {"code": "uz",  "name": "O'zbek",           "greeting": "Salom",          "regions": ["UZ"]},
    {"code": "kk",  "name": "Қазақ",            "greeting": "Сәлем",          "regions": ["KZ"]},
    {"code": "ky",  "name": "Кыргыз",           "greeting": "Салам",          "regions": ["KG"]},
    {"code": "hy",  "name": "Հայերեն",          "greeting": "Բարև",           "regions": ["AM"]},
    {"code": "ka",  "name": "ქართული",          "greeting": "გამარჯობა",      "regions": ["GE"]},
    # SE / E Asia
    {"code": "vi",  "name": "Tiếng Việt",       "greeting": "Xin chào",       "regions": ["VN"]},
    {"code": "th",  "name": "ภาษาไทย",          "greeting": "สวัสดี",         "regions": ["TH"]},
    {"code": "id",  "name": "Bahasa Indonesia", "greeting": "Halo",           "regions": ["ID"]},
    {"code": "ms",  "name": "Bahasa Melayu",    "greeting": "Helo",           "regions": ["MY","BN"]},
    {"code": "tl",  "name": "Filipino",         "greeting": "Kamusta",        "regions": ["PH"]},
    {"code": "my",  "name": "မြန်မာဘာသာ",        "greeting": "မင်္ဂလာပါ",      "regions": ["MM"]},
    {"code": "km",  "name": "ខ្មែរ",             "greeting": "ជំរាបសួរ",       "regions": ["KH"]},
    {"code": "lo",  "name": "ລາວ",              "greeting": "ສະບາຍດີ",        "regions": ["LA"]},
    {"code": "mn",  "name": "Монгол",           "greeting": "Сайн уу",        "regions": ["MN"]},
    # African
    {"code": "sw",  "name": "Kiswahili",        "greeting": "Habari",         "regions": ["KE","TZ","UG","RW"]},
    {"code": "am",  "name": "አማርኛ",             "greeting": "ሰላም",            "regions": ["ET"]},
    {"code": "ha",  "name": "Hausa",            "greeting": "Sannu",          "regions": ["NG","NE"]},
    {"code": "yo",  "name": "Yorùbá",           "greeting": "Bawo",           "regions": ["NG","BJ"]},
    {"code": "ig",  "name": "Igbo",             "greeting": "Ndewo",          "regions": ["NG"]},
    {"code": "zu",  "name": "isiZulu",          "greeting": "Sawubona",       "regions": ["ZA"]},
    {"code": "xh",  "name": "isiXhosa",         "greeting": "Molo",           "regions": ["ZA"]},
    {"code": "af",  "name": "Afrikaans",        "greeting": "Hallo",          "regions": ["ZA","NA"]},
    {"code": "so",  "name": "Soomaali",         "greeting": "Salaan",         "regions": ["SO"]},
    {"code": "om",  "name": "Oromoo",           "greeting": "Akkam",          "regions": ["ET"]},
    {"code": "rw",  "name": "Kinyarwanda",      "greeting": "Muraho",         "regions": ["RW"]},
    {"code": "mg",  "name": "Malagasy",         "greeting": "Salama",         "regions": ["MG"]},
    # Pacific / Americas
    {"code": "mi",  "name": "Māori",            "greeting": "Kia ora",        "regions": ["NZ"]},
    {"code": "haw", "name": "ʻŌlelo Hawaiʻi",   "greeting": "Aloha",          "regions": ["US"]},
    {"code": "sm",  "name": "Gagana Sāmoa",     "greeting": "Talofa",         "regions": ["WS"]},
    {"code": "to",  "name": "Lea fakatonga",    "greeting": "Mālō e lelei",   "regions": ["TO"]},
    {"code": "qu",  "name": "Runa Simi",        "greeting": "Rimaykullayki",  "regions": ["PE","BO","EC"]},
    {"code": "gn",  "name": "Avañeʼẽ",          "greeting": "Mbaʼéichapa",    "regions": ["PY"]},
    {"code": "ht",  "name": "Kreyòl",           "greeting": "Bonjou",         "regions": ["HT"]},
]

BIRTH_CONTENT = {
    "en": {"combinedTitle": "When Did You Arrive\nOn Earth?", "placeTitle": "Where Did You Take\nYour First Breath?", "placePlaceholder": "Search city", "continue": "CONTINUE", "labels": {"day": "DAY", "month": "MONTH", "year": "YEAR", "hour": "HOUR", "minute": "MINUTE"}},
    "hi": {"combinedTitle": "आप धरती पर\nकब आए थे?", "placeTitle": "आपने पहली सांस\nकहाँ ली?", "placePlaceholder": "शहर खोजें", "continue": "आगे", "labels": {"day": "दिन", "month": "माह", "year": "वर्ष", "hour": "घंटा", "minute": "मिनट"}},
    "zh": {"combinedTitle": "你何时\n降临人间？", "placeTitle": "你在哪里\n吸入第一口气？", "placePlaceholder": "搜索城市", "continue": "继续", "labels": {"day": "日", "month": "月", "year": "年", "hour": "时", "minute": "分"}},
    "es": {"combinedTitle": "¿Cuándo llegaste\na la Tierra?", "placeTitle": "¿Dónde tomaste\ntu primer aliento?", "placePlaceholder": "Buscar ciudad", "continue": "CONTINUAR", "labels": {"day": "DÍA", "month": "MES", "year": "AÑO", "hour": "HORA", "minute": "MIN"}},
    "pt": {"combinedTitle": "Quando você\nchegou à Terra?", "placeTitle": "Onde você deu\nseu primeiro suspiro?", "placePlaceholder": "Buscar cidade", "continue": "CONTINUAR", "labels": {"day": "DIA", "month": "MÊS", "year": "ANO", "hour": "HORA", "minute": "MIN"}},
    "ja": {"combinedTitle": "いつこの世に\n降り立ちましたか？", "placeTitle": "最初の息を\nどこで吸いましたか？", "placePlaceholder": "都市を検索", "continue": "続ける", "labels": {"day": "日", "month": "月", "year": "年", "hour": "時", "minute": "分"}},
    "fr": {"combinedTitle": "Quand es-tu\narrivé sur Terre?", "placeTitle": "Où as-tu pris\nton premier souffle?", "placePlaceholder": "Chercher une ville", "continue": "CONTINUER", "labels": {"day": "JOUR", "month": "MOIS", "year": "ANNÉE", "hour": "HEURE", "minute": "MIN"}},
    "de": {"combinedTitle": "Wann kamst du\nauf die Erde?", "placeTitle": "Wo hast du deinen\nersten Atemzug genommen?", "placePlaceholder": "Stadt suchen", "continue": "WEITER", "labels": {"day": "TAG", "month": "MONAT", "year": "JAHR", "hour": "STUNDE", "minute": "MIN"}},
    "ru": {"combinedTitle": "Когда ты прибыл\nна Землю?", "placeTitle": "Где ты сделал\nпервый вдох?", "placePlaceholder": "Найти город", "continue": "ДАЛЕЕ", "labels": {"day": "ДЕНЬ", "month": "МЕС.", "year": "ГОД", "hour": "ЧАС", "minute": "МИН"}},
    "ar": {"combinedTitle": "متى وصلت\nإلى الأرض؟", "placeTitle": "أين أخذت\nأنفاسك الأولى؟", "placePlaceholder": "ابحث عن مدينة", "continue": "متابعة", "labels": {"day": "يوم", "month": "شهر", "year": "سنة", "hour": "ساعة", "minute": "دقيقة"}},
}


# Loading-screen config. Upload any image/video/gif to
# /static/onboarding/loading.{png|jpg|gif|mp4|mov} and the universal
# manifest will pick it up automatically.
AUTH_MODE = "otp_code"  # "otp_code" | "magic_link"

LANGUAGE_TRANSITION_CONTENT = {"mediaPath": "onboarding/language_transition"}

LOADING_CONTENT = {"mediaPath": "onboarding/loading"}


def _language_name(code):
    code = (code or "").strip().lower()
    for entry in LANGUAGES:
        if entry["code"].lower() == code:
            return entry["name"]
    return code


async def build_onboarding_payload(language):
    """Compose the full onboarding payload for the given language.

    Auth + birth screen copy is resolved via the LLM-driven translator.
    Results cached to disk so each (screen, language) pair is generated
    at most once.
    """
    from app.services.onboarding_translator import get_auth_content, get_birth_content

    lang = (language or "en").strip().lower()
    name = _language_name(lang)

    auth, birth = await asyncio.gather(
        get_auth_content(lang, name),
        get_birth_content(lang, name),
    )

    return {
        "language":  lang,
        "languages": LANGUAGES,
        "screens": {
            "auth":               {**auth, "authMode": AUTH_MODE},
            "birth":              birth,
            "languageTransition": LANGUAGE_TRANSITION_CONTENT,
            "loading":            LOADING_CONTENT,
        },
    }
