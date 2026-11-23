"""Billing and error-report checks against a running PeakCut server.

    python tests/test_billing_errors.py <base url>

Runs with the throwaway server from tests/run.py (accounts on, no payment keys): nothing is charged and no
real provider is contacted. Keeps the original harness style: PASS/FAIL lines and a non-zero exit on failure.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

BASE = sys.argv[1]
ROOT = Path(__file__).resolve().parent.parent
ORIGIN = {"Origin": BASE}
FAKE_SECRET = "sk" + "_test_billingcheck_" + "b" * 16   # test-only marker, never a real key
FAKE_EMAIL = "billingcheck@example.com"
fails = []


def check(name, got, want):
    ok = got == want if not callable(want) else want(got)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(name)


def client():
    return httpx.Client(base_url=BASE, timeout=30, follow_redirects=False)


def signup(email):
    c = client()
    r = c.post("/api/auth/signup", json={"email": email, "password": "test-pass-123", "name": "B1 check"},
               headers=ORIGIN)
    assert r.status_code == 200, r.text
    return c, r.json()["user"]


def cli(*args):
    return subprocess.run([sys.executable, "-m", "studio.admin", *args], cwd=ROOT, env=os.environ,
                          capture_output=True, text=True)


anon = client()
a, ua = signup("billing-admin-check@example.com")
b, ub = signup("billing-user-check@example.com")

# ---- the catalogue is public to signed-in accounts and never leaks a key
r = a.get("/api/billing/plans")
check("plans 200", r.status_code, 200)
ids = {p["id"] for p in r.json().get("plans", [])}
check("Free and Bring-your-own-key are always listed", {"free", "byok"} <= ids, True)
check("no secret in the catalogue", "sk_test" in r.text or "whsec" in r.text, False)
check("billing is not configured by this harness", r.json().get("configured"), False)

# ---- no keys means a clear 503, never a fake checkout
r = a.post("/api/billing/checkout", json={"plan": "pro"}, headers=ORIGIN)
check("checkout without keys -> 503", r.status_code, 503)
check("checkout failure explains how to configure billing", "not set up" in r.json().get("detail", ""), True)
check("no checkout URL was invented", "url" in r.json(), False)

# ---- an unsigned or badly signed webhook grants nothing
sub = a.get("/api/billing/subscription")
check("subscription 200", sub.status_code, 200)
tier_before = sub.json()["tier"]
body = {"id": "evt_billingcheck_bad", "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_bad", "mode": "subscription", "subscription": "sub_bad",
                            "customer": "cus_bad", "metadata": {"user_id": ua["id"], "plan_id": "pro"}}}}
r = b.post("/api/billing/webhook", json=body, headers={"stripe-signature": f"t=1,v1={'0' * 64}"})
check("webhook with a bad signature -> 400", r.status_code, 400)
r = b.post("/api/billing/webhook", json=body)
check("webhook without any signature -> 400", r.status_code, 400)
check("a rejected webhook grants no paid tier", a.get("/api/billing/subscription").json()["tier"], tier_before)

# ---- consent is required, and the server scrubs what the browser reviewed
raw = (f'api_key="{FAKE_SECRET}" mail {FAKE_EMAIL} Authorization: Bearer {FAKE_SECRET} '
       f'stack at C:\\secret\\trace token=abc123XYZ')
no_consent = {"action": "billing check", "comments": raw, "consent": False}
check("report without consent -> 400", b.post("/api/error-report", json=no_consent, headers=ORIGIN).status_code, 400)
sent = b.post("/api/error-report", json={"action": "billing check", "consent": True, "comments": raw,
                                         "repro": f"open {FAKE_EMAIL} then paste {FAKE_SECRET}",
                                         "stack": f"Error: Authorization: Bearer {FAKE_SECRET}"}, headers=ORIGIN)
check("report with consent -> 200", sent.status_code, 200)
rid = sent.json().get("id") if sent.status_code == 200 else ""
check("the reply does not echo the report text", FAKE_SECRET in sent.text or FAKE_EMAIL in sent.text, False)

folder = os.environ.get("PEAKCUT_DATA")
if folder:
    saved = Path(folder) / "error-reports" / f"{ub['id']}.json"
    check("one scrubbed JSON file per account", saved.is_file(), True)
    text = saved.read_text(encoding="utf-8") if saved.is_file() else ""
    check("the stored file keeps the report id", rid in text, True)
    check("no key, email or token in the stored file",
          all(x not in text for x in (FAKE_SECRET, FAKE_EMAIL, "abc123XYZ")), True)
    check("secrets were replaced in the stored file", "[redacted]" in text and "[email]" in text, True)
else:
    print("SKIP per-user JSON file check (PEAKCUT_DATA not set)")

# ---- the admin view is not reachable by visitors or ordinary accounts
for who, c in (("anonymous", anon), ("user", a), ("other user", b)):
    check(f"{who} cannot list error reports", c.get("/api/admin/error-reports").status_code, 404)
check("grant admin on the server", cli("grant", "billing-admin-check@example.com").returncode, 0)
listed = a.get("/api/admin/error-reports")
check("admin can list error reports", listed.status_code, 200)
check("the submitted report is in the admin list", any(i["id"] == rid for i in listed.json().get("items", [])), True)
check("the admin view is scrubbed too",
      all(x not in listed.text for x in (FAKE_SECRET, FAKE_EMAIL, "abc123XYZ")), True)

print("\n%d failed" % len(fails) if fails else "\nALL PASSED")
sys.exit(1 if fails else 0)
