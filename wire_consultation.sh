#!/bin/bash
# ═══════════════════════════════════════════
# WIRE CONSULTATION ENGINE INTO PIPELINE
# Run AFTER uploading consultation_engine.py to:
#   /var/www/jyotish/backend/app/services/oracle/consultation_engine.py
# ═══════════════════════════════════════════

set -e
BACKEND="/var/www/jyotish/backend"

echo "═══════════════════════════════════════════"
echo "  WIRING CONSULTATION ENGINE"
echo "═══════════════════════════════════════════"

# Verify file exists
if [ ! -f "$BACKEND/app/services/oracle/consultation_engine.py" ]; then
    echo "ERROR: consultation_engine.py not found!"
    echo "Upload it to: $BACKEND/app/services/oracle/consultation_engine.py"
    exit 1
fi

# 1. Patch pipeline.py to use consult() instead of assemble_data()
python3 << 'PYEOF'
filepath = "/var/www/jyotish/backend/app/services/oracle/pipeline.py"
with open(filepath, "r") as f:
    content = f.read()

# Add consultation engine import
if "from .consultation_engine import consult" not in content:
    content = content.replace(
        "from .data_assembler import assemble_data",
        "from .data_assembler import assemble_data\nfrom .consultation_engine import consult"
    )

# Replace assemble_data call with consult
# Find the block that calls assemble_data and replace it
old_block = """        # Step 3: Assemble data
        if engine:
            data_packet = assemble_data(engine, intent)
        else:
            data_packet = {
                'oracle_briefing': 'No birth data provided. Respond based on general astrology principles.',
                'sections': [],
                'intent': intent['primary_intent'],
                'tone': intent['emotional_tone'],
            }

        # Step 3.5: Inject user memory
        if birth_data:
            try:
                mem = recall_user_memory(birth_data)
                if mem:
                    data_packet['user_memory'] = mem
            except Exception as e:
                print(f"[Memory] Recall error: {e}")"""

