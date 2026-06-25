#!/usr/bin/env python3
"""
compute-cogs.py — real funnel/catalog COGS from Medusa orders + BV print cost.

Pipeline:
  1. orders JSON (from backend/src/scripts/cogs-orders.cjs over railway ssh) on stdin
     or --orders <file>.
  2. live per-ISBN US print cost from BookVAULT GET /Title (needs BOOKVAULT_API_KEY).
  3. group each main order with its PPU children (ship in one box), apply the
     dispatch step table, sum print, and aggregate revenue/COGS by class.

Emits a JSON summary on stdout: per-class {orders, revenue, cogs, margin, cogs_pct}
plus a baked-ready funnel cogs_pct. Read-only; no writes to prod.
"""
import json, os, sys, urllib.parse, urllib.request

BV_API = "https://api.bookvault.app/v3"
BV_KEY = os.environ.get("BOOKVAULT_API_KEY")
AVG_PRINT = 2.72  # fallback per-book print for PPU books with no resolvable ISBN

# Dispatch (BV DispatchCost) per ORDER by paperback count — Rich's validated table.
def shipping(pb_count):
    if pb_count <= 0:  return 0.0
    if pb_count == 1:  return 6.43
    if pb_count <= 4:  return 7.42
    if pb_count <= 7:  return 8.41
    if pb_count <= 10: return 9.40
    return 9.40 + 0.99 * ((pb_count - 10 + 2) // 3)  # rough extrapolation past 10

_print_cache = {}
def print_cost(isbn):
    if isbn in _print_cache:
        return _print_cache[isbn]
    cost = AVG_PRINT
    try:
        url = "%s/Title?%s" % (BV_API, urllib.parse.urlencode({"ISBN": isbn}))
        req = urllib.request.Request(url, headers={
            "Authorization": "basic " + BV_KEY, "Accept": "application/json", "User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.load(r)
        t = d[0] if isinstance(d, list) and d else d
        for p in (t.get("Pricing") or []):
            if (p.get("Partner") or {}).get("Name") == "Bookvault US":
                cost = float(p.get("Price") or AVG_PRINT); break
    except Exception as e:
        sys.stderr.write("BV print lookup failed for %s (%s); using avg\n" % (isbn, e))
    _print_cache[isbn] = cost
    return cost

def ppu_books(order):
    """(count, is_paperback) for a PPU order, parsed from its line title."""
    n, pb = 0, False
    for l in order.get("lines_raw", []):
        title = (l.get("title") or "")
        cnt = title.count(" + ") + 1 if " + " in title else 1
        if "ebook" in title.lower():
            pass  # ebook PPU → no print/shipping
        elif "paperback" in title.lower():
            n += cnt * int(l.get("qty") or 1); pb = True
    return n, pb

def main():
    src = None
    if "--orders" in sys.argv:
        src = sys.argv[sys.argv.index("--orders") + 1]
    raw = open(src).read() if src else sys.stdin.read()
    orders = json.loads(raw)
    by_id = {o["id"]: o for o in orders}

    # bucket PPUs under their parent main order
    ppu_children = {}
    for o in orders:
        if o["class"] == "ppu":
            ppu_children.setdefault(o.get("original_order_id"), []).append(o)

    # funnel includes content_name-less "unknown" orders that carry Brady bundles
    def cls(o):
        if o["class"] == "unknown":
            return "funnel" if o["pb_count"] > 0 or o["has_ebook"] else "funnel"
        return o["class"]

    agg = {}
    def add(c, rev, cogs):
        a = agg.setdefault(c, {"orders": 0, "revenue": 0.0, "cogs": 0.0})
        a["orders"] += 1; a["revenue"] += rev; a["cogs"] += cogs

    orphan_ppu_rev = 0.0; orphan_ppu_cogs = 0.0; orphan_ppu_n = 0
    for o in orders:
        if o["class"] == "ppu":
            if o.get("original_order_id") in by_id:
                continue  # folded into its parent shipment below
            # orphan PPU (parent outside window): treat standalone
            n, pb = ppu_books(o)
            cogs = AVG_PRINT * n + shipping(n)
            orphan_ppu_rev += o["revenue"]; orphan_ppu_cogs += cogs; orphan_ppu_n += 1
            continue

        # main order (+ its PPU children) = one shipment
        pb_isbns = list(o["pb_isbns"])
        rev = o["revenue"]
        ppu_pb = 0
        for ch in ppu_children.get(o["id"], []):
            rev += ch["revenue"]
            n, pb = ppu_books(ch)
            ppu_pb += n
        print_total = sum(print_cost(i) for i in pb_isbns) + AVG_PRINT * ppu_pb
        ship = shipping(len(pb_isbns) + ppu_pb)
        add(cls(o), rev, print_total + ship)

    if orphan_ppu_n:
        a = agg.setdefault("funnel", {"orders": 0, "revenue": 0.0, "cogs": 0.0})
        a["orders"] += orphan_ppu_n; a["revenue"] += orphan_ppu_rev; a["cogs"] += orphan_ppu_cogs

    total = {"orders": 0, "revenue": 0.0, "cogs": 0.0}
    for c, a in agg.items():
        for k in total: total[k] += a[k]
    for a in list(agg.values()) + [total]:
        a["margin"] = round(a["revenue"] - a["cogs"], 2)
        a["cogs_pct"] = round(a["cogs"] / a["revenue"] * 100, 1) if a["revenue"] else 0.0
        a["revenue"] = round(a["revenue"], 2); a["cogs"] = round(a["cogs"], 2)

    result = {"by_class": agg, "total": total,
              "funnel_cogs_pct": agg.get("funnel", {}).get("cogs_pct", 0.0),
              "print_costs": _print_cache}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
