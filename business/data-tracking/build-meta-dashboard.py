#!/usr/bin/env python3
"""
Rebuild meta-ads-dashboard-NOS.html with fresh Prospecting_CBO data.

Reads ACCESS_TOKEN + AD_ACCOUNT_ID from the environment (source
~/.config/meta-ads/.env first, or run via refresh-meta-dashboard.sh).
Pulls Prospecting_CBO insights from 2026-06-04 → today via Graph API v25.0,
bakes them into a standalone copy of meta-ads-dashboard-template.html.
"""
import json, os, sys, datetime, urllib.parse, urllib.request

HERE        = os.path.dirname(os.path.abspath(__file__))
TEMPLATE    = os.path.join(HERE, "meta-ads-dashboard-template.html")
OUT         = os.path.join(HERE, "meta-ads-dashboard-NOS.html")
CAMPAIGN_ID = "120246948101300371"     # Prospecting_CBO
SINCE       = "2026-06-04"             # PCBO launch
API         = "https://graph.facebook.com/v25.0"

TOKEN = os.environ.get("ACCESS_TOKEN")
ACCT  = os.environ.get("AD_ACCOUNT_ID", "act_3438890589494443")
if not TOKEN:
    sys.exit("ERROR: ACCESS_TOKEN not set. Run:  source ~/.config/meta-ads/.env  (or use refresh-meta-dashboard.sh)")

TODAY = datetime.date.today().isoformat()
TR    = json.dumps({"since": SINCE, "until": TODAY})

# ---- Cost model ----------------------------------------------------------
# COGS comes from cogs.json (real Medusa orders × live BV print cost + your
# dispatch step table, computed by compute-cogs.py — see refresh-meta-dashboard.sh).
# We bake the funnel COGS% as the dashboard default; the "Configure cost" modal
# still overrides. If cogs.json is missing, fall back to the estimate below.
#   Variable = Stripe processing per order (pct + fixed)
COGS_FILE = os.path.join(HERE, "cogs.json")
COST_INPUTS = {
    "pb_print_cost":   2.75,   # FALLBACK est: avg print/book if cogs.json missing
    "dispatch_cost":   4.50,   # FALLBACK est: dispatch/order if cogs.json missing
    "books_per_order": 3,      # funnel bundle = 3 books (fallback only)
    "ebook_share":     0.0,    # share of orders that are ebook-only (≈$0 COGS)
    "stripe_pct":      0.029,  # Stripe US card fee
    "stripe_fixed":    0.30,   # Stripe per-transaction fixed fee
    "avg_order_value": None,   # None → derive AOV from the window; or set a USD override
}


