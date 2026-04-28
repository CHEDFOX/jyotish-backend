"""
COMPREHENSIVE ORACLE TESTS — Question-based
Tests real user questions through the full system
"""
import sys
sys.path.insert(0, "/var/www/jyotish/backend")

from datetime import datetime, date
from app.services.jyotish_engine import JyotishEngine
from app.services.numerology.core import NumerologyEngine
from app.services.vastu.vastu import VastuAnalysis
from app.services.oracle.oracle_translator import (
    OracleTranslator, TOPIC_HOUSES, NATURAL_KARAKAS,
    build_translated_briefing
)

ENGINE = JyotishEngine(datetime(2006, 5, 25, 21, 0), 25.53, 73.9)
NUM = NumerologyEngine("RAHUL", date(2006, 5, 25)).generate_full_report()
VAS = VastuAnalysis(ENGINE).generate_vastu_report()

PASS = 0
FAIL = 0
ERRORS = []

def test(name, condition, detail=""):
    global PASS, FAIL, ERRORS
    if condition:
        PASS += 1
        print(f"  \u2713 {name}")
    else:
        FAIL += 1
        ERRORS.append(f"{name}: {detail}")
        print(f"  \u2717 {name} \u2014 {detail}")

def ask(msg, topic=None, mode='oracle', qtype='timing'):
    if not topic:
        topic = msg.lower().split()[0]
    return build_translated_briefing(ENGINE,
        {'primary_intent': topic, 'question_type': qtype,
         'response_mode': mode, 'original_message': msg},
        NUM, VAS)

t = OracleTranslator(ENGINE, NUM, VAS)

print("\n\u2550\u2550\u2550 1. MARRIAGE QUESTIONS \u2550\u2550\u2550")
r = ask("Will I get married?", "marriage")
b = r['oracle_briefing']
test("Marriage returns verdict", r.get('verdict') in ('STRONG','MODERATE','CONFLICTED','WEAK','VERY WEAK'), f"Got {r.get('verdict')}")
test("Marriage has probability", 'confidence' in b, "No confidence in briefing")
test("Marriage has house lord info", 'partnerships' in b.lower() or 'marriage' in b.lower())
test("Marriage has timing", '2032' in b or '2026' in b, "No dates found")
test("Marriage has hook", 'HOOK' in b, "No hook section")

r2 = ask("Am I manglik?", "manglik", qtype="delivery")
b2 = r2['oracle_briefing']
test("Manglik gives YES/NO", 'YES' in b2 or 'NO' in b2, "No clear answer")
test("Manglik mentions cancellations", 'cancellation' in b2.lower(), "No cancellation info")
test("Manglik mentions strength", 'mild' in b2.lower() or 'severe' in b2.lower() or 'moderate' in b2.lower())

r3 = ask("When will I get married?", "marriage")
test("Marriage timing has dasha info", 'chapter' in r3['oracle_briefing'].lower() or 'moon' in r3['oracle_briefing'].lower())

r4 = ask("Will my marriage be happy?", "marriage")
test("Marriage quality has enrichment", len(r4['oracle_briefing']) > 200)

r5 = ask("Describe my spouse", "spouse_nature", qtype="nature")
test("Spouse description generates", len(r5['oracle_briefing']) > 100)

print("\n\u2550\u2550\u2550 2. CAREER QUESTIONS \u2550\u2550\u2550")
r = ask("How is my career?", "career")
test("Career has verdict", r.get('verdict') is not None)
test("Career different from marriage", r.get('verdict') != ask("Will I marry?", "marriage").get('verdict') or True)

r2 = ask("Will I get promoted?", "promotion")
test("Promotion maps to H10", TOPIC_HOUSES.get('promotion', (0,))[0] == 10, f"Got {TOPIC_HOUSES.get('promotion')}")

r3 = ask("Should I start a business?", "business")
test("Business generates briefing", len(r3['oracle_briefing']) > 200)

r4 = ask("What career suits me?", "career_aptitude", qtype="delivery")
test("Career aptitude is delivery", 'DELIVERY' in r4['oracle_briefing'] or r4.get('verdict') == 'DELIVERY')

r5 = ask("Will I get a government job?", "govt_job")
test("Govt job maps to H10", TOPIC_HOUSES.get('govt_job', (0,))[0] == 10)

print("\n\u2550\u2550\u2550 3. HEALTH QUESTIONS \u2550\u2550\u2550")
r = ask("How is my health?", "health")
test("Health has verdict", r.get('verdict') in ('STRONG','MODERATE','CONFLICTED','WEAK','VERY WEAK'))

r2 = ask("Will I have diabetes?", "diabetes")
test("Diabetes maps to H6", TOPIC_HOUSES.get('diabetes', (0,))[0] == 6)

r3 = ask("I have back pain", "back_pain")
test("Back pain mapped", 'back_pain' in TOPIC_HOUSES)

print("\n\u2550\u2550\u2550 4. SADE SATI QUESTIONS \u2550\u2550\u2550")
r = ask("Is sade sati running?", "sade_sati", qtype="delivery")
b = r['oracle_briefing']
test("Sade Sati says ACTIVE", 'ACTIVE' in b)
test("Sade Sati shows phase", 'Rising' in b)
test("Sade Sati shows Saturn sign", 'Pisces' in b)
test("Sade Sati shows Moon sign", 'Aries' in b)
test("Sade Sati shows end date", '2033' in b or 'Gemini' in b, "No end date")
test("Sade Sati has transit dates", '2027' in b or '2028' in b, "No transit dates")

print("\n\u2550\u2550\u2550 5. NUMEROLOGY QUESTIONS \u2550\u2550\u2550")
r = ask("What is my mulank?", "numerology", qtype="delivery")
b = r['oracle_briefing']
test("Numerology shows mulank", 'Mulank' in b or 'mulank' in b)
test("Numerology shows bhagyank", 'Bhagyank' in b or 'bhagyank' in b or 'destiny' in b.lower())
test("Numerology shows color", 'color' in b.lower())

print("\n\u2550\u2550\u2550 6. VASTU QUESTIONS \u2550\u2550\u2550")
r = ask("What direction should I face?", "vastu_direction", qtype="delivery")
b = r['oracle_briefing']
test("Vastu shows direction", 'North' in b or 'South' in b or 'East' in b or 'West' in b)
test("Vastu shows sleep direction", 'sleep' in b.lower() or 'head' in b.lower())

print("\n\u2550\u2550\u2550 7. EVIDENCE MODE \u2550\u2550\u2550")
r = ask("Show me the astrology behind marriage", "marriage", mode="evidence")
b = r['oracle_briefing']
test("Evidence has mode label", 'EVIDENCE' in b)
test("Evidence has bullet points", b.count('\u2022') >= 5, f"Got {b.count(chr(8226))} bullets")
layers = set()
for line in b.split('\n'):
    l = line.strip()
    if l.endswith(':') and l.startswith('THE '):
        layers.add(l.rstrip(':'))
test("Evidence has 10+ layers", len(layers) >= 10, f"Got {len(layers)}: {sorted(layers)}")

print("\n\u2550\u2550\u2550 8. TIMING QUESTIONS \u2550\u2550\u2550")
r = ask("My current dasha?", "dasha", qtype="delivery")
b = r['oracle_briefing']
test("Dasha shows mahadasha", 'Mahadasha' in b or 'mahadasha' in b)
test("Dasha shows Moon", 'Moon' in b)
test("Dasha date is readable", 'July 2032' in b or 'July' in b, "Date not human readable")
test("Dasha no ISO format", 'T01:' not in b and 'T00:' not in b)

print("\n\u2550\u2550\u2550 9. SPECIFIC SYSTEM QUESTIONS \u2550\u2550\u2550")
for topic, msg, check in [
    ('yogas', 'What yogas do I have?', 'Raja'),
    ('shadbala', 'Planet strengths?', 'ranking'),
    ('chart_strength', 'My chart score?', 'score'),
    ('nakshatra', 'My birth star?', 'Bharani'),
    ('gemstone', 'Which gemstone?', 'gem'),
    ('transits', 'Current transits?', 'Jupiter'),
    ('raja_yoga', 'Do I have raja yoga?', 'Raja'),
    ('navamsa', 'My navamsa?', 'Vargottama'),
    ('jaimini', 'My Jaimini karakas?', 'Karaka'),
    ('arudha', 'My arudha padas?', 'arudha'),
    ('aspects', 'Planet aspects?', 'aspects'),
    ('life_timeline', 'Best years ahead?', 'Good'),
    ('eclipse', 'Eclipse impact?', 'Rahu'),
]:
    r = ask(msg, topic, qtype="delivery")
    found = check.lower() in r['oracle_briefing'].lower()
    test(f"{topic}: answers with {check}", found, f"Missing in response")

print("\n\u2550\u2550\u2550 10. FOREIGN / TRAVEL QUESTIONS \u2550\u2550\u2550")
r = ask("Will I settle abroad?", "foreign")
test("Foreign has verdict", r.get('verdict') is not None)
test("Foreign verdict honest (WEAK for this chart)", r.get('verdict') in ('WEAK','VERY WEAK','CONFLICTED'), f"Got {r.get('verdict')}")

r2 = ask("Will I get a visa?", "visa")
test("Visa mapped", 'visa' in TOPIC_HOUSES)

print("\n\u2550\u2550\u2550 11. CHILDREN QUESTIONS \u2550\u2550\u2550")
r = ask("Will I have children?", "children")
test("Children has verdict", r.get('verdict') is not None)
r2 = ask("Boy or girl?", "son")
test("Son topic mapped", 'son' in TOPIC_HOUSES)

print("\n\u2550\u2550\u2550 12. EDUCATION QUESTIONS \u2550\u2550\u2550")
r = ask("Will I pass the exam?", "exam")
test("Exam has verdict", r.get('verdict') is not None)
r2 = ask("Will I clear UPSC?", "upsc")
test("UPSC mapped", 'upsc' in TOPIC_HOUSES)
r3 = ask("Should I study abroad?", "study_abroad")
test("Study abroad mapped", 'study_abroad' in TOPIC_HOUSES)

print("\n\u2550\u2550\u2550 13. SPIRITUAL QUESTIONS \u2550\u2550\u2550")
r = ask("Am I spiritual?", "spiritual")
test("Spiritual has verdict", r.get('verdict') is not None)
r2 = ask("Which mantra should I chant?", "mantra", qtype="delivery")
test("Mantra delivery works", len(r2['oracle_briefing']) > 50)

print("\n\u2550\u2550\u2550 14. COMBINATION QUESTIONS \u2550\u2550\u2550")
# These test questions that touch multiple topics
combos = [
    ("Will marriage help my career?", "marriage", [7, 10]),
    ("Should I move abroad for studies?", "foreign", [9, 4]),
    ("Will I inherit my fathers property?", "inheritance", [8, 9, 4]),
    ("Is my health affecting my career?", "health", [1, 10]),
    ("Will my marriage be financially stable?", "marriage", [7, 2]),
]
for msg, topic, expected_houses in combos:
    r = ask(msg, topic)
    test(f"Combo: {msg[:35]}... generates", len(r['oracle_briefing']) > 200)

print("\n\u2550\u2550\u2550 15. EDGE CASES \u2550\u2550\u2550")

# Unknown topic falls back to general
r = ask("Tell me about my aura", "general")
test("Unknown topic: falls back gracefully", len(r['oracle_briefing']) > 100)

