#!/bin/bash
# ═══════════════════════════════════════════
# DEPLOY MATCH MODE & READ MODE
# 
# PREREQUISITE: Upload these 2 files first:
#   known_people.py       → /var/www/jyotish/backend/app/services/oracle/
#   synastry_pipeline.py  → /var/www/jyotish/backend/app/services/oracle/
#
# Then run: bash deploy_match_mode.sh
# ═══════════════════════════════════════════

set -e
BACKEND="/var/www/jyotish/backend"
ORACLE="$BACKEND/app/services/oracle"

echo "═══════════════════════════════════════════"
echo "  DEPLOYING MATCH MODE & READ MODE"
echo "═══════════════════════════════════════════"

# ─── 1. Verify files exist ───
echo "[1/5] Checking files..."
for f in known_people.py synastry_pipeline.py; do
    if [ ! -f "$ORACLE/$f" ]; then
        echo "ERROR: $f not found in $ORACLE/"
        exit 1
    fi
done
echo "  ✓ All files present"

# ─── 2. Verify syntax ───
echo "[2/5] Verifying syntax..."
cd "$BACKEND"
python3 -c "import py_compile; py_compile.compile('app/services/oracle/known_people.py', doraise=True)" && echo "  ✓ known_people.py OK" || { echo "  ✗ SYNTAX ERROR"; exit 1; }
python3 -c "import py_compile; py_compile.compile('app/services/oracle/synastry_pipeline.py', doraise=True)" && echo "  ✓ synastry_pipeline.py OK" || { echo "  ✗ SYNTAX ERROR"; exit 1; }

# ─── 3. Patch public.py to add the endpoints ───
echo "[3/5] Patching public.py..."

python3 << 'PYEOF'
filepath = "/var/www/jyotish/backend/app/api/public.py"

with open(filepath, "r") as f:
    content = f.read()

# Add imports if not present
if "from app.services.oracle.synastry_pipeline import" not in content:
    # Find a good import location — after existing oracle imports
    import_block = '''from app.services.oracle.synastry_pipeline import (
    process_match_request,
    process_match_chat,
    process_read_request,
    process_read_chat,
)
from app.services.oracle.known_people import (
    load_known_people,
    delete_person,
    RELATIONSHIP_TYPES,
    RELATIONSHIP_LABELS,
)
'''
    # Insert after existing pipeline import
    if "from app.services.oracle.pipeline import" in content:
        content = content.replace(
            "from app.services.oracle.pipeline import",
            import_block + "from app.services.oracle.pipeline import",
            1
        )
    else:
        # Fallback: add at top after other imports
        content = import_block + content

    print("  + Imports added")

# Add request models if not present
models_block = '''

class MatchRequest(BaseModel):
    user_birth: dict
    partner_birth: dict
    partner_name: str
    relationship_type: str = "partner"
    message: Optional[str] = ""
    conversation_history: Optional[list] = []


class MatchChatRequest(BaseModel):
    user_birth: dict
    partner_birth: dict
    partner_name: str
    relationship_type: str = "partner"
    message: str
    conversation_history: Optional[list] = []


class ReadRequest(BaseModel):
    user_birth: dict
    person_birth: dict
    person_name: Optional[str] = ""
    relationship_type: str = "read_only"
    message: Optional[str] = ""
    conversation_history: Optional[list] = []


class ReadChatRequest(BaseModel):
    user_birth: dict
    person_birth: dict
    person_name: Optional[str] = ""
    relationship_type: str = "read_only"
    message: str
    conversation_history: Optional[list] = []
'''

if "class MatchRequest" not in content:
    # Find where other BaseModel classes are defined
    if "class ChatRequest" in content:
        # Insert after ChatRequest class
        idx = content.index("class ChatRequest")
        # Find end of that class (next class or function)
        end_idx = content.find("\nclass ", idx + 1)
        if end_idx == -1:
            end_idx = content.find("\n@router", idx + 1)
        if end_idx == -1:
            end_idx = len(content)
        content = content[:end_idx] + models_block + content[end_idx:]
        print("  + Request models added")

