import httpx, time, sys

URL = "https://api.plutto.space/api/public/chat"
BIRTH = {"year":2006,"month":5,"day":25,"hour":21,"minute":0,"lat":25.53,"lng":73.9}

tests = [
    # DELIVERY
    "Am I manglik?",
    "Is sade sati running?",
    "When will sade sati end?",
    "What is my nakshatra?",
    "Which gemstone should I wear?",
    "My current dasha?",
    "What is my mulank?",
    "Lucky color for today?",
    "Which direction should my desk face?",
    "Best sleeping direction?",
    "My planet strengths?",
    "What yogas do I have?",
    "My chart score?",
    "Do I have raja yoga?",
    "Current transits?",
    "Which mantra should I chant?",
    "Today panchanga?",
    "My Jaimini karakas?",
    "My navamsa chart?",
    "Tell me about my personality",
    "What remedies do I need?",
    # MARRIAGE
    "Will I get married?",
    "When will I get married?",
    "Will it be love marriage or arranged?",
    "How will my spouse look?",
    "What will my spouse do for work?",
    "Why is my marriage delayed?",
    "Will I get divorced?",
    "My boyfriend left me why?",
    "Will I find my soulmate?",
    "Is my partner cheating?",
    "Second marriage chances?",
    "Sexual problems in marriage",
    "Engagement timing?",
    # CAREER
    "How is my career?",
    "Will I get promoted this year?",
    "Should I change my job?",
    "Will I get a government job?",
    "Should I start a business?",
    "Will my business succeed?",
    "I lost my job what to do?",
    "Best career for me?",
    "Will I get a salary raise?",
    "Should I resign?",
    "My boss hates me",
    "Office politics affecting me",
    "Should I do freelancing?",
    # WEALTH
    "Will I become rich?",
    "Should I invest in stocks?",
    "I have too much debt",
    "Will I win the lottery?",
    "Should I buy property?",
    "Is crypto good for me?",
    "When will I earn more?",
    "Should I take a loan?",
    "Will I get inheritance?",
    # HEALTH
    "How is my health?",
    "I feel depressed",
    "Will my surgery go well?",
    "Do I have diabetes risk?",
    "I have chronic back pain",
    "Am I prone to accidents?",
    "Mental health issues",
    "Hair loss problem",
    "Eye problems?",
    # EDUCATION
    "Will I pass my exam?",
    "Will I clear UPSC?",
    "NEET preparation advice?",
    "Should I study abroad?",
    "PhD chances?",
    "Will I get into college?",
    "Board exam results?",
    # FOREIGN
    "Will I settle abroad?",
    "Will I get a visa?",
    "Immigration chances?",
    "Should I work abroad?",
    # CHILDREN
    "Will I have children?",
    "When will I have a baby?",
    "Boy or girl?",
    "IVF will it work?",
    # FAMILY
    "How is my father's health?",
    "My mother worries too much",
    "Sibling rivalry",
    "In-law problems",
    # SPIRITUAL
    "Am I spiritual?",
    "Tell me about my past life",
    "Which god should I worship?",
    "Should I do meditation?",
    "Is there a curse on me?",
    "Black magic affected?",
    # LEGAL
    "Will I win my court case?",
    "Property dispute outcome?",
    # TIMING
    "When will things get better?",
    "Best period ahead?",
    "Worst period?",
    "2026 prediction?",
    "Next 5 years?",
    "When will my dasha change?",
    # MODERN
    "My boss is toxic",
    "Social anxiety problem",
    "Dating apps not working",
    "Work life balance?",
    "Should I become an influencer?",
    "YouTube career?",
    # MUHURTA
    "Best date for wedding?",
    "Griha pravesh date?",
    "Good time for surgery?",
    # VASTU
    "Kitchen direction?",
    "Bedroom vastu?",
    "Office vastu?",
    # NUMEROLOGY
    "My phone number lucky?",
    "Name correction needed?",
    "Soul urge number?",
    # EVIDENCE
    "Why? Show me the astrology behind my marriage",
    # CONFUSING
    "Is the moon made of cheese?",
    "Tell me everything about my life",
    "Will I die soon?",
    "Previous astrologer said I will never marry is that true?",
    "My kundli is bad everyone says",
    "I want to know about my pet dog",
    "Nothing is going right in my life",
    "Should I buy bitcoin or ethereum?",
    "Which country should I move to?",
    "Why am I so unlucky?",
    "Am I cursed?",
    "Will I become famous?",
    "What should I eat today?",
    "I am scared of the future",
    "Marriage and career both suffering what to do?",
    "Kya meri shaadi hogi?",
    "Mera sade sati kab khatam hoga?",
    "Mujhe kaunsa ratna pehenna chahiye?",
]

client = httpx.Client(timeout=90.0)
passed = 0
failed = 0
errors = 0
total = len(tests)
fail_list = []

print(f"Running {total} tests...\n")

for i, msg in enumerate(tests):
    print(f"{'='*70}")
    print(f"Q{i+1}/{total}: {msg}")
    print(f"{'='*70}")
    try:
        start = time.time()
        resp = client.post(URL, json={"message": msg, "birth_data": BIRTH})
        elapsed = round(time.time() - start, 1)

        if resp.status_code != 200:
            print(f"ERROR: HTTP {resp.status_code}\n")
            errors += 1
            continue

        data = resp.json()
        response = data.get('response', '')
        intent = data.get('intent', '')
        hook = data.get('hook', '')

        issues = []
        jargon_words = ['mahadasha','antardasha','rashi','bhava','graha','kendra','trikona','dusthana','significator']
        found_j = [j for j in jargon_words if j in response.lower()]
        if found_j and 'astrology' not in msg.lower() and 'evidence' not in msg.lower():
            issues.append(f"JARGON:{found_j[0]}")
        if 'your your' in response.lower():
            issues.append("DOUBLE_YOUR")
        if '2th ' in response or '3th ' in response:
            issues.append("BAD_ORDINAL")
        if "{'rashi'" in response or "T01:01:" in response:
            issues.append("RAW_DATA")
        if len(response) < 20:
            issues.append("TOO_SHORT")

        status = "PASS" if not issues else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
            fail_list.append((msg, issues))

        print(f"Intent: {intent} | Time: {elapsed}s | {status} {' '.join(issues)}")
        print(f"\nRESPONSE:\n{response}")
        if hook:
            print(f"\nHOOK: {hook}")
        print()

    except Exception as e:
        errors += 1
        print(f"CRASH: {e}\n")

client.close()

print(f"\n{'='*70}")
print(f"FINAL: {total} tests | {passed} PASS | {failed} FAIL | {errors} ERROR")
print(f"Pass rate: {round(passed/max(total,1)*100)}%")
if fail_list:
    print(f"\nFAILED:")
    for msg, iss in fail_list:
        print(f"  {msg[:50]} -> {', '.join(iss)}")
