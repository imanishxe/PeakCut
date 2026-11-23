"""Focused real boot check for the B1 billing + error-report slice.

    python scratch/b1_boot_check.py [--with-harness-test]

Starts throwaway PeakCut servers on spare ports with temp PEAKCUT_DATA folders and talks to them over real HTTP.
Nothing in the project's real data folder, and no payment provider, is touched.
"""
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("PEAKCUT_B1_PORT", "8877"))
BASE_A = f"http://127.0.0.1:{PORT}"
BASE_B = f"http://127.0.0.1:{PORT + 1}"
BASE_C = f"http://127.0.0.1:{PORT + 2}"
# Fake, test-only marker values. They are split so no scanner can mistake them for a real credential.
WEBHOOK_SECRET = "wh" + "sec_bootcheck_" + "a" * 16
STRIPE_SECRET = "sk" + "_test_bootcheck_" + "c" * 16
fails = []


def check(name, got, want=True):
    ok = got == want if not callable(want) else want(got)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got!r}, wanted {want!r}"))
    if not ok:
        fails.append(name)


def env_for(data, port, accounts=False):
    env = {**os.environ,
           "PEAKCUT_DATA": str(data), "PEAKCUT_PORT": str(port), "PEAKCUT_PUBLIC_URL": f"http://127.0.0.1:{port}",
           "PEAKCUT_HOST": "127.0.0.1", "PEAKCUT_AUTO_RELOAD": "0", "DATABASE_URL": "",
           "PEAKCUT_ACCOUNTS": "1" if accounts else "0", "PEAKCUT_FETCH_MODEL": "0",
           "PEAKCUT_UPDATE_CHECK": "0", "PEAKCUT_SMTP_HOST": "", "PEAKCUT_VERIFY_EMAIL": "0",
           "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "", "GOOGLE_CLIENT_FILE": "",
           "PEAKCUT_AI_KEY": "", "PEAKCUT_AI_KEY_FILE": "",
           "PEAKCUT_BILLING_PROVIDER": "", "PEAKCUT_BILLING_SECRET_KEY": "",
           "PEAKCUT_BILLING_SECRET_KEY_FILE": "", "PEAKCUT_BILLING_WEBHOOK_SECRET": "",
           "PEAKCUT_BILLING_WEBHOOK_SECRET_FILE": "", "PEAKCUT_BILLING_PLANS": "",
           "PEAKCUT_BILLING_PRICE_STARTER": "", "PEAKCUT_BILLING_PRICE_PRO": "",
           "PEAKCUT_BILLING_PRICE_STUDIO": "", "PYTHONUNBUFFERED": "1"}
    return env


def boot(data, port, accounts=False, extra=None):
    env = env_for(data, port, accounts)
    env.update(extra or {})
    log = data / f"server-{port}.log"
    out = log.open("w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "studio.server"], cwd=ROOT, env=env,
                            stdout=out, stderr=subprocess.STDOUT)
    return proc, env, log