new_block = """        # Step 3: CONSULTATION ENGINE (replaces basic assemble_data)
        # Recalls user memory internally for finding ranking
        memory_text = ""
        if birth_data:
            try:
                memory_text = recall_user_memory(birth_data)
            except Exception:
                pass

        if engine:
            try:
                data_packet = consult(engine, intent, memory_text)
                # Also inject memory into data_packet for prompt_builder
                if memory_text:
                    data_packet['user_memory'] = memory_text
            except Exception as e:
                print(f"[Consultation] Error, falling back to basic assembly: {e}")
                import traceback
                traceback.print_exc()
                data_packet = assemble_data(engine, intent)
                if memory_text:
                    data_packet['user_memory'] = memory_text
        else:
            data_packet = {
                'oracle_briefing': 'No birth data provided. Respond based on general astrology principles.',
                'sections': [],
                'intent': intent['primary_intent'],
                'tone': intent['emotional_tone'],
            }"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, "w") as f:
        f.write(content)
    print("pipeline.py patched (exact match)")
else:
    # Try flexible: just replace the assemble_data call
    if "data_packet = assemble_data(engine, intent)" in content and "consult(engine" not in content:
        # Replace assemble_data with consult, keeping fallback
        content = content.replace(
            "            data_packet = assemble_data(engine, intent)",
            """            # Use Consultation Engine with fallback
            memory_text_for_consult = ""
            if birth_data:
                try:
                    memory_text_for_consult = recall_user_memory(birth_data)
                except Exception:
                    pass
            try:
                data_packet = consult(engine, intent, memory_text_for_consult)
                if memory_text_for_consult:
                    data_packet['user_memory'] = memory_text_for_consult
            except Exception as _ce:
                print(f"[Consultation] Fallback to assembler: {_ce}")
                data_packet = assemble_data(engine, intent)"""
        )
        with open(filepath, "w") as f:
            f.write(content)
        print("pipeline.py patched (flexible match)")
    elif "consult(engine" in content:
        print("pipeline.py already uses consultation engine")
    else:
        print("WARNING: Could not patch pipeline.py automatically")
        print("You need to replace 'assemble_data(engine, intent)' with 'consult(engine, intent, memory_text)'")

PYEOF

# 2. Update prompt_builder to handle the structured briefing better
python3 << 'PYEOF'
filepath = "/var/www/jyotish/backend/app/services/oracle/prompt_builder.py"
with open(filepath, "r") as f:
    content = f.read()

# The structured briefing from consultation_engine already has sections
# labeled with ═══ headers. The prompt_builder should tell the LLM
# how to use this structure.

old_chart_instruction = "CHART DATA (SYNTHESIS observations are the most important"
new_chart_instruction = "CHART DATA (structured by importance — LEAD finding answers the question directly. PRASHNA is the universe's real-time verdict. Cross-validate VERDICTS before making claims. Use ANOMALIES to personalize"

if old_chart_instruction in content:
    content = content.replace(old_chart_instruction, new_chart_instruction)
    with open(filepath, "w") as f:
        f.write(content)
    print("prompt_builder.py updated for structured briefing")
else:
    print("prompt_builder.py chart instruction not found (may already be updated)")

PYEOF

# 3. Update methods_fired tracking in pipeline return
python3 << 'PYEOF'
filepath = "/var/www/jyotish/backend/app/services/oracle/pipeline.py"
with open(filepath, "r") as f:
    content = f.read()

# The consultation engine returns methods_fired in data_packet
# Update the pipeline return to use it
if "'methods_fired': intent.get('methods', [])" in content:
    content = content.replace(
        "'methods_fired': intent.get('methods', [])",
        "'methods_fired': data_packet.get('methods_fired', intent.get('methods', []))"
    )
    with open(filepath, "w") as f:
        f.write(content)
    print("pipeline.py methods_fired updated")
else:
    print("pipeline.py methods_fired already correct or different format")

PYEOF

# 4. Verify syntax
echo ""
echo "Verifying syntax..."
python3 -c "import py_compile; py_compile.compile('$BACKEND/app/services/oracle/consultation_engine.py', doraise=True); print('  consultation_engine.py: OK')"
python3 -c "import py_compile; py_compile.compile('$BACKEND/app/services/oracle/pipeline.py', doraise=True); print('  pipeline.py: OK')"
python3 -c "import py_compile; py_compile.compile('$BACKEND/app/services/oracle/prompt_builder.py', doraise=True); print('  prompt_builder.py: OK')"

# 5. Test imports
echo ""
echo "Testing imports..."
cd "$BACKEND"
python3 -c "from app.services.oracle.consultation_engine import consult; print('  consultation_engine: OK')"
python3 -c "from app.services.oracle.pipeline import process_oracle_query; print('  pipeline: OK')"

# 6. Test with real chart
echo ""
echo "Testing with real chart data..."
python3 -c "
from app.services.jyotish_engine import JyotishEngine
from app.services.oracle.consultation_engine import consult
from datetime import datetime

e = JyotishEngine(datetime(2004, 3, 1, 8, 0), 24.89, 74.65)
intent = {'primary_intent': 'marriage', 'emotional_tone': 'hopeful', 'emotion': 'curious'}

result = consult(e, intent)

print('Methods fired:', len(result.get('methods_fired', [])))
print('Findings:', result.get('findings_count', 0))
print('Prashna verdict:', result.get('prashna_verdict', ''))
print('Prashna confidence:', result.get('prashna_confidence', 0), '%')
print()
briefing = result.get('oracle_briefing', '')
# Show first 800 chars of briefing
print('=== BRIEFING (first 800 chars) ===')
print(briefing[:800])
print('...')
print()
print('=== BRIEFING LENGTH ===')
print(len(briefing), 'chars')
"

# 7. Restart
echo ""
echo "Restarting..."
systemctl restart jyotish
sleep 4
systemctl status jyotish | head -5

# 8. Clear memory and test
rm -f "$BACKEND/data/memory/*.json"

echo ""
echo "═══════════════════════════════════════════"
echo "  CONSULTATION ENGINE DEPLOYED"
echo "═══════════════════════════════════════════"
echo ""
echo "Test:"
echo '  curl -s -X POST http://localhost:8081/api/public/chat \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"message":"Will I get married?","kundli_data":{"raw":{"birth_details":{"year":2004,"month":3,"day":1,"hour":8,"minute":0,"latitude":24.89,"longitude":74.65}}}}'"'"' | python3 -m json.tool'

