#!/usr/bin/env python3
"""
build-breakeven.py — Sam Piliero's break-even calculator, fed from live data.

Replaces hand-entered guesses with measured inputs:
  orders / AOV / revenue   → prod Medusa (pnl-orders.cjs)
  COGS                     → live BookVault per-ISBN print cost (compute-cogs.py)
  fixed costs              → fixed-costs.json
  ad spend                 → Meta Graph API

Break-even ROI here INCLUDES fixed costs, matching Sam's sheet. Note the target
is not a constant: catalog orders cost ~28% to deliver vs the funnel's ~35%, so
break-even falls as catalog share rises.

  python3 build-breakeven.py --orders pnl-orders.json --spend spend.json
Writes breakeven-NOS.html.
"""
import json, os, sys, datetime, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))

# reuse compute-cogs.py's proven BV lookup + dispatch table rather than copying it
spec = importlib.util.spec_from_file_location("cc", os.path.join(HERE, "compute-cogs.py"))
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)

TEST_PAT = ("richthewriterguy+", "txthruxton+", "@example.", ".test", ".invalid", "smoke@")

def is_test(e):
    e = (e or "").lower()
    return any(p in e for p in TEST_PAT)

def cogs_for(orders):
    """Print + dispatch for a set of orders, PPUs grouped into the parent shipment."""
    by_id = {o["id"]: o for o in orders}
    kids = {}
    for o in orders:
        if o["class"] == "ppu":
            kids.setdefault(o.get("original_order_id"), []).append(o)
    total = 0.0
    for o in orders:
        if o["class"] == "ppu" and o.get("original_order_id") in by_id:
            continue  # counted with its parent
        pb = list(o["pb_isbns"])
        for k in kids.get(o["id"], []):
            pb += k["pb_isbns"]
            n, is_pb = cc.ppu_books(k)
            if is_pb and not k["pb_isbns"]:
                pb += ["?"] * n
        total += sum(cc.print_cost(i) if i != "?" else cc.AVG_PRINT for i in pb)
        total += cc.shipping(len(pb))
    return round(total, 2)

def model(rows, spend, fixed_month, days, cfg):
    rev = sum(o["revenue"] for o in rows)
    n = len(rows)
    if not n or rev <= 0:
        return None
    cogs = cogs_for(rows)
    fees = rev * cfg["stripe_pct"] + n * cfg["stripe_fixed"]
    fixed = fixed_month * (days / 30.4)
    be_spend = rev - cogs - fees - fixed
    cat = sum(o["revenue"] for o in rows if o["class"] == "catalog")
    return dict(
        days=days, orders=n, aov=rev / n, revenue=rev,
        cogs=cogs, cogs_pct=cogs / rev * 100, fees=fees, fixed=fixed,
        be_spend=be_spend,
        be_roi=(rev / be_spend) if be_spend > 0 else None,
        be_cpa=be_spend / n, be_spend_pct=be_spend / rev * 100,
        spend=spend, roas=(rev / spend) if spend else None,
        profit=rev - cogs - fees - fixed - spend,
        catalog_share=cat / rev * 100,
    )

def money(v):  return f"${v:,.2f}"
def pct(v):    return f"{v:.1f}%"

