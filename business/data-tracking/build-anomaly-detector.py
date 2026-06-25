#!/usr/bin/env python3
"""
build-anomaly-detector.py — populate anomaly_detector_shareable.html with real
ACCOUNT-LEVEL daily metrics (last 60 days) from the Meta Graph API and write
meta-anomaly-detector-NOS.html.

The MCP can't reach the live account (rollout gate), so we use the same Graph
token as the dashboard. Reads ACCESS_TOKEN + AD_ACCOUNT_ID from the environment
(source ~/.config/meta-ads/.env, or run via refresh-meta-dashboard.sh).
"""
import calendar, datetime, json, os, re, sys, urllib.parse, urllib.request

HERE     = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "anomaly_detector_shareable.html")
OUT      = os.path.join(HERE, "meta-anomaly-detector-NOS.html")
API      = "https://graph.facebook.com/v25.0"
LOOKBACK = 60   # days of history (covers the 30-day baseline + prev windows)

TOKEN = os.environ.get("ACCESS_TOKEN")
ACCT  = os.environ.get("AD_ACCOUNT_ID", "act_3438890589494443")
if not TOKEN:
    sys.exit("ERROR: ACCESS_TOKEN not set. Run:  source ~/.config/meta-ads/.env")

def f(x):
    try: return float(x)
    except: return 0.0

def actval(actions, *types):
    if not isinstance(actions, list): return 0.0
    m = {a.get("action_type"): a.get("value") for a in actions}
    for t in types:
        if t in m: return f(m[t])
    return 0.0

def roasval(pr):
    if not isinstance(pr, list): return 0.0
    for x in pr:
        if x.get("action_type") in ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase"):
            return f(x.get("value"))
    return f(pr[0].get("value")) if pr else 0.0

today   = datetime.date.today()
end_day = today - datetime.timedelta(days=1)   # last COMPLETE day (exclude partial today)
since   = (end_day - datetime.timedelta(days=LOOKBACK)).isoformat()
until   = end_day.isoformat()
tr = json.dumps({"since": since, "until": until})

url = "%s/%s/insights?%s" % (API, ACCT, urllib.parse.urlencode({
    "access_token": TOKEN, "level": "account", "time_increment": "1", "limit": "500",
    "time_range": tr, "fields": "spend,impressions,clicks,actions,purchase_roas",
}))
with urllib.request.urlopen(url, timeout=60) as r:
    data = json.load(r)
if isinstance(data, dict) and data.get("error"):
    sys.exit("Graph API error: " + json.dumps(data["error"]))

rows = []
for d in sorted(data.get("data", []), key=lambda x: x.get("date_start", "")):
    iso   = d.get("date_start", "")
    dt    = datetime.date.fromisoformat(iso)
    spend = round(f(d.get("spend")), 2)
    roas  = roasval(d.get("purchase_roas"))
    rows.append({
        "date": "%s %d, %d" % (calendar.month_name[dt.month], dt.day, dt.year),
        "ts":   int(datetime.datetime(dt.year, dt.month, dt.day).timestamp() * 1000),
        "spend": spend,
        "impr":  int(f(d.get("impressions"))),
        "clicks": int(f(d.get("clicks"))),
        "purch": int(actval(d.get("actions"), "purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase")),
        "revenue": round(spend * roas, 2),
    })

if not rows:
    sys.exit("No insights rows returned for %s..%s — nothing to bake." % (since, until))

rng = "%s → %s · %d days · account %s" % (rows[0]["date"], rows[-1]["date"], len(rows), ACCT)
gen = today.isoformat()

new_fetch = (
    "// BAKED-IN LIVE DATA — account-level daily metrics via Graph API v25.0 (generated %s).\n" % gen
    + "const EMBEDDED_DAYS = " + json.dumps(rows) + ";\n"
    + "async function fetchData(){\n"
    + "  document.getElementById('rangelbl').textContent = %s;\n" % json.dumps("live · " + rng)
    + "  return EMBEDDED_DAYS;\n"
    + "}"
)

src = open(TEMPLATE).read()

def rep(s, pattern, repl, is_re=False):
    if is_re:
        new, n = re.subn(pattern, repl, s, count=1, flags=re.S)
        assert n == 1, "MISSING regex anchor: %r" % pattern[:50]
        return new
    assert pattern in s, "MISSING anchor: %r" % pattern[:60]
    return s.replace(pattern, repl, 1)

src = rep(src, r"// SYNTHETIC SAMPLE DATA.*?return rows;\n\}", lambda _: new_fetch, is_re=True)
src = rep(src, "const ACCT = 'DEMO';   // synthetic demo — not linked to any ad account",
               "const ACCT = '%s';   // live account" % ACCT)
src = rep(src, "<b>Demo</b> · sample data · daily account-level metrics · baseline = trailing 30 complete days · ",
               "<b>Live</b> · daily account-level metrics · baseline = trailing 30 complete days · ")
src = rep(src, "    This is a self-contained demo populated with synthetic sample data — it is not connected to any ad account.",
               "    Live account-level data baked from the Meta Graph API (generated %s). Re-run build-anomaly-detector.py to refresh." % gen)

open(OUT, "w").write(src)
flagged = "ROAS %.2fx, CPA $%.2f (last day)" % (
    (rows[-1]["revenue"] / rows[-1]["spend"]) if rows[-1]["spend"] else 0,
    (rows[-1]["spend"] / rows[-1]["purch"]) if rows[-1]["purch"] else 0)
print("Wrote %s" % OUT)
print("  %s" % rng)
print("  latest day: %s | spend $%.2f | %s" % (rows[-1]["date"], rows[-1]["spend"], flagged))
