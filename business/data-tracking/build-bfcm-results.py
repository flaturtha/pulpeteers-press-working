#!/usr/bin/env python3
"""
build-bfcm-results.py — THE VAULT OPENS (BFCM 2026) results for the Meta dashboard.

Reads the read-only order export from NOS backend/src/scripts/bfcm-results.cjs
(--orders /tmp/nos-bfcm-orders.json) and writes bfcm.json, which
build-meta-dashboard.py renders as the "THE VAULT OPENS — results" section.

Contribution = net revenue − Bookvault print (live per-ISBN price, cached) −
Bookvault dispatch (book-count table, PPUs ride in their parent's box) − Stripe
(2.9% + $0.30 per charge). Before ad spend. Same cost model as compute-cogs.py.
"""
import argparse, importlib.util, json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cc", os.path.join(HERE, "compute-cogs.py"))
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)

ISBN = re.compile(r"^\d{10,13}$")
CT = timezone(timedelta(hours=-6))
NEW_LIBS = {"sax-rohmer": "Sax Rohmer", "vintage-true-crime": "Vintage True Crime", "gothic-mysteries": "Wilkie Collins",
            "essential-detectives": "Essential Detectives", "nick-carter-library": "Nick Carter"}
SERIES = {**NEW_LIBS, "brady-series": "Bradys", "old-cap-collier": "Old Cap Collier"}

def offer_of(l):
    """Which offer a line is: (group, label)."""
    k, key = l.get("bundle_kind"), l.get("pack_key") or ""
    fmt = "PB" if re.search(r"paperback", l.get("title") or "", re.I) or (l.get("handle") or "").endswith("-pb") else "EB"
    if k == "sampler": return ("Sampler", f"Vintage Mystery Sampler {fmt}")
    if k == "collection": return ("Library bundle", f"{NEW_LIBS.get(key, key)} (5) {fmt}")
    if k == "addon": return ("Completion add-on", f"{NEW_LIBS.get(key.replace('addon-', ''), key)} add-on (4) {fmt}")
    if k == "all": return ("All 25", f"All 25 new {fmt}")
    if k == "bradys": return ("Complete Bradys", f"Complete Bradys (32) {fmt}")
    if l.get("mega_pack"): return ("Old Cap pack", f"Old Cap pack {key} {fmt}")
    if (l.get("handle") or "").startswith(("vault-", "occ-mega-")): return ("Other bundle", l.get("title"))
    col = l.get("collection") or ""
    if col == "swag" or re.search(r"\b(tee|mug|sticker|magnet|bookmark)\b", l.get("title") or "", re.I): return ("Swag", "Swag")
    if col in SERIES: return ("Single books", f"{SERIES[col]} singles {fmt}")
    return ("Funnel / other", "Funnel bundles & upsells")