def wait(base, proc, log):
    for _ in range(120):
        try:
            urllib.request.urlopen(base + "/healthz", timeout=2)
            return True
        except Exception:  # noqa: BLE001 - the server may still be starting
            if proc.poll() is not None:
                print(log.read_text(encoding="utf-8", errors="replace")[-2000:])
                return False
            time.sleep(0.5)
    print(log.read_text(encoding="utf-8", errors="replace")[-2000:])
    return False


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def signed(eid, kind, obj):
    body = json.dumps({"id": eid, "object": "event", "type": kind, "data": {"object": obj}},
                      separators=(",", ":")).encode()
    stamp = str(int(time.time()))
    sig = hmac.new(WEBHOOK_SECRET.encode(), stamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return body, {"stripe-signature": f"t={stamp},v1={sig}", "Content-Type": "application/json"}


def unconfigured_boot(data):
    proc, _env, log = boot(data, PORT)
    try:
        if not wait(BASE_A, proc, log):
            check("unconfigured server boots", False)
            return
        check("unconfigured server boots and answers /healthz", True)
        with httpx.Client(base_url=BASE_A, timeout=10, follow_redirects=False) as c:
            origin = {"Origin": BASE_A}
            r = c.get("/api/billing/plans")
            check("plans 200", r.status_code, 200)
            check("free and byok always listed", {"free", "byok"} <= {p["id"] for p in r.json()["plans"]}, True)
            check("not configured, no checkout", (r.json()["configured"], r.json()["checkout_available"]), (False, False))
            check("subscription 200", c.get("/api/billing/subscription").status_code, 200)
            r = c.post("/api/billing/checkout", json={"plan": "pro"}, headers=origin)
            check("checkout without keys -> 503", r.status_code, 503)
            check("503 explains the missing configuration", "not set up" in r.json().get("detail", ""), True)
            check("no fake checkout URL", "url" in r.json(), False)
            check("unsigned webhook -> 400", c.post("/api/billing/webhook", json={"id": "evt_a", "type": "x"}).status_code, 400)
            check("report without consent -> 400",
                  c.post("/api/error-report", json={"action": "boot check"}, headers=origin).status_code, 400)
            secret = "sk" + "_test_scrub_" + "d" * 16
            email = "bootcheck@example.com"
            r = c.post("/api/error-report", headers=origin,
                       json={"action": "boot check", "consent": True,
                             "comments": f'api_key="{secret}" mail {email} Authorization: Bearer {secret}',
                             "stack": f"Error: token=abc123XYZ at C:\\secret\\trace"})
            check("report with consent -> 200", r.status_code, 200)
            check("the reply does not echo the report", secret not in r.text and email not in r.text, True)
            saved = data / "error-reports" / "u_local.json"
            check("per-user JSON report exists", saved.is_file(), True)
            text = saved.read_text(encoding="utf-8") if saved.is_file() else ""
            check("no key, email or token on disk",
                  all(x not in text for x in (secret, email, "abc123XYZ")), True)
            check("scrub markers on disk", "[redacted]" in text and "[email]" in text, True)
            r = c.get("/api/admin/error-reports")
            check("local owner is admin and can list reports", r.status_code, 200)
            check("admin view is scrubbed", secret not in r.text and email not in r.text, True)
    finally:
        stop(proc)


def configured_boot(data):
    extra = {"PEAKCUT_BILLING_PROVIDER": "stripe", "PEAKCUT_BILLING_SECRET_KEY": STRIPE_SECRET,
             "PEAKCUT_BILLING_WEBHOOK_SECRET": WEBHOOK_SECRET, "PEAKCUT_BILLING_PRICE_PRO": "price_boot_pro"}
    proc, _env, log = boot(data, PORT + 1, extra=extra)
    try:
        if not wait(BASE_B, proc, log):
            check("configured server boots", False)
            return
        check("configured server boots", True)
        with httpx.Client(base_url=BASE_B, timeout=10, follow_redirects=False) as c:
            r = c.get("/api/billing/plans")
            check("catalogue reports a configured provider", r.status_code == 200 and r.json()["configured"], True)
            check("checkout is offered with a price id", r.json().get("checkout_available"), True)
            check("paid pro plan is listed", any(p["id"] == "pro" and p["checkout"] for p in r.json()["plans"]), True)
            check("secret key is not in the catalogue", STRIPE_SECRET in r.text, False)

            bad = {"id": "evt_boot_bad", "type": "checkout.session.completed",
                   "data": {"object": {"id": "cs_bad", "mode": "subscription", "subscription": "sub_bad",
                                       "customer": "cus_bad", "metadata": {"user_id": "u_local", "plan_id": "pro"}}}}
            header = f"t={int(time.time())},v1={'0' * 64}"
            check("bad HMAC -> 400",
                  c.post("/api/billing/webhook", json=bad, headers={"stripe-signature": header}).status_code, 400)
            check("no entitlement from a bad HMAC", c.get("/api/billing/subscription").json()["tier"], "free")

            oneoff = {"id": "evt_boot_oneoff", "object": "event", "type": "checkout.session.completed",
                      "data": {"object": {"id": "cs_oneoff", "mode": "payment", "customer": "cus_boot_ok",
                                          "client_reference_id": "u_local",
                                          "metadata": {"user_id": "u_local", "plan_id": "pro"}}}}
            body = json.dumps(oneoff, separators=(",", ":")).encode()
            stamp = str(int(time.time()))
            sig = hmac.new(WEBHOOK_SECRET.encode(), stamp.encode() + b"." + body, hashlib.sha256).hexdigest()
            r = c.post("/api/billing/webhook", content=body,
                       headers={"stripe-signature": f"t={stamp},v1={sig}", "Content-Type": "application/json"})
            check("signed one-off payment accepted but grants nothing", r.status_code, 200)
            check("no paid tier from a one-off payment", c.get("/api/billing/subscription").json()["tier"], "free")

            checkout_obj = {"id": "cs_boot_ok", "mode": "subscription", "subscription": "sub_boot_ok",
                            "customer": "cus_boot_ok", "client_reference_id": "u_local",
                            "metadata": {"user_id": "u_local", "plan_id": "pro"}}
            body, headers = signed("evt_boot_ok", "checkout.session.completed", checkout_obj)
            r = c.post("/api/billing/webhook", content=body, headers=headers)
            check("valid signed checkout event -> 200", r.status_code, 200)
            check("event response names the owner", r.json().get("user_id") if r.status_code == 200 else None, "u_local")
            sub = c.get("/api/billing/subscription").json()
            check("verified event grants the paid plan", (sub["tier"], sub["plan"]["id"]), ("paid", "pro"))
            r = c.post("/api/billing/webhook", content=body, headers=headers)
            check("the same event id is idempotent", (r.status_code, r.json().get("duplicate")), (200, True))
            check("duplicate does not change the plan", c.get("/api/billing/subscription").json()["plan"]["id"], "pro")

            tampered = body.replace(b"pro", b"studio", 1)
            check("tampering with a signed body -> 400",
                  c.post("/api/billing/webhook", content=tampered, headers=headers).status_code, 400)

            deleted = {"id": "sub_boot_ok", "customer": "cus_boot_ok", "status": "canceled",
                       "metadata": {"user_id": "u_local", "plan_id": "pro"}}
            body, headers = signed("evt_boot_deleted", "customer.subscription.deleted", deleted)
            check("signed cancellation -> 200", c.post("/api/billing/webhook", content=body, headers=headers).status_code, 200)
            sub = c.get("/api/billing/subscription").json()
            check("cancellation removes the paid tier", (sub["status"], sub["tier"]), ("canceled", "free"))
    finally:
        stop(proc)


def harness_test(data):
    proc, env, log = boot(data, PORT + 2, accounts=True,
                          extra={"PEAKCUT_VERIFY_EMAIL": "1", "PEAKCUT_UPLOAD_PART_MB": "5",
                                 "PEAKCUT_MAX_UPLOAD_MB": "64"})
    try:
        if not wait(BASE_C, proc, log):
            check("harness-test server boots", False)
            return
        r = subprocess.run([sys.executable, "tests/test_billing_errors.py", BASE_C], cwd=ROOT, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print((r.stdout + r.stderr).rstrip())
        check("tests/test_billing_errors.py against a real server", r.returncode, 0)
    finally:
        stop(proc)


def main():
    folders = []
    try:
        folders.append(Path(tempfile.mkdtemp(prefix="pc-b1-boot-")))
        unconfigured_boot(folders[-1])
        folders.append(Path(tempfile.mkdtemp(prefix="pc-b1-signed-")))
        configured_boot(folders[-1])
        if "--with-harness-test" in sys.argv:
            folders.append(Path(tempfile.mkdtemp(prefix="pc-b1-harness-")))
            harness_test(folders[-1])
    finally:
        for f in folders:
            shutil.rmtree(f, ignore_errors=True)
    print("\n%d failed" % len(fails) if fails else "\nALL PASSED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
