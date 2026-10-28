"""Local-only Splitwise fetch. Reads the key from SPLITWISE_API_KEY env var.
Never commit the key or the output data.json (see .gitignore).
Keeps USD, non-payment, non-deleted expenses; 'my share' is owed_share.
Splitwise requires a Pro subscription to register an application / API key.
"""
import json, os, urllib.request, urllib.error

BASE = "https://secure.splitwise.com/api/v3.0"
KEY = os.environ.get("SPLITWISE_API_KEY")
if not KEY:
    raise SystemExit("Set SPLITWISE_API_KEY (never commit it).")

def get(path):
    req = urllib.request.Request(BASE + path, headers={
        "Accept": "application/json",
        # Splitwise / Cloudflare rejects default urllib clients; a browser UA works.
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Authorization": f"Bearer {KEY}",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

me = get("/get_current_user")["user"]
me_id = me["id"]
expenses, offset = [], 0
while offset < 3000:
    batch = get(f"/get_expenses?limit=100&offset={offset}").get("expenses", [])
    if not batch:
        break
    expenses.extend(batch)
    if len(batch) < 100:
        break
    offset += 100

out = []
for e in expenses:
    if e.get("deleted_at") or e.get("payment"):
        continue
    if e.get("currency_code") != "USD":
        continue
    users = e.get("users", [])
    mine = next((u for u in users if u["user_id"] == me_id), None)
    if not mine:
        continue
    out.append({
        "date": e["date"][:10], "month": e["date"][:7],
        "desc": e.get("description", ""), "cat": e.get("category", {}).get("name", "General"),
        "group": e.get("group_id") or "Non-group",
        "cost": float(e["cost"]), "myOwed": float(mine["owed_share"]),
        "myPaid": float(mine["paid_share"]), "source": "splitwise",
    })
with open("data.json", "w") as f:
    json.dump(out, f, indent=1)
print(f"{len(out)} USD spending expenses for user {me_id}")
