#!/bin/bash
# ═══════════════════════════════════════════
# DEPLOY NEW PIPELINE v2
# Replaces old pipeline with: chart builder + LLM selector + verdict extraction
#
# PREREQUISITE: Upload these 3 files first:
#   chart_builder.py   → /var/www/jyotish/backend/app/services/oracle/
#   method_selector.py → /var/www/jyotish/backend/app/services/oracle/
#   new_pipeline.py    → /var/www/jyotish/backend/app/services/oracle/
#
# Then run: bash deploy_pipeline_v2.sh
# ═══════════════════════════════════════════

set -e
BACKEND="/var/www/jyotish/backend"
ORACLE="$BACKEND/app/services/oracle"

echo "═══════════════════════════════════════════"
echo "  DEPLOYING NEW PIPELINE v2"
echo "═══════════════════════════════════════════"

# ─── 1. Verify files exist ───
echo "[1/6] Checking files..."
for f in chart_builder.py method_selector.py new_pipeline.py; do
    if [ ! -f "$ORACLE/$f" ]; then
        echo "ERROR: $f not found in $ORACLE/"
        echo "Upload it first, then re-run this script."
        exit 1
    fi
done
echo "  ✓ All files present"

# ─── 2. Backup old pipeline ───
echo "[2/6] Backing up old pipeline..."
cp "$ORACLE/pipeline.py" "$ORACLE/pipeline_old_backup.py"
echo "  ✓ Backed up to pipeline_old_backup.py"

# ─── 3. Replace pipeline.py with new_pipeline.py ───
echo "[3/6] Replacing pipeline..."
cp "$ORACLE/new_pipeline.py" "$ORACLE/pipeline.py"
echo "  ✓ pipeline.py replaced"

# ─── 4. Verify syntax ───
echo "[4/6] Verifying syntax..."
cd "$BACKEND"
python3 -c "import py_compile; py_compile.compile('app/services/oracle/chart_builder.py', doraise=True)" && echo "  ✓ chart_builder.py OK" || { echo "  ✗ chart_builder.py SYNTAX ERROR"; exit 1; }
python3 -c "import py_compile; py_compile.compile('app/services/oracle/method_selector.py', doraise=True)" && echo "  ✓ method_selector.py OK" || { echo "  ✗ method_selector.py SYNTAX ERROR"; exit 1; }
python3 -c "import py_compile; py_compile.compile('app/services/oracle/pipeline.py', doraise=True)" && echo "  ✓ pipeline.py OK" || { echo "  ✗ pipeline.py SYNTAX ERROR"; exit 1; }

# ─── 5. Test imports ───
echo "[5/6] Testing imports..."
cd "$BACKEND"
python3 -c "
from app.services.oracle.chart_builder import build_organized_chart
from app.services.oracle.method_selector import select_methods
from app.services.oracle.pipeline import process_oracle_query, store_oracle_memory
print('  ✓ All imports OK')
"

# ─── 6. Test with real chart ───
echo "[6/6] Testing with real chart..."
cd "$BACKEND"
python3 -c "
from app.services.jyotish_engine import JyotishEngine
from app.services.oracle.chart_builder import build_organized_chart
from datetime import datetime

e = JyotishEngine(datetime(1976, 7, 28, 9, 30), 25.305942, 74.090914)
chart = build_organized_chart(e)
print('  Chart length:', len(chart), 'chars')
print('  Preview:')
for line in chart.split(chr(10))[:5]:
    print('    ', line)
print('  ✓ Chart builder works')
"

# ─── Restart ───
echo ""
echo "Restarting..."
systemctl restart jyotish
sleep 4
STATUS=$(systemctl is-active jyotish)
if [ "$STATUS" = "active" ]; then
    echo "  ✓ Server running"
else
    echo "  ✗ Server failed to start"
    journalctl -u jyotish --no-pager -n 15
    exit 1
fi

# ─── Clear memory for clean test ───
rm -f "$BACKEND/data/memory/"*.json

echo ""
echo "═══════════════════════════════════════════"
echo "  PIPELINE v2 DEPLOYED"
echo "═══════════════════════════════════════════"
echo ""
echo "  Architecture:"
echo "    1. Organized chart (906 chars, cached)"
echo "    2. Prashna cast fresh each query"
echo "    3. LLM selector picks 4-8 methods"
echo "    4. Methods fired, verdicts extracted"
echo "    5. User memory recalled"
echo "    6. Clean briefing sent to Oracle LLM"
echo ""
echo "  Test with:"
echo "    curl -s -X POST http://localhost:8081/api/public/chat \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"message\":\"Should I invest in silver?\",\"kundli_data\":{\"raw\":{\"birth_details\":{\"year\":1976,\"month\":7,\"day\":28,\"hour\":9,\"minute\":30,\"latitude\":25.305942,\"longitude\":74.090914}}}}' | python3 -m json.tool"
echo ""
echo "  To rollback:"
echo "    cp $ORACLE/pipeline_old_backup.py $ORACLE/pipeline.py"
echo "    systemctl restart jyotish"

