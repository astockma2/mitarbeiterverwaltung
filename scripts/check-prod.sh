#!/bin/bash
# Produktionssystem prüfen und bei Bedarf wiederherstellen
# Verwendung: ./scripts/check-prod.sh [--fix]

set -e

COMPOSE_FILE="/opt/mva/docker-compose.prod.yml"
BASE_URL="http://localhost:8090"
FIX_MODE=false

[[ "${1:-}" == "--fix" ]] && FIX_MODE=true

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

echo "=== MVA Produktions-Check $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""

# 1. Container-Status
echo "--- Container ---"
ERRORS=0

for SVC in db redis backend frontend; do
    STATUS=$(sudo docker compose -f "$COMPOSE_FILE" ps --format json "$SVC" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('State','?'))" 2>/dev/null || echo "unbekannt")
    if [[ "$STATUS" == "running" ]]; then
        ok "$SVC: läuft"
    else
        fail "$SVC: $STATUS"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# 2. HTTP-Checks
echo "--- HTTP ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE_URL/api/health" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    VERSION=$(curl -s --max-time 5 "$BASE_URL/api/health" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
    ok "Health-Check: HTTP $HTTP_CODE (Version $VERSION)"
else
    fail "Health-Check: HTTP $HTTP_CODE"
    ERRORS=$((ERRORS + 1))
fi

FRONT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE_URL/" 2>/dev/null || echo "000")
if [[ "$FRONT_CODE" == "200" ]]; then
    ok "Frontend: HTTP $FRONT_CODE"
else
    fail "Frontend: HTTP $FRONT_CODE"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 3. Ergebnis / Wiederherstellung
if [[ $ERRORS -eq 0 ]]; then
    ok "System ist gesund."
    exit 0
fi

warn "$ERRORS Problem(e) gefunden."

if $FIX_MODE; then
    echo ""
    echo "--- Wiederherstellung ---"
    warn "Starte ausgefallene Container neu..."
    sudo docker compose -f "$COMPOSE_FILE" up -d
    echo ""
    echo "Warte 30 Sekunden auf Backend-Start..."
    sleep 30
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$BASE_URL/api/health" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        ok "System läuft wieder."
        exit 0
    else
        fail "Wiederherstellung fehlgeschlagen (HTTP $HTTP_CODE). Bitte Logs prüfen:"
        echo "  sudo docker compose -f $COMPOSE_FILE logs backend --tail=50"
        exit 1
    fi
else
    echo "Zum Beheben ausführen: $0 --fix"
    exit 1
fi