# Add the endpoints if not present
endpoints_block = '''

# ═══════════════════════════════════════════
# MATCH MODE & READ MODE ENDPOINTS
# ═══════════════════════════════════════════

@router.post("/match")
async def match_create(request: Request, body: MatchRequest):
    """Match Mode: synastry pie chart + initial reading."""
    check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)

    try:
        result = process_match_request(
            user_birth=body.user_birth,
            partner_birth=body.partner_birth,
            partner_name=body.partner_name,
            relationship_type=body.relationship_type,
            user_message=body.message,
            conversation_history=body.conversation_history or [],
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL

        messages = [
            {"role": "system", "content": result["system_prompt"]},
            {"role": "user", "content": result["user_prompt"]},
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            llm_response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 400, "temperature": 0.8},
            )

        if llm_response.status_code != 200:
            raise HTTPException(status_code=502, detail="LLM error")

        oracle_text = llm_response.json()["choices"][0]["message"]["content"]

        try:
            from app.services.oracle.known_people import update_person_summary
            update_person_summary(body.user_birth, result["partner_id"], oracle_text[:300])
        except Exception:
            pass

        return {
            "synastry_scores": result["synastry_scores"],
            "response": oracle_text,
            "partner_id": result["partner_id"],
            "partner_name": result["partner_name"],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-chat")
async def match_chat(request: Request, body: MatchChatRequest):
    """Subsequent messages in Match Mode."""
    check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)

    try:
        result = process_match_chat(
            user_birth=body.user_birth,
            partner_birth=body.partner_birth,
            partner_name=body.partner_name,
            relationship_type=body.relationship_type,
            user_message=body.message,
            conversation_history=body.conversation_history or [],
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL

        messages = [{"role": "system", "content": result["system_prompt"]}]
        for msg in (body.conversation_history or [])[-6:]:
            if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": body.message})

        async with httpx.AsyncClient(timeout=30.0) as client:
            llm_response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 400, "temperature": 0.8},
            )

        if llm_response.status_code != 200:
            raise HTTPException(status_code=502, detail="LLM error")

        return {"response": llm_response.json()["choices"][0]["message"]["content"]}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read")
async def read_create(request: Request, body: ReadRequest):
    """Read Mode: read someone else's chart."""
    check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)

    try:
        result = process_read_request(
            user_birth=body.user_birth,
            person_birth=body.person_birth,
            person_name=body.person_name or "",
            relationship_type=body.relationship_type,
            user_message=body.message,
            conversation_history=body.conversation_history or [],
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL

        messages = [
            {"role": "system", "content": result["system_prompt"]},
            {"role": "user", "content": result["user_prompt"]},
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            llm_response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 400, "temperature": 0.8},
            )

        if llm_response.status_code != 200:
            raise HTTPException(status_code=502, detail="LLM error")

        oracle_text = llm_response.json()["choices"][0]["message"]["content"]

        try:
            from app.services.oracle.known_people import update_person_summary
            update_person_summary(body.user_birth, result["person_id"], oracle_text[:300])
        except Exception:
            pass

        return {
            "response": oracle_text,
            "person_id": result["person_id"],
            "person_name": result["person_name"],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read-chat")
async def read_chat(request: Request, body: ReadChatRequest):
    """Subsequent messages in Read Mode."""
    check_rate_limit(request, "chat", settings.RATE_LIMIT_CHAT)

    try:
        result = process_read_chat(
            user_birth=body.user_birth,
            person_birth=body.person_birth,
            person_name=body.person_name or "",
            relationship_type=body.relationship_type,
            user_message=body.message,
            conversation_history=body.conversation_history or [],
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        api_key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL

        messages = [{"role": "system", "content": result["system_prompt"]}]
        for msg in (body.conversation_history or [])[-6:]:
            if isinstance(msg, dict) and msg.get("role") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": body.message})

        async with httpx.AsyncClient(timeout=30.0) as client:
            llm_response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 400, "temperature": 0.8},
            )

        if llm_response.status_code != 200:
            raise HTTPException(status_code=502, detail="LLM error")

        return {"response": llm_response.json()["choices"][0]["message"]["content"]}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
'''

if "@router.post(\"/match\")" not in content:
    content = content.rstrip() + "\n" + endpoints_block + "\n"
    print("  + Endpoints added")

with open(filepath, "w") as f:
    f.write(content)

print("  ✓ public.py patched")
PYEOF

# ─── 4. Verify public.py syntax ───
echo "[4/5] Verifying public.py..."
python3 -c "import py_compile; py_compile.compile('$BACKEND/app/api/public.py', doraise=True)" && echo "  ✓ public.py OK" || { echo "  ✗ SYNTAX ERROR"; exit 1; }

# ─── 5. Restart and test ───
echo "[5/5] Restarting server..."
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

echo ""
echo "═══════════════════════════════════════════"
echo "  MATCH MODE & READ MODE DEPLOYED"
echo "═══════════════════════════════════════════"
echo ""
echo "Test Match Mode:"
echo '  curl -X POST http://localhost:8081/api/public/match \'
echo '    -H "Content-Type: application/json" \'
echo '    -d "{"'"'"'user_birth"'"'"':{"'"'"'year"'"'"':1976,"'"'"'month"'"'"':7,"'"'"'day"'"'"':28,"'"'"'hour"'"'"':9,"'"'"'minute"'"'"':30,"'"'"'lat"'"'"':25.305942,"'"'"'lng"'"'"':74.090914},"'"'"'partner_birth"'"'"':{"'"'"'year"'"'"':1980,"'"'"'month"'"'"':5,"'"'"'day"'"'"':12,"'"'"'hour"'"'"':14,"'"'"'minute"'"'"':30,"'"'"'lat"'"'"':28.61,"'"'"'lng"'"'"':77.21},"'"'"'partner_name"'"'"':"'"'"'Maya"'"'"',"'"'"'relationship_type"'"'"':"'"'"'spouse"'"'"',"'"'"'message"'"'"':"'"'"'How is our bond?"'"'"'}" '