def get(path, params):
    params = dict(params); params["access_token"] = TOKEN
    url = "%s/%s?%s" % (API, path, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    if isinstance(data, dict) and data.get("error"):
        sys.exit("Graph API error: " + json.dumps(data["error"]))
    return data


def f(x):
    try: return float(x)
    except: return 0.0

def actval(actions, *types):
    if not isinstance(actions, list): return 0.0
    m = {a.get("action_type"): a.get("value") for a in actions}
    for t in types:
        if t in m:
            return f(m[t])
    return 0.0

def roasval(pr):
    if not isinstance(pr, list): return 0.0
    for x in pr:
        if x.get("action_type") in ("omni_purchase", "purchase", "offsite_conversion.fb_pixel_purchase"):
            return f(x.get("value"))
    return f(pr[0].get("value")) if pr else 0.0

def dayspan(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days + 1


def load_cogs():
    """Real COGS summary from cogs.json (compute-cogs.py), or None if absent."""
    try:
        with open(COGS_FILE) as fh:
            return json.load(fh)
    except Exception:
        return None


# 1) campaign daily
daily_raw = get("%s/insights" % CAMPAIGN_ID, {
    "time_increment": "1", "time_range": TR, "limit": "200",
    "fields": "spend,impressions,clicks,cpc,cpm,ctr,reach,frequency,actions,purchase_roas",
}).get("data", [])
DAILY = []
for r in daily_raw:
    DAILY.append({
        "date": r["date_start"],
        "spend": round(f(r.get("spend")), 2),
        "impressions": int(f(r.get("impressions"))),
        "clicks": int(f(r.get("clicks"))),
        "reach": int(f(r.get("reach"))),
        "results": int(actval(r.get("actions"), "purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase")),
        "roas": round(roasval(r.get("purchase_roas")), 4),
    })
DAILY.sort(key=lambda x: x["date"])

# 2) ad-level within the campaign
ad_raw = get("%s/insights" % CAMPAIGN_ID, {
    "level": "ad", "time_range": TR, "sort": "spend_descending", "limit": "100",
    "fields": "ad_id,ad_name,spend,impressions,clicks,cpc,cpm,ctr,actions,purchase_roas",
}).get("data", [])

# 3) created_time for those ads
ad_ids = [r["ad_id"] for r in ad_raw if r.get("ad_id")]
created = {}
if ad_ids:
    meta = get("", {"ids": ",".join(ad_ids), "fields": "created_time"})
    for k, v in meta.items():
        ct = v.get("created_time", "")
        created[k] = ct[:10] if ct else ""

ADS = []
for i, r in enumerate(ad_raw):
    spend = round(f(r.get("spend")), 2)
    purch = int(actval(r.get("actions"), "purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"))
    roas  = round(roasval(r.get("purchase_roas")), 4)
    c     = created.get(r.get("ad_id"), "")
    ADS.append({
        "id": r.get("ad_id", "ad%d" % i), "name": r.get("ad_name", "(unnamed ad)"),
        "created": c, "daysLive": dayspan(c, TODAY) if c else None,
        "spend": spend, "impressions": int(f(r.get("impressions"))), "clicks": int(f(r.get("clicks"))),
        "ctr": round(f(r.get("ctr")), 4), "cpc": round(f(r.get("cpc")), 4), "cpm": round(f(r.get("cpm")), 4),
        "purchases": purch, "results": purch, "roas": roas,
        "revenue": round(spend * roas, 2), "cpa": round(spend / purch, 2) if purch > 0 else 0,
    })
ADS.sort(key=lambda x: -x["spend"])

# 4) demographic breakdowns (campaign-level, whole window)
def demo_rows(breakdowns, segfn):
    raw = get("%s/insights" % CAMPAIGN_ID, {
        "time_range": TR, "limit": "500", "breakdowns": breakdowns,
        "fields": "spend,impressions,clicks,ctr,cpc,cpm,actions,purchase_roas",
    }).get("data", [])
    out = []
    for r in raw:
        spend = round(f(r.get("spend")), 2)
        impr  = int(f(r.get("impressions")))
        clk   = int(f(r.get("clicks")))
        purch = int(actval(r.get("actions"), "purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"))
        roas  = round(roasval(r.get("purchase_roas")), 4)
        out.append({
            "segment": segfn(r), "spend": spend, "impressions": impr, "clicks": clk,
            "ctr": round(clk / impr * 100, 4) if impr else 0.0,
            "cpc": round(spend / clk, 4) if clk else 0.0,
            "purchases": purch, "roas": roas,
            "revenue": round(spend * roas, 2),
            "cpa": round(spend / purch, 2) if purch > 0 else 0,
        })
    out.sort(key=lambda x: -x["spend"])
    return out

DEMO = {
    "ageGender": demo_rows("age,gender",
                           lambda r: "%s · %s" % (r.get("age", "?"), r.get("gender", "?"))),
    "platform":  demo_rows("publisher_platform,platform_position",
                           lambda r: "%s · %s" % (r.get("publisher_platform", "?"), r.get("platform_position", "?"))),
    "device":    demo_rows("impression_device",
                           lambda r: r.get("impression_device", "?")),
}

# 5) COGS% / variable% — real (cogs.json: Medusa orders × live BV print) or estimate
ci = COST_INPUTS
_tot_pur = sum(d["results"] for d in DAILY)
_tot_rev = sum(d["spend"] * d["roas"] for d in DAILY)
AOV = ci["avg_order_value"] or (_tot_rev / _tot_pur if _tot_pur else 0)

COGS = load_cogs()           # {by_class, total, funnel_cogs_pct, ...} or None
if COGS and COGS.get("funnel_cogs_pct"):
    COGS_PCT = round(float(COGS["funnel_cogs_pct"]), 1)
    fn = COGS["by_class"].get("funnel", {})
    cost_source = "Medusa actuals · %d funnel orders · $%.0f rev / $%.0f COGS" % (
        fn.get("orders", 0), fn.get("revenue", 0), fn.get("cogs", 0))
else:
    cogs_per_order = (ci["pb_print_cost"] * ci["books_per_order"] + ci["dispatch_cost"]) * (1 - ci["ebook_share"])
    COGS_PCT = round(cogs_per_order / AOV * 100, 1) if AOV > 0 else 35.0
    cost_source = "estimate · %d×$%.2f print + $%.2f dispatch (cogs.json missing)" % (
        ci["books_per_order"], ci["pb_print_cost"], ci["dispatch_cost"])

VAR_PCT = round((ci["stripe_pct"] * AOV + ci["stripe_fixed"]) / AOV * 100, 1) if AOV > 0 else 10.0
cogs_per_order = round(COGS_PCT / 100 * AOV, 2)   # implied per-order COGS for display
# business-health segments (funnel/catalog/total) for the dashboard, if available
HEALTH = (COGS or {}).get("by_class", {})
HEALTH_TOTAL = (COGS or {}).get("total", {})

snapshot = {"generated": TODAY, "account": "Prospecting_CBO · %s" % ACCT,
            "since": DAILY[0]["date"] if DAILY else SINCE, "until": DAILY[-1]["date"] if DAILY else TODAY}

block = (
    "/* ===== BAKED-IN LIVE DATA (generated %s via Graph API v25.0) ===== */\n" % TODAY
    + "const SNAPSHOT = " + json.dumps(snapshot) + ";\n"
    + "const EMBEDDED_DAILY = " + json.dumps(DAILY) + ";\n"
    + "const EMBEDDED_ADS = " + json.dumps(ADS) + ";\n"
    + "const EMBEDDED_DEMO = " + json.dumps(DEMO) + ";\n"
    + "const EMBEDDED_HEALTH = " + json.dumps({"by_class": HEALTH, "total": HEALTH_TOTAL, "source": cost_source}) + ";\n"
    + ("/* cost: AOV $%.2f → COGS %.1f%% ($%.2f/order · %s) + var %.1f%% (Stripe %.1f%%+$%.2f) */\n"
       % (AOV, COGS_PCT, cogs_per_order, cost_source, VAR_PCT, ci["stripe_pct"] * 100, ci["stripe_fixed"]))
    + "const USE_EMBEDDED = true;\n"
    + """function groupReal(daily, gran){
  daily = daily.slice().sort((a,b)=>a.date<b.date?-1:1);
  if(gran==="1") return daily;
  let groups=[];
  if(gran==="7"){ for(let i=0;i<daily.length;i+=7) groups.push(daily.slice(i,i+7)); }
  else { const map={}; daily.forEach(r=>{const k=r.date.slice(0,7);(map[k]=map[k]||[]).push(r);});
    Object.keys(map).sort().forEach(k=>groups.push(map[k])); }
  return groups.filter(g=>g.length).map(g=>{
    const t={spend:0,impressions:0,clicks:0,reach:0,results:0,revenue:0};
    g.forEach(r=>{t.spend+=r.spend;t.impressions+=r.impressions;t.clicks+=r.clicks;t.reach+=r.reach;t.results+=(r.results||0);t.revenue+=r.spend*r.roas;});
    return {date:g[0].date, spend:+t.spend.toFixed(2), impressions:t.impressions, clicks:t.clicks,
      reach:t.reach, results:t.results, roas:t.spend>0?+(t.revenue/t.spend).toFixed(4):0};
  });
}
""")

src = open(TEMPLATE).read()

def rep(s, old, new):
    assert old in s, "MISSING anchor: %r" % old[:60]
    return s.replace(old, new, 1)

src = rep(src, 'const ACCOUNT_ID = "YOUR_AD_ACCOUNT_ID";', 'const ACCOUNT_ID = "%s";' % ACCT.replace("act_", ""))
src = rep(src, 'const TOOL = "mcp__YOUR_META_ADS_MCP__ads_get_ad_entities";',
               'const TOOL = "mcp__claude_ai_FB_Ads_MCP__ads_get_ad_entities";')
src = rep(src, 'const LS = "meta_dash_v1";', 'const LS = "meta_dash_nos_v1";')
src = rep(src, 'cost: {cogsPct:35, varPct:10, fixedMo:0},',
               'cost: {cogsPct:%s, varPct:%s, fixedMo:0},' % (COGS_PCT, VAR_PCT))
src = rep(src, """  targets: [
    {id:"t1", label:"CPA (efficiency)", metric:"cpa", value:35},
    {id:"t2", label:"Spend", metric:"spend", value:20000},
    {id:"t3", label:"Meta Contribution Margin", metric:"cm", value:15000},
  ],""", """  targets: [
    {id:"t1", label:"ROAS (king goal)", metric:"roas", value:1.65},
    {id:"t2", label:"CPA (cost / purchase)", metric:"cpa", value:35},
    {id:"t3", label:"Ad Spend (range)", metric:"spend", value:3000},
  ],""")
src = rep(src, 'range:null, // {from,to}', 'range:{from:"%s",to:"%s"}, // {from,to}' % (snapshot["since"], snapshot["until"]))
src = rep(src, 'const USE_DUMMY = true;', 'const USE_DUMMY = false;')
src = rep(src, "let RAW_ROWS=[];", block + "\nlet RAW_ROWS=[];")
src = rep(src, """async function fetchData(){
  const r = currentRange();
  const gran = state.granularity;
  if(USE_DUMMY){""", """async function fetchData(){
  const r = currentRange();
  const gran = state.granularity;
  if(typeof USE_EMBEDDED!=="undefined" && USE_EMBEDDED){
    const daily = EMBEDDED_DAILY.filter(d=>d.date>=r.from && d.date<=r.to);
    RAW_ROWS = groupReal(daily, gran);
    AD_ROWS = EMBEDDED_ADS.slice();
    DEMO = EMBEDDED_DEMO;
    HEALTH = (typeof EMBEDDED_HEALTH!=="undefined") ? EMBEDDED_HEALTH : null;
    const ps = daily.reduce((a,b)=>a+(b.results||0),0);
    PERIOD_PURCHASES = ps>0?ps:null;
    showBanner("info", `Baked live snapshot · ${SNAPSHOT.account} · data ${SNAPSHOT.since} → ${SNAPSHOT.until} (generated ${SNAPSHOT.generated}). Static — re-run the build to refresh.`);
    setStatus("ok","");
    renderAll();
    return;
  }
  if(USE_DUMMY){""")
src = rep(src, 'if(USE_DUMMY || (window.cowork && window.cowork.callMcpTool)){ fetchData(); }',
               'if((typeof USE_EMBEDDED!=="undefined" && USE_EMBEDDED) || USE_DUMMY || (window.cowork && window.cowork.callMcpTool)){ fetchData(); }')

open(OUT, "w").write(src)

tot = sum(d["spend"] for d in DAILY); pur = sum(d["results"] for d in DAILY)
rev = sum(d["spend"] * d["roas"] for d in DAILY)
print("Wrote %s" % OUT)
print("  %s -> %s | %d days, %d ads" % (snapshot["since"], snapshot["until"], len(DAILY), len(ADS)))
print("  spend $%.2f | purchases %d | blended ROAS %.2fx" % (tot, pur, rev / tot if tot else 0))
print("  cost: AOV $%.2f | COGS %.1f%% ($%.2f/order) | variable %.1f%% (Stripe)"
      % (AOV, COGS_PCT, cogs_per_order, VAR_PCT))
print("  cost source: %s" % cost_source)
print("  demographics: %d age×gender, %d placement, %d device segments"
      % (len(DEMO["ageGender"]), len(DEMO["platform"]), len(DEMO["device"])))