def pb_isbns(l):
    if l.get("bundle_barcodes") is not None:
        return [b for b in l["bundle_barcodes"] if ISBN.match(b or "")] * int(l.get("qty") or 1)
    return [l["barcode"]] * int(l.get("qty") or 1) if ISBN.match(l.get("barcode") or "") else []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--orders", required=True); ap.add_argument("--out", default=os.path.join(HERE, "bfcm.json"))
    a = ap.parse_args()
    orders = json.load(open(a.orders))
    by_id = {o["id"]: o for o in orders}

    # Paperback ISBNs per SHIPMENT: a PPU's books ride in its parent's box.
    ship_isbns = defaultdict(list)
    for o in orders:
        root = o["original_order_id"] if o["is_ppu"] and o.get("original_order_id") in by_id else o["id"]
        for l in o["lines"]: ship_isbns[root] += pb_isbns(l)

    T = Counter(); offers = defaultdict(lambda: Counter()); groups = defaultdict(lambda: Counter())
    libs = defaultdict(lambda: Counter()); days = defaultdict(lambda: Counter()); src = defaultdict(lambda: Counter())
    fmt = defaultdict(lambda: Counter()); sampler_orders = 0; sampler_with_addon = 0
    for o in orders:
        net = o["paid_total"] - o["refunded"]
        isbns = [] if (o["is_ppu"] and o.get("original_order_id") in by_id) else ship_isbns[o["id"]]
        print_cost = sum(cc.print_cost(i) for i in isbns)
        ship = cc.shipping(len(isbns))
        stripe = 0.029 * o["paid_total"] + 0.30 if o["paid_total"] > 0 else 0
        contrib = net - print_cost - ship - stripe
        T["orders"] += 1; T["revenue"] += net; T["contrib"] += contrib; T["refunded"] += o["refunded"]
        T["returning"] += o["returning_buyer"]; T["gifts"] += o["is_gift"]; T["codes"] += bool(o.get("coupon_code"))
        T["code_discount"] += sum(l["discount"] for l in o["lines"] if "TMP_CODE" in (l.get("codes") or ""))
        T["books"] += sum((len(l["bundle_barcodes"]) if l.get("bundle_barcodes") is not None else 1) * l["qty"] for l in o["lines"] if offer_of(l)[0] != "Swag")
        d = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).astimezone(CT).strftime("%a %b %d")
        days[d]["orders"] += 1; days[d]["revenue"] += net
        source = "Email" if (o.get("utm_source") or "").lower() == "email" else "Facebook (paid click)" if o["has_fbc"] or (o.get("utm_source") or "").lower() == "facebook" else "Direct / organic"
        src[source]["orders"] += 1; src[source]["revenue"] += net
        kinds = [l.get("bundle_kind") for l in o["lines"]]
        if "sampler" in kinds:
            sampler_orders += 1; sampler_with_addon += "addon" in kinds
        # spread the order's net revenue + contribution over its lines by line value
        line_vals = [max(0.0, l["unit_price"] * l["qty"] - l["discount"]) for l in o["lines"]]
        tot = sum(line_vals) or 1.0
        for l, v in zip(o["lines"], line_vals):
            g, lab = offer_of(l); share = v / tot
            for bucket in (offers[lab], groups[g]):
                bucket["units"] += l["qty"]; bucket["revenue"] += net * share; bucket["contrib"] += contrib * share
            is_pb = re.search(r"paperback", l.get("title") or "", re.I) or (l.get("handle") or "").endswith("-pb") or bool(pb_isbns(l))
            f = "Swag" if g == "Swag" else ("Paperback" if is_pb else "Ebook")
            fmt[f]["revenue"] += net * share
            lib = (l.get("pack_key") or "").replace("addon-", "") if l.get("bundle_kind") in ("collection", "addon") else l.get("collection")
            if lib in NEW_LIBS:
                libs[NEW_LIBS[lib]]["revenue"] += net * share
                libs[NEW_LIBS[lib]]["books"] += (len(l["bundle_barcodes"]) if l.get("bundle_barcodes") is not None else 1) * l["qty"]

    r2 = lambda c: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.items()}
    out = {
        "generated": datetime.now(CT).strftime("%Y-%m-%d %H:%M CT"),
        "window": "Wed Nov 25 9 AM CT onward (test orders excluded)",
        "totals": {**r2(T), "aov": round(T["revenue"] / T["orders"], 2) if T["orders"] else 0,
                   "contrib_pct": round(100 * T["contrib"] / T["revenue"], 1) if T["revenue"] else 0,
                   "new_buyers": T["orders"] - T["returning"],
                   "addon_attach_pct": round(100 * sampler_with_addon / sampler_orders, 1) if sampler_orders else None,
                   "sampler_orders": sampler_orders},
        "groups": sorted(({"name": k, **r2(v)} for k, v in groups.items()), key=lambda x: -x["revenue"]),
        "offers": sorted(({"name": k, **r2(v)} for k, v in offers.items()), key=lambda x: -x["revenue"]),
        "libraries": sorted(({"name": k, **r2(v)} for k, v in libs.items()), key=lambda x: -x["revenue"]),
        "formats": sorted(({"name": k, **r2(v)} for k, v in fmt.items()), key=lambda x: -x["revenue"]),
        "sources": sorted(({"name": k, **r2(v)} for k, v in src.items()), key=lambda x: -x["revenue"]),
        "days": [{"name": k, **r2(v)} for k, v in sorted(days.items(), key=lambda kv: datetime.strptime(kv[0] + " 2026", "%a %b %d %Y"))],
    }
    json.dump(out, open(a.out, "w"), indent=1)
    t = out["totals"]
    print("BFCM: %d orders, $%.2f net, contribution $%.2f (%.1f%%), AOV $%.2f, add-on attach %s"
          % (t.get("orders", 0), t.get("revenue", 0), t.get("contrib", 0), t["contrib_pct"], t["aov"], t["addon_attach_pct"]))

if __name__ == "__main__":
    main()