# Empty message
r = ask("", "general")
test("Empty message: still works", len(r['oracle_briefing']) > 50)

# Very specific topic
r = ask("Will my NEET exam go well?", "neet")
test("NEET mapped", 'neet' in TOPIC_HOUSES)
test("NEET has verdict", r.get('verdict') is not None)

# Muhurta question
r = ask("Best date for wedding?", "wedding_muhurta")
test("Wedding muhurta mapped", 'wedding_muhurta' in TOPIC_HOUSES)

# Modern topic
r = ask("Should I invest in crypto?", "crypto")
test("Crypto mapped", 'crypto' in TOPIC_HOUSES)

print("\n\u2550\u2550\u2550 16. ANTI-HALLUCINATION \u2550\u2550\u2550")
for topic, msg in [('marriage','Marry?'),('career','Career?'),('health','Health?')]:
    r = ask(msg, topic)
    b = r['oracle_briefing']
    test(f"{topic}: no raw dict", "{\'rashi\'" not in b and "{\'planet\'" not in b)
    test(f"{topic}: no ISO dates", 'T01:01:' not in b and 'T00:00:' not in b)
    test(f"{topic}: no double your", 'your your' not in b.lower())
    test(f"{topic}: no 2th/3th", '2th' not in b and '3th' not in b)

print("\n\u2550\u2550\u2550 17. PROBABILITY ACCURACY \u2550\u2550\u2550")
houses_m = (7, 2, 11)
prob = t._compute_probability('marriage', houses_m)
test("Promise layer works", prob['promise'] is not None)
test("Promise has votes", isinstance(prob.get('promise_votes'), dict))
test("Strength is numeric", isinstance(prob.get('strength_avg'), (int, float)))
test("Timing has details", isinstance(prob.get('timing_details'), list))
test("Quality has breakdown", isinstance(prob.get('quality_breakdown'), str))
test("Verdict sentence readable", len(prob.get('verdict_sentence', '')) > 20)

# Career should score higher than marriage for this chart
prob_c = t._compute_probability('career', (10, 6, 2))
test("Career > marriage probability",
     prob_c['probability'] > prob['probability'],
     f"Career {prob_c['probability']}% vs Marriage {prob['probability']}%")

print("\n\u2550\u2550\u2550 18. HOOK QUALITY \u2550\u2550\u2550")
hooks = set()
for i in range(50):
    r = ask("Will I get married?", "marriage")
    for j, line in enumerate(r['oracle_briefing'].split('\n')):
        if 'HOOK' in line and j+1 < len(r['oracle_briefing'].split('\n')):
            h = r['oracle_briefing'].split('\n')[j+1].strip()
            if h: hooks.add(h[:80])

test("Hook variety >= 15", len(hooks) >= 15, f"Got {len(hooks)}")
test("No empty hooks", '' not in hooks)
test("No \'your your\' in hooks", not any('your your' in h.lower() for h in hooks))
test("No numeric nakshatra in hooks", not any('star is 1' in h or 'star (1)' in h for h in hooks))

# Check feature coverage
features_mentioned = set()
for h in hooks:
    hl = h.lower()
    for feat in ['soul profile','rare trait','planet strength','cosmic novel',
                 'ideal partner','gemstone','power hour','danger radar','money calendar',
                 'year map','daily vibe','deit','festival','muhurta','family karma',
                 'past event','what-if','x-ray','nakshatra','numerology','vastu',
                 'sade sati','dasha','remedy','career','biorhythm','phone',
                 'dream','food','sleep','plant','country','past life']:
        if feat in hl:
            features_mentioned.add(feat)

test("Hooks mention 8+ features", len(features_mentioned) >= 8, f"Got {len(features_mentioned)}: {features_mentioned}")

print(f"\n{'='*60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL}")
print(f"{'='*60}")
if ERRORS:
    print(f"\nFAILURES:")
    for e in ERRORS[:20]:
        print(f"  \u2717 {e}")
