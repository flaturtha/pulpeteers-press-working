#!/usr/bin/env python3
"""
push-to-sheets.py — write breakeven.json into a Google Sheet.

Run through the venv so gspread is on the path:
    .venv/bin/python push-to-sheets.py

Needs two values in ~/.config/meta-ads/.env:
    GOOGLE_SA_KEY_PATH=/home/h/.config/gcp/tomp-sheets.json
    BREAKEVEN_SHEET_ID=<the id from the sheet's URL>

and the sheet shared (Editor) with the service account's client_email.
Setup walkthrough: docs/breakeven-model.md in the NOS repo.

Writes four tabs and rewrites them in place each run. Anything you build in
your OWN tabs is untouched — reference these with formulas rather than editing
them, or your edits are overwritten on the next refresh.
"""
import json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

def die(msg, code=2):
    print(f"push-to-sheets: {msg}", file=sys.stderr)
    sys.exit(code)

def main():
    key = os.environ.get("GOOGLE_SA_KEY_PATH")
    sid = os.environ.get("BREAKEVEN_SHEET_ID")
    if not key or not sid:
        die("GOOGLE_SA_KEY_PATH / BREAKEVEN_SHEET_ID not set — see docs/breakeven-model.md", 3)
    if not os.path.exists(key):
        die(f"service-account key not found at {key}", 3)

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        die("gspread missing — run: .venv/bin/pip install gspread google-auth", 4)

    d = json.load(open(os.path.join(HERE, "breakeven.json")))
    creds = Credentials.from_service_account_file(
        key, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    try:
        sh = gc.open_by_key(sid)
    except Exception as e:
        die(f"cannot open sheet {sid} — is it shared with the service account? ({e})", 5)

    m2 = lambda v: round(float(v), 2)

    tabs = {
        "model": (
            ["Window", "Days", "Orders", "AOV", "Revenue", "COGS", "COGS %", "Fees",
             "Fixed", "Break-even ad spend", "Break-even ROI", "Break-even CPA",
             "Actual ad spend", "Actual ROAS", "Profit", "Catalogue share %"],
            [[w["name"], w["days"], w["orders"], m2(w["aov"]), m2(w["revenue"]), m2(w["cogs"]),
              m2(w["cogs_pct"]), m2(w["fees"]), m2(w["fixed"]), m2(w["be_spend"]),
              m2(w["be_roi"] or 0), m2(w["be_cpa"]), m2(w["spend"]), m2(w["roas"] or 0),
              m2(w["profit"]), m2(w["catalog_share"])] for w in d["windows"]]),
        "cohorts": (
            ["Cohort", "Customers", "Age (days)", "Entry rev", "Repeat rev", "LTV",
             "LTV multiple", "Returned %"],
            [[c["cohort"], c["n"], c["age"], m2(c["entry"]), m2(c["repeat"]), m2(c["ltv"]),
              m2(c["multiple"]), m2(c["ret_pct"])] for c in d["cohorts"]]),
        "ltv": (
            ["LTV", "Per customer", "Per month", "Per year", "Note"],
            [[m2(l["ltv"]), m2(l["per_customer"]), m2(l["per_month"]), m2(l["per_year"]),
              "measured today" if abs(l["ltv"] - d["measured_ltv"]) < 0.01
              else "target" if abs(l["ltv"] - d["target_ltv"]) < 0.01 else ""]
             for l in d["ladder"]]),
        "inputs": (
            ["Input", "Value"],
            [["Generated", d["generated"]],
             ["Fixed costs / month", m2(d["fixed_month"])],
             ["Contribution margin", m2(d["margin"] * 100)],
             ["CAC", m2(d["cac"])],
             ["New customers / month", m2(d["new_per_month"])],
             ["Measured LTV", m2(d["measured_ltv"])],
             ["Target LTV", m2(d["target_ltv"])],
             ["Repeat order AOV", m2(d["repeat_aov"])],
             ["Customers to date", d["customers"]]]),
    }

    for name, (hdr, rows) in tabs.items():
        try:
            ws = sh.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=name, rows=max(len(rows) + 10, 20), cols=len(hdr) + 2)
        ws.clear()
        ws.update(values=[hdr] + rows, range_name="A1")
        print(f"  {name}: {len(rows)} rows")

    print(f"  → https://docs.google.com/spreadsheets/d/{sid}")

if __name__ == "__main__":
    main()
