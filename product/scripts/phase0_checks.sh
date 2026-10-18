#!/usr/bin/env bash
# Phase 0: run the existing system's critical workflows and record real outputs. Run from the project root.
set -u
PY=.venv/Scripts/python.exe
OUT=product/evidence/phase0
TMP=$OUT/tmp_artifacts
rm -rf "$TMP"
stamp() { date +"%Y-%m-%dT%H:%M:%S"; }
{
echo "phase0 checks started $(stamp) on $(uname -s) git $(git rev-parse --short HEAD) branch $(git branch --show-current)"
echo "== 1 doctor"; s=$(date +%s); $PY -m sentinelloop doctor; echo "exit=$? time=$(( $(date +%s)-s ))s"
echo "== 2 full test suite"; s=$(date +%s); $PY -m pytest tests -q -p no:cacheprovider 2>&1 | tail -n 3; echo "exit=${PIPESTATUS[0]} time=$(( $(date +%s)-s ))s"
echo "== 3 pipeline fast FD001 into scratch dir"; s=$(date +%s); $PY -m sentinelloop run --subset FD001 --fast --stream-units 3 --out-dir "$TMP" 2>&1 | grep -E "^\[FD001\]|Error|Traceback"; echo "exit=${PIPESTATUS[0]} time=$(( $(date +%s)-s ))s"
echo "== 4 pipeline fast FD004 (multi-regime) into scratch dir"; s=$(date +%s); $PY -m sentinelloop run --subset FD004 --fast --stream-units 2 --out-dir "$TMP" 2>&1 | grep -E "^\[FD004\] done|Error|Traceback"; echo "exit=${PIPESTATUS[0]} time=$(( $(date +%s)-s ))s"
echo "== 5 retrain flow (simulated new data) into scratch dir"; s=$(date +%s); $PY -m sentinelloop retrain --subset FD003 --simulate-new-data --fast --out-dir "$TMP" 2>&1 | grep -E "^\[FD003\]|\"decision\"|Error|Traceback"; echo "exit=${PIPESTATUS[0]} time=$(( $(date +%s)-s ))s"
echo "== 6 audit on the shipped evidence artifacts"; s=$(date +%s); $PY -m sentinelloop audit 2>/dev/null | $PY -c "import json,sys; d=json.load(sys.stdin); print('n', d['n'], 'mismatches', d['mismatches'], 'chain_valid', d['chain_valid'])"; echo "exit=$? time=$(( $(date +%s)-s ))s"
echo "== 7 audit on the scratch run"; $PY -m sentinelloop --out-dir "$TMP" audit 2>/dev/null | $PY -c "import json,sys; d=json.load(sys.stdin); print('n', d['n'], 'mismatches', d['mismatches'], 'chain_valid', d['chain_valid'])"
echo "== 8 dashboard boots and serves HTTP"; $PY -m streamlit run src/sentinelloop/dashboard.py --server.port 8599 --server.headless true --browser.gatherUsageStats false -- --out-dir artifacts > $OUT/dashboard_boot.log 2>&1 & DPID=$!
for i in $(seq 1 30); do sleep 1; code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8599/_stcore/health); [ "$code" = "200" ] && break; done
echo "dashboard health http=$code after ${i}s"; kill $DPID 2>/dev/null; wait $DPID 2>/dev/null
echo "== 9 code size"; for d in src/sentinelloop tests experiments; do printf "%s: %s files, %s lines\n" "$d" "$(ls $d/*.py | wc -l)" "$(cat $d/*.py | wc -l)"; done
echo "phase0 checks finished $(stamp)"
} 2>&1 | tee $OUT/phase0_checks.log
