#!/usr/bin/env bash
# Refresh meta-ads-dashboard-NOS.html with the latest Prospecting_CBO data.
# Pulls FB ad insights + real Medusa orders (read-only) + live BV print cost.
# Usage:  ./refresh-meta-dashboard.sh
set -euo pipefail
HERE="$(dirname "$0")"
set -a; . "$HOME/.config/meta-ads/.env"; set +a

SINCE="${COGS_SINCE:-2026-06-04}"   # keep aligned with build-meta-dashboard.py SINCE
REPO="$HOME/Documents/2_Projects/tmp/charliechan/NOS"
ORDERS=/tmp/nos-cogs-orders.json
COGS="$HERE/cogs.json"

# 1) real COGS: pull paid orders from prod Medusa (read-only) → BV print + shipping.
#    Best-effort: on any failure the dashboard build falls back to the estimate.
if [ -f "$REPO/backend/src/scripts/cogs-orders.cjs" ]; then
  echo "Pulling Medusa orders since $SINCE (read-only)…"
  set +e   # railway ssh exits non-zero on its agent-tooling notice; don't let it abort
  B64=$(base64 -w0 "$REPO/backend/src/scripts/cogs-orders.cjs")
  railway ssh --project 3f81ffdb-8676-4e44-b460-131fe6d32b5a --environment production --service NOS_prod \
    -i "$HOME/.ssh/railway-nos" \
    "echo $B64 | base64 -d > /tmp/co.cjs && cd /app && SINCE=$SINCE NODE_PATH=/app/node_modules node /tmp/co.cjs" \
    2>/dev/null | grep -v "agent tooling\|railway setup" > "$ORDERS"
  set -e
  if [ -s "$ORDERS" ] && python3 -c "import json,sys; json.load(open('$ORDERS'))" 2>/dev/null; then
    python3 "$HERE/compute-cogs.py" --orders "$ORDERS" > "$COGS" && echo "  COGS computed → cogs.json"
  else
    echo "  (Medusa pull failed — dashboard will use the cost estimate)"; rm -f "$COGS"
  fi
fi

# 1b) THE VAULT OPENS (BFCM 2026) results: read-only order pull → bfcm.json (best-effort).
if [ -f "$REPO/backend/src/scripts/bfcm-results.cjs" ]; then
  echo "Pulling BFCM vault orders (read-only)…"
  set +e
  B64=$(base64 -w0 "$REPO/backend/src/scripts/bfcm-results.cjs")
  railway ssh --project 3f81ffdb-8676-4e44-b460-131fe6d32b5a --environment production --service NOS_prod \
    -i "$HOME/.ssh/railway-nos" \
    "echo $B64 | base64 -d > /tmp/br.cjs && cd /app && NODE_PATH=/app/node_modules node /tmp/br.cjs" \
    2>/dev/null | grep -v "agent tooling\|railway setup" > /tmp/nos-bfcm-orders.json
  set -e
  if [ -s /tmp/nos-bfcm-orders.json ] && python3 -c "import json; json.load(open('/tmp/nos-bfcm-orders.json'))" 2>/dev/null; then
    python3 "$HERE/build-bfcm-results.py" --orders /tmp/nos-bfcm-orders.json || echo "  (BFCM results build failed)"
  else
    echo "  (BFCM pull failed — section left as last built)"
  fi
fi

# 2) build the dashboard (reads cogs.json if present)
python3 "$HERE/build-meta-dashboard.py"

# 3) build the account-level anomaly detector (best-effort)
if [ -f "$HERE/anomaly_detector_shareable.html" ]; then
  python3 "$HERE/build-anomaly-detector.py" || echo "  (anomaly detector build skipped)"
fi
