#!/usr/bin/env bash
# Suite de pruebas del scanner: valida deteccion en un objetivo vulnerable
# y CERO falsos positivos en un objetivo seguro. Uso: bash tests/run_tests.sh
set -u
cd "$(dirname "$0")/.."

export NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost"
MODS="sqli,xss,ssti,ssrf,cmdi,lfi,hosthdr"
VPORT=8199; SPORT=8200
PASS=0; FAIL=0

python3 tests/lab_vuln_server.py $VPORT >/dev/null 2>&1 &
VPID=$!
python3 tests/lab_safe_server.py $SPORT >/dev/null 2>&1 &
SPID=$!
trap 'kill $VPID $SPID 2>/dev/null' EXIT
sleep 1

VLOG=$(mktemp); SLOG=$(mktemp)
python3 active-recon.py "http://127.0.0.1:$VPORT/?id=1" -m "$MODS" \
    --mode high --skip-disclaimer --no-color > "$VLOG" 2>&1
python3 active-recon.py "http://127.0.0.1:$SPORT/?id=1" -m "$MODS" \
    --mode high --skip-disclaimer --no-color > "$SLOG" 2>&1

check() {  # $1 = etiqueta, $2 = patron que DEBE aparecer en el log vulnerable
    if grep -qE "$2" "$VLOG"; then
        echo "  [PASS] detecta $1"; PASS=$((PASS+1))
    else
        echo "  [FAIL] NO detecta $1"; FAIL=$((FAIL+1))
    fi
}

echo "== Deteccion en objetivo VULNERABLE =="
check "SQLi"        "SQLi \(error-based\)"
check "XSS"         "XSS reflejado|XSS POST|XSS: markup"
check "SSTI"        "SSTI:"
check "SSRF"        "SSRF:"
check "CMDi"        "Command Injection"
check "LFI"         "LFI:"
check "Host Header" "Host Header Injection"

echo "== Falsos positivos en objetivo SEGURO (debe ser 0) =="
FP=$(grep -E "\[(CRITICAL|HIGH|MEDIUM)\]" "$SLOG" | grep -viE "AUTO-ESCALATION|CVE:|ESCALATION" | wc -l | tr -d ' ')
if [ "$FP" -eq 0 ]; then
    echo "  [PASS] 0 falsos positivos"; PASS=$((PASS+1))
else
    echo "  [FAIL] $FP falsos positivos:"; grep -E "\[(CRITICAL|HIGH|MEDIUM)\]" "$SLOG" | grep -viE "AUTO-ESCALATION|CVE:|ESCALATION"; FAIL=$((FAIL+1))
fi

echo "== Sin tracebacks =="
TB=$(( $(grep -icE "traceback|exception" "$VLOG") + $(grep -icE "traceback|exception" "$SLOG") ))
if [ "$TB" -eq 0 ]; then echo "  [PASS] sin excepciones"; PASS=$((PASS+1)); else echo "  [FAIL] $TB excepciones"; FAIL=$((FAIL+1)); fi

rm -f "$VLOG" "$SLOG"
echo
echo "Resultado: $PASS OK, $FAIL fallidos"
[ "$FAIL" -eq 0 ]