def render(windows, cfg, fixed_month, generated):
    def card(w, name):
        if not w: return f'<div class="win"><h3>{name}</h3><p class="muted">No orders in window.</p></div>'
        ok = w["profit"] >= 0
        roas = f'{w["roas"]:.2f}&times;' if w["roas"] else "—"
        be   = f'{w["be_roi"]:.2f}&times;' if w["be_roi"] else "—"
        cls  = "pos" if ok else "neg"
        verdict = f'PROFIT {money(w["profit"])}' if ok else f'LOSS ({money(abs(w["profit"]))})'
        return f'''<div class="win">
  <h3>{name}</h3>
  <div class="hero"><div><span class="lbl">Actual ROAS</span><span class="big {cls}">{roas}</span></div>
    <div><span class="lbl">Break-even</span><span class="big">{be}</span></div></div>
  <div class="verdict {cls}">{verdict} <span class="muted">over {w["days"]} days</span></div>
  <table>
    <tr><td>Orders</td><td>{w["orders"]:,}</td></tr>
    <tr><td>AOV</td><td>{money(w["aov"])}</td></tr>
    <tr><td>Revenue</td><td>{money(w["revenue"])}</td></tr>
    <tr><td>COGS</td><td>{money(w["cogs"])} <span class="muted">({pct(w["cogs_pct"])})</span></td></tr>
    <tr><td>Payment fees</td><td>{money(w["fees"])}</td></tr>
    <tr><td>Fixed costs</td><td>{money(w["fixed"])}</td></tr>
    <tr class="rule"><td>Break-even ad spend</td><td>{money(w["be_spend"])} <span class="muted">({pct(w["be_spend_pct"])})</span></td></tr>
    <tr><td>Break-even CPA</td><td>{money(w["be_cpa"])}</td></tr>
    <tr><td>Actual ad spend</td><td>{money(w["spend"])}</td></tr>
    <tr class="rule"><td>Catalogue share</td><td>{pct(w["catalog_share"])}</td></tr>
  </table>
</div>'''
    cards = "\n".join(card(w, n) for n, w in windows)
    costs = "".join(f"<tr><td>{k}</td><td>{money(v)}</td></tr>" for k, v in
                    sorted(cfg["costs"].items(), key=lambda x: -x[1]))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Break-even — Tales of Murder Press</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{{--paper:#F0F2EF;--panel:#F7F8F6;--ink:#1B2430;--soft:#55646C;--rule:#CBD4D0;--strong:#9BA9A4;--red:#9E2B25;--green:#2E6B4F;--blue:#38607F}}
@media(prefers-color-scheme:dark){{:root{{--paper:#141A1E;--panel:#1A2126;--ink:#E4E9E6;--soft:#94A3A9;--rule:#2A343A;--strong:#425057;--red:#E0736C;--green:#6FBF95;--blue:#84AECC}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:48px 24px 80px}}
h1{{font-family:"Libre Baskerville",Georgia,serif;font-size:clamp(1.7rem,4vw,2.4rem);margin:0;line-height:1.2}}
h2,h3{{font-family:"Libre Baskerville",Georgia,serif;margin:0}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;color:var(--soft)}}
header{{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:28px}}
.sub{{color:var(--soft);margin:10px 0 0;max-width:62ch}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}}
.win{{background:var(--panel);border:1px solid var(--rule);border-radius:2px;padding:20px}}
.win h3{{font-size:1.05rem;margin-bottom:14px}}
.hero{{display:flex;gap:24px;margin-bottom:12px}}
.lbl{{display:block;font-family:"IBM Plex Mono",monospace;font-size:.63rem;letter-spacing:.12em;text-transform:uppercase;color:var(--soft)}}
.big{{font-family:"IBM Plex Mono",monospace;font-size:1.7rem;font-weight:600;font-variant-numeric:tabular-nums}}
.verdict{{font-family:"IBM Plex Mono",monospace;font-size:.9rem;font-weight:600;padding:7px 10px;border-radius:2px;margin-bottom:14px}}
.verdict.pos{{background:#2E6B4F1a;color:var(--green)}} .verdict.neg{{background:#9E2B251a;color:var(--red)}}
.pos{{color:var(--green)}} .neg{{color:var(--red)}} .muted{{color:var(--soft);font-weight:400}}
table{{width:100%;border-collapse:collapse;font-size:.92rem}}
td{{padding:6px 0;border-bottom:1px solid var(--rule)}}
td:last-child{{text-align:right;font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}}
tr.rule td{{border-top:1px solid var(--strong)}}
tr:last-child td{{border-bottom:none}}
section{{margin-top:40px}}
.note{{color:var(--soft);font-size:.9rem;max-width:70ch;margin-top:14px}}
footer{{margin-top:48px;padding-top:16px;border-top:1px solid var(--rule);color:var(--soft);font-size:.83rem}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">Tales of Murder Press &middot; live break-even model</div>
  <h1>What it takes to break even</h1>
  <p class="sub">Sam Piliero's calculator with measured inputs instead of estimates. Orders,
  AOV and revenue from production Medusa; COGS from live BookVault print costs; ad spend from
  the Meta API; fixed costs from <code>fixed-costs.json</code>. Break-even ROI includes fixed costs.</p>
</header>
<div class="grid">{cards}</div>
<section>
  <h2>Fixed costs — {money(fixed_month)}/month</h2>
  <div class="win" style="margin-top:14px;max-width:420px"><table>{costs}
  <tr class="rule"><td><b>Total</b></td><td><b>{money(fixed_month)}</b></td></tr></table></div>
  <p class="note">Edit <code>fixed-costs.json</code> and re-run. BookVault sits in COGS and
  Stripe is computed per transaction, so neither appears here.</p>
</section>
<section>
  <h2>Reading this</h2>
  <p class="note"><b>Break-even ROI is not a fixed target.</b> Catalogue orders cost roughly 28%
  to deliver against the funnel's 35%, so the more the back catalogue sells, the lower the bar
  drops — toward a floor near 1.45&times; at an all-catalogue mix. Compare each window's
  break-even against its own catalogue share rather than carrying one number forward.</p>
  <p class="note"><b>LTV is deliberately absent.</b> The original sheet assumed $250 and built a
  twelve-month projection on it; measured LTV is far lower and still moving. Nothing here depends
  on a number that has not been observed.</p>
</section>
<footer>Generated {generated} &middot; <code>refresh-breakeven.sh</code></footer>
</div></body></html>'''

def main():
    a = sys.argv
    orders_f = a[a.index("--orders") + 1]
    spend_f  = a[a.index("--spend") + 1]
    cfg = json.load(open(os.path.join(HERE, "fixed-costs.json")))
    fixed_month = sum(cfg["costs"].values())
    rows = [o for o in json.load(open(orders_f)) if not is_test(o.get("email"))]
    spend = json.load(open(spend_f))            # {"YYYY-MM-DD": float}

    today = datetime.date.today()
    # Compare against the PULL date, not the first order date — a quiet stretch
    # with no orders is not the same as missing data. Clipping a window silently
    # would understate revenue and inflate ROAS.
    pulled_since = a[a.index("--since") + 1] if "--since" in a else None

    def window(label, start, end):
        s, e = start.isoformat(), end.isoformat()
        if pulled_since and s < pulled_since:
            print(f"  !! {label}: starts {s} but orders were only pulled from "
                  f"{pulled_since} — re-run with SINCE={s}", file=sys.stderr)
            return label, None
        sel = [o for o in rows if s <= o["created_at"][:10] <= e]
        sp  = sum(v for k, v in spend.items() if s <= k <= e)
        d   = (end - start).days + 1
        return label, model(sel, sp, fixed_month, d, cfg)

    y = today - datetime.timedelta(days=1)      # exclude today (partial)
    wins = [
        window("Last 7 complete days",  y - datetime.timedelta(days=6),  y),
        window("Last 30 complete days", y - datetime.timedelta(days=29), y),
        window("June–August baseline",  datetime.date(2026, 6, 1), datetime.date(2026, 8, 31)),
    ]
    html = render(wins, cfg, fixed_month, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    out = os.path.join(HERE, "breakeven-NOS.html")
    open(out, "w").write(html)
    print("wrote", out)
    for n, w in wins:
        if w: print(f"  {n:24} ROAS {w['roas'] or 0:.2f}x  break-even {w['be_roi'] or 0:.2f}x  "
                    f"AOV ${w['aov']:.2f}  COGS {w['cogs_pct']:.1f}%  profit ${w['profit']:,.2f}")

if __name__ == "__main__":
    main()
