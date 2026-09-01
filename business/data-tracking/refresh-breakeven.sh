#!/usr/bin/env bash
# refresh-breakeven.sh — rebuild the live break-even model.
#
#   ./refresh-breakeven.sh            # last 90 days of orders
#   SINCE=2026-06-01 ./refresh-breakeven.sh
#
# Read-only against production. Needs ~/.config/meta-ads/.env (ACCESS_TOKEN,
# AD_ACCOUNT_ID, BOOKVAULT_API_KEY) and the railway-nos ssh key.
set -euo pipefail
cd "$(dirname "$0")"

set -a; . ~/.config/meta-ads/.env; set +a
: "${ACCESS_TOKEN:?missing ACCESS_TOKEN}"; : "${BOOKVAULT_API_KEY:?missing BOOKVAULT_API_KEY}"

# Default to the start of the Medusa era so no reporting window is clipped.
SINCE="${SINCE:-2026-06-01}"
UNTIL="$(date +%F)"
RAILWAY_PROJECT=3f81ffdb-8676-4e44-b460-131fe6d32b5a

echo "▸ orders since $SINCE (read-only, prod)"
B64=$(base64 -w0 pnl-orders.cjs)
railway ssh --project "$RAILWAY_PROJECT" --environment production --service NOS_prod \
  -i ~/.ssh/railway-nos \
  "echo $B64 | base64 -d > /tmp/pnl.cjs && cd /app && SINCE=$SINCE NODE_PATH=/app/node_modules node /tmp/pnl.cjs" \
  2>/dev/null | sed -n 's/^\(\[.*\)$/\1/p' > pnl-orders.json
python3 -c "import json;d=json.load(open('pnl-orders.json'));print(f'  {len(d)} orders')"

echo "▸ ad spend by day, $SINCE → $UNTIL"
# NB: /insights paginates at 25 rows by default — a 90-day daily series needs
# limit AND paging, or spend comes back silently truncated and ROAS reads high.
python3 - "$SINCE" "$UNTIL" <<'PYP'
import json,os,sys,urllib.parse,urllib.request
since,until=sys.argv[1],sys.argv[2]
url=("https://graph.facebook.com/v25.0/act_%s/insights?" % os.environ["AD_ACCOUNT_ID"].removeprefix("act_")) + urllib.parse.urlencode({
    "level":"account","time_increment":"1","limit":"500",
    "time_range":json.dumps({"since":since,"until":until}),
    "fields":"spend","access_token":os.environ["ACCESS_TOKEN"]})
d={}
while url:
    with urllib.request.urlopen(url, timeout=60) as r: page=json.load(r)
    for row in page.get("data",[]): d[row["date_start"]]=float(row["spend"])
    url=(page.get("paging") or {}).get("next")
json.dump(d,open("spend.json","w"))
print(f"  {len(d)} days, ${sum(d.values()):,.2f}")
PYP

echo "▸ model (live BookVault print costs — takes a moment)"
python3 build-breakeven.py --orders pnl-orders.json --spend spend.json --since "$SINCE"

echo "▸ done → breakeven-NOS.html"
