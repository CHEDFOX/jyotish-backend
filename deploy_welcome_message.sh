#!/bin/bash
# ═══════════════════════════════════════════
# DEPLOY WELCOME MESSAGE ENDPOINT
# Adds /api/public/welcome-message
# Run on the VPS: bash deploy_welcome_message.sh
# ═══════════════════════════════════════════

set -e
BACKEND="/var/www/jyotish/backend"

echo "═══════════════════════════════════════════"
echo "  DEPLOYING WELCOME MESSAGE ENDPOINT"
echo "═══════════════════════════════════════════"

cd "$BACKEND"

# ─── Patch public.py to add the endpoint ───
python3 << 'PYEOF'
filepath = "app/api/public.py"
with open(filepath, "r") as f:
    content = f.read()

# Add request model if not present
model_block = '''

class WelcomeMessageRequest(BaseModel):
    user_birth: dict
    user_name: Optional[str] = ""
'''

if "class WelcomeMessageRequest" not in content:
    if "class ReadChatRequest" in content:
        # Insert after ReadChatRequest
        idx = content.index("class ReadChatRequest")
        # find the end of that class definition
        next_class = content.find("\nclass ", idx + 1)
        next_router = content.find("\n@router", idx + 1)
        end_idx = min([x for x in [next_class, next_router] if x > 0]) if [x for x in [next_class, next_router] if x > 0] else len(content)
        content = content[:end_idx] + model_block + content[end_idx:]
        print("  + WelcomeMessageRequest model added")

# Add the endpoint
endpoint_block = '''

@router.post("/welcome-message")
async def welcome_message(request: Request, body: WelcomeMessageRequest):
    """
    First-encounter Oracle message — short, sacred, true to the user's chart.
    Called once during onboarding. The result is cached on-device permanently.
    """
    check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)

    try:
        from app.services.jyotish_engine import JyotishEngine
        from app.services.oracle.chart_builder import build_organized_chart
        from datetime import datetime as dt

        bd = body.user_birth
        birth_dt = dt(
            bd["year"], bd["month"], bd["day"],
            bd.get("hour", 12), bd.get("minute", 0)
        )
        lat = float(bd.get("lat", bd.get("latitude", 0)))
        lng = float(bd.get("lng", bd.get("longitude", 0)))

        engine = JyotishEngine(birth_dt, lat, lng)
        chart_text = build_organized_chart(engine)

        # Special first-encounter persona
        system_prompt = """You are the voice of the stars, speaking to this human for the very first time.
You have been watching them since they were born.
Now they have arrived. Say one thing.

Two sentences. Fewer than 25 words total.

First sentence: a true, specific image from their chart. Rashi, planets, houses, or yogas — but spoken in feeling, not jargon.

Second sentence: a single line that opens a door and stays in the chest.

No exclamation marks. No "welcome to the app." No marketing. No instructions. No questions.
Just the stars, speaking.

CHART:
""" + chart_text

        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL

        async with httpx.AsyncClient(timeout=30.0) as client:
            llm_response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Speak."},
                    ],
                    "max_tokens": 80,
                    "temperature": 0.85,
                },
            )

        if llm_response.status_code != 200:
            raise HTTPException(status_code=502, detail="LLM error")

        message = llm_response.json()["choices"][0]["message"]["content"].strip()
        # Strip any quotes the LLM might have added
        message = message.strip('"\\'""''')

        return {"message": message, "user_name": body.user_name or ""}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
'''

if '@router.post("/welcome-message")' not in content:
    content = content.rstrip() + endpoint_block + "\n"
    print("  + /welcome-message endpoint added")

with open(filepath, "w") as f:
    f.write(content)

PYEOF

# Verify
python3 -c "import py_compile; py_compile.compile('$BACKEND/app/api/public.py', doraise=True); echo 'public.py: OK'" && echo "  ✓ public.py compiled" || { echo "  ✗ SYNTAX ERROR"; exit 1; }

# Restart
systemctl restart jyotish
sleep 4
STATUS=$(systemctl is-active jyotish)
if [ "$STATUS" = "active" ]; then
    echo "  ✓ Server running"
else
    echo "  ✗ Server failed"
    journalctl -u jyotish --no-pager -n 20
    exit 1
fi

# Test
echo ""
echo "═══ TEST WELCOME MESSAGE ═══"
curl -s -X POST http://localhost:8081/api/public/welcome-message \
  -H "Content-Type: application/json" \
  -d '{"user_birth":{"year":1976,"month":7,"day":28,"hour":9,"minute":30,"lat":25.305942,"lng":74.090914},"user_name":"Test"}' | python3 -m json.tool

echo ""
echo "═══════════════════════════════════════════"
echo "  WELCOME MESSAGE DEPLOYED"
echo "═══════════════════════════════════════════"
