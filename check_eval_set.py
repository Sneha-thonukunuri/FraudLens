"""Usage: python check_eval_set.py data/eval_set.jsonl [more.jsonl ...]
Checks unique ids, required fields, valid labels, and prints class balance."""
import json, sys, collections
LABELS = {"banking_kyc","upi_payment","phishing","fake_job","romance","legitimate"}
DIFF = {"easy","medium","hard"}
rows, errors = [], []
for path in sys.argv[1:]:
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as e: errors.append(f"{path}:{n} bad JSON: {e}")
ids = collections.Counter(r.get("id") for r in rows)
errors += [f"duplicate id {i}" for i, c in ids.items() if c > 1]
for r in rows:
    for k in ("id","text","url","label","difficulty"):
        if k not in r: errors.append(f"id {r.get('id')}: missing {k}")
    if r.get("label") not in LABELS: errors.append(f"id {r.get('id')}: bad label {r.get('label')}")
    if r.get("difficulty") not in DIFF: errors.append(f"id {r.get('id')}: bad difficulty")
    if not str(r.get("text","")).strip(): errors.append(f"id {r.get('id')}: empty text")
scam = sum(r.get("label") != "legitimate" for r in rows)
print(f"{len(rows)} rows | scam {scam} | legitimate {len(rows)-scam}")
print("labels:", dict(collections.Counter(r.get("label") for r in rows)))
print("difficulty:", dict(collections.Counter(r.get("difficulty") for r in rows)))
print("with URL:", sum(bool(r.get("url")) for r in rows))
print("\n".join(errors) if errors else "OK: no problems found")
sys.exit(1 if errors else 0)