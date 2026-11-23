"""Optional Stripe billing: a small plan catalogue, checkout sessions, signed webhooks and local subscriptions.

No key lives in this file or in the data folder. An operator supplies Stripe credentials through the environment
(or *_FILE paths); until then the checkout route answers 503 instead of pretending a subscription was created.
Paid entitlements come only from webhook events whose Stripe signature has been verified here.
"""
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
import sqlalchemy as sa

from . import config, db

_UID = re.compile(r"[A-Za-z0-9_]{6,40}\Z")
_PLAN_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}\Z")
_EMAIL = re.compile(r"[^@\s,;:<>]+@[^@\s,;:<>]+\.[A-Za-z]{2,24}\Z")
CONFIGURE_HINT = ("Billing is not set up on this server. Ask the operator to set PEAKCUT_BILLING_PROVIDER=stripe "
                  "and PEAKCUT_BILLING_SECRET_KEY (or PEAKCUT_BILLING_SECRET_KEY_FILE), plus a paid plan price "
                  "such as PEAKCUT_BILLING_PRICE_PRO, then restart PeakCut.")


class BillingError(RuntimeError):
    """A problem safe to show a user: no secret, provider response body or stack trace is included."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    tier: str                              # free | byok | paid
    description: str
    price_id: str = ""
    amount: int = 0                        # smallest currency unit; 0 for the two built-in tiers
    currency: str = "usd"
    interval: str = "month"
    features: tuple = ()
    limits: dict = field(default_factory=dict)

    def public(self) -> dict:
        """What the browser may see. There is nothing secret in a plan, but never add a key here."""
        return {"id": self.id, "name": self.name, "tier": self.tier, "description": self.description,
                "price": {"amount": self.amount, "currency": self.currency, "interval": self.interval},
                "features": list(self.features), "limits": dict(self.limits),
                "checkout": self.tier == "paid" and bool(self.price_id)}


FREE = Plan("free", "Free", "free", "PeakCut on this machine, with the free local speech model.",
            features=("Clip and schedule videos", "Guided tour and templates", "Community support"),
            limits={"max_active_jobs": 2, "max_creators": 3, "max_video_hours": 2, "max_user_gb": 5})
BYOK = Plan("byok", "Bring your own key", "byok", "Use your own AI key; you pay that provider directly.",
            features=("Everything in Free", "Your own AI provider and models", "AI hooks, titles and captions"),
            limits={"max_active_jobs": 5, "max_creators": 10, "max_video_hours": 10, "max_user_gb": 25})


def _default_paid() -> list:
    """The simple config form: one price id per tier, with amounts in PEAKCUT_BILLING_*_AMOUNT."""
    rows = (("starter", "Starter", config.BILLING_PRICE_STARTER, config.BILLING_STARTER_AMOUNT,
             ("Everything in BYOK", "More simultaneous videos", "Email support"),
             {"max_active_jobs": 10, "max_creators": 25, "max_video_hours": 40, "max_user_gb": 100}),
            ("pro", "Pro", config.BILLING_PRICE_PRO, config.BILLING_PRO_AMOUNT,
             ("Everything in Starter", "Priority processing", "More creators and storage"),
             {"max_active_jobs": 25, "max_creators": 100, "max_video_hours": 150, "max_user_gb": 500}),
            ("studio", "Studio", config.BILLING_PRICE_STUDIO, config.BILLING_STUDIO_AMOUNT,
             ("Everything in Pro", "Team workspace", "Highest limits"),
             {"max_active_jobs": 60, "max_creators": 300, "max_video_hours": 500, "max_user_gb": 2000}))
    plans = []
    for pid, name, price, amount, features, limits in rows:
        if price:
            plans.append(Plan(pid, name, "paid", f"Paid PeakCut plan: {name}.", price, max(0, int(amount)),
                              config.BILLING_CURRENCY, "month", features, limits))
    return plans


def _json_paid() -> list:
    """The full config form: PEAKCUT_BILLING_PLANS is a JSON list of paid plan definitions."""
    try:
        raw = json.loads(config.BILLING_PLANS_JSON)
    except (ValueError, TypeError):
        raise BillingError(500, "PEAKCUT_BILLING_PLANS is not valid JSON. Check the server settings.")
    if not isinstance(raw, list):
        raise BillingError(500, "PEAKCUT_BILLING_PLANS must be a JSON list of plans.")
    plans = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip().lower()
        price = str(item.get("price_id") or "").strip()
        if not _PLAN_ID.match(pid) or not price or pid in ("free", "byok"):
            continue
        interval = str(item.get("interval") or "month").lower()
        if interval not in ("day", "week", "month", "year"):
            interval = "month"
        try:
            amount = max(0, int(item.get("amount", 0)))
        except (ValueError, TypeError):
            amount = 0
        features = tuple(str(x)[:160] for x in (item.get("features") or [])[:12])
        limits = {str(k)[:40]: str(v)[:80] for k, v in list(dict(item.get("limits") or {}).items())[:20]}
        plans.append(Plan(pid, str(item.get("name") or pid)[:60], "paid",
                          str(item.get("description") or "Paid PeakCut plan.")[:300], price, amount,
                          str(item.get("currency") or config.BILLING_CURRENCY).lower()[:3], interval,
                          features, limits))
    return plans


def plans() -> list:
    paid = _json_paid() if config.BILLING_PLANS_JSON else _default_paid()
    out, seen = [FREE, BYOK], {"free", "byok"}
    for p in paid:
        if p.id not in seen:
            out.append(p)
            seen.add(p.id)
    return out


def catalogue() -> dict:
    return {"provider": config.BILLING_PROVIDER or None, "configured": configured(),
            "publishable_key": config.BILLING_PUBLISHABLE_KEY or None,
            "checkout_available": checkout_available(),
            "plans": [p.public() for p in plans()]}


def configured() -> bool:
    return config.BILLING_PROVIDER == "stripe" and bool(config.billing_secret())


def checkout_available() -> bool:
    return configured() and any(p.tier == "paid" and p.price_id for p in plans())


def plan_by_id(pid: str):
    return next((p for p in plans() if p.id == pid), None)


def plan_by_price(price_id: str):
    return next((p for p in plans() if p.price_id and p.price_id == price_id), None)


def byok_available() -> bool:
    """A key typed in Settings counts as BYOK; only its presence is reported, never the key itself."""
    if config.ai_key():
        return True
    try:
        saved = json.loads((config.DATA_DIR / "ai.json").read_text(encoding="utf-8"))
        return bool(saved.get("key"))
    except (OSError, ValueError, AttributeError):
        return False


def _row(uid: str):
    with db.engine.connect() as c:
        return c.execute(sa.select(db.billing_subscriptions).where(db.billing_subscriptions.c.user_id == uid)).mappings().first()


def subscription(uid: str) -> dict:
    """This account's current tier and machine-readable entitlements. Owner-scoped by the caller."""
    row = _row(uid)
    tier, plan, status = "free", FREE, "none"
    if row:
        status = row["status"] or "none"
        found = plan_by_id(row["plan_id"])
        paid_ok = status in ("active", "trialing") and found is not None and found.tier == "paid"
        if paid_ok:
            tier, plan = "paid", found
    if tier == "free" and byok_available():
        tier, plan = "byok", BYOK
    return {"tier": tier, "status": status, "plan": plan.public(), "entitlements": dict(plan.limits),
            "renews_at": (row["current_period_end"] if row else None),
            "cancel_at_period_end": bool(row["cancel_at_period_end"]) if row else False,
            "checkout_available": checkout_available(), "provider": config.BILLING_PROVIDER or None}


def entitlements(uid: str) -> dict:
    """Small helper for callers that need to know what an account is entitled to."""
    s = subscription(uid)
    return {"tier": s["tier"], "plan": s["plan"]["id"], "limits": s["entitlements"]}


def _stripe(method, path, data=None):
    """Only ever talks to the fixed HTTPS Stripe address; the key is sent as HTTP Basic auth, never in a URL."""
    url = config.BILLING_API_BASE.rstrip("/") + path
    if not url.startswith("https://") or urlparse(url).hostname != "api.stripe.com":
        raise BillingError(502, "Billing settings are invalid: the payment address must be api.stripe.com over HTTPS.")
    try:
        r = method(url, data=data, auth=(config.billing_secret(), ""), timeout=20.0)
    except httpx.HTTPError:
        raise BillingError(502, "The payment service could not be reached. Try again shortly.")
    if r.status_code < 200 or r.status_code >= 300:
        raise BillingError(502, f"The payment service refused the request (status {r.status_code}). "
                                "Check the server's billing settings and plan prices.")
    try:
        return r.json()
    except (ValueError, AttributeError):
        raise BillingError(502, "The payment service sent an unexpected reply. Nothing was changed.")


def checkout(uid: str, email: str, plan_id: str) -> dict:
    """Create a real Stripe Checkout session. No configured keys means a clear 503, never a fake success."""
    if not configured():
        raise BillingError(503, CONFIGURE_HINT)
    plan = plan_by_id(str(plan_id or "").strip().lower())
    if not plan or plan.tier != "paid" or not plan.price_id:
        raise BillingError(400, "Choose one of the paid plans to subscribe.")
    if not _UID.match(uid or ""):
        raise BillingError(400, "Only a signed-in account can subscribe.")
    data = {"mode": "subscription", "success_url": config.PUBLIC_URL + "/app?billing=success",
            "cancel_url": config.PUBLIC_URL + "/app?billing=cancel",
            "client_reference_id": uid, "metadata[user_id]": uid, "metadata[plan_id]": plan.id,
            "subscription_data[metadata][user_id]": uid, "subscription_data[metadata][plan_id]": plan.id,
            "line_items[0][price]": plan.price_id, "line_items[0][quantity]": "1"}
    with db.engine.connect() as c:
        customer = c.execute(sa.select(db.billing_customers.c.stripe_customer_id)
                             .where(db.billing_customers.c.user_id == uid)).scalar()
    if customer:
        data["customer"] = customer
    elif _EMAIL.match(str(email or "")):
        data["customer_email"] = str(email)[:254]
    # A double click within the same hour must not create two open sessions.
    key = hashlib.sha256(f"{uid}:{plan.id}:{int(time.time() // 3600)}".encode()).hexdigest()
    try:
        r = httpx.post(config.BILLING_API_BASE + "/v1/checkout/sessions", data=data,
                       auth=(config.billing_secret(), ""), timeout=20.0, headers={"Idempotency-Key": key})
    except httpx.HTTPError:
        raise BillingError(502, "The payment service could not be reached. Try again shortly.")
    if r.status_code < 200 or r.status_code >= 300:
        raise BillingError(502, f"The payment service refused the checkout request (status {r.status_code}). "
                                "Check the plan price and the server's billing settings.")
    try:
        session = r.json()
        url, sid = str(session.get("url") or ""), str(session.get("id") or "")
    except (ValueError, AttributeError):
        raise BillingError(502, "The payment service sent an unexpected checkout reply. Nothing was charged.")
    host = urlparse(url).hostname or ""
    if urlparse(url).scheme != "https" or not (host == "checkout.stripe.com" or host.endswith(".stripe.com")):
        raise BillingError(502, "The payment service returned an unexpected checkout address. Nothing was charged.")
    return {"url": url, "session_id": sid[:80], "plan": plan.id}


def verify(payload: bytes, header: str, now: float = None) -> bool:
    """Stripe's t=...,v1=... HMAC-SHA256 signature over the exact raw body, with a freshness window."""
    secret = config.billing_webhook_secret()
    if not secret or not header:
        return False
    parts = {}
    for chunk in header.split(","):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            parts.setdefault(k.strip(), []).append(v.strip())
    stamps = parts.get("t", [])
    signatures = parts.get("v1", [])
    if len(stamps) != 1 or not stamps[0].isdigit() or not signatures:
        return False
    if abs((now if now is not None else time.time()) - int(stamps[0])) > config.BILLING_WEBHOOK_TOLERANCE:
        return False
    expected = hmac.new(secret.encode("utf-8"), stamps[0].encode("ascii") + b"." + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in signatures)


def _customer(c, uid: str, cid: str):
    if not _UID.match(uid or "") or not re.fullmatch(r"[A-Za-z0-9_]{4,80}", cid or ""):
        raise BillingError(400, "The payment event did not name a valid account or customer.")
    c.execute(db.billing_customers.delete().where(db.billing_customers.c.user_id == uid))
    c.execute(db.billing_customers.insert().values(user_id=uid, stripe_customer_id=cid, created_at=time.time()))


def _save_sub(c, uid: str, status: str, plan_id: str, cid: str, sid: str, price: str,
              period_end, cancel_at_period_end: bool):
    """One subscription row per account. Upsert by account, never by a caller-supplied row id."""
    if not _UID.match(uid or "") or not re.fullmatch(r"[A-Za-z0-9_]{4,80}", sid or ""):
        raise BillingError(400, "The payment event did not name a valid account or subscription.")
    now = time.time()
    values = {"plan_id": plan_id, "status": status, "stripe_customer_id": cid or None,
              "stripe_subscription_id": sid, "stripe_price_id": price or None,
              "current_period_end": period_end, "cancel_at_period_end": bool(cancel_at_period_end),
              "updated_at": now, "canceled_at": now if status == "canceled" else None}
    known = c.execute(sa.select(db.billing_subscriptions.c.user_id)
                      .where(db.billing_subscriptions.c.user_id == uid)).scalar()
    if known:
        c.execute(db.billing_subscriptions.update().where(db.billing_subscriptions.c.user_id == uid).values(**values))
    else:
        c.execute(db.billing_subscriptions.insert().values(user_id=uid, created_at=now, **values))


def _handle(c, event: dict) -> str:
    """Apply one verified event inside the caller's transaction. Returns the affected account id, if any."""
    kind = str(event.get("type") or "")
    obj = event.get("data", {}).get("object") if isinstance(event.get("data"), dict) else None
    if not isinstance(obj, dict):
        return ""
    sid = str(obj.get("subscription") or obj.get("id") or "")
    meta = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    uid = str(meta.get("user_id") or obj.get("client_reference_id") or "")
    if not _UID.match(uid):
        known = c.execute(sa.select(db.billing_subscriptions.c.user_id)
                          .where(db.billing_subscriptions.c.stripe_subscription_id == sid)).scalar()
        uid = known or ""

    if kind == "checkout.session.completed":
        # Only a subscription checkout grants a paid tier. A one-off payment has a checkout id but no
        # subscription id, and must never be turned into a subscription by this handler.
        sub = str(obj.get("subscription") or "")
        mode = str(obj.get("mode") or "")
        if not sub or (mode and mode != "subscription") or not obj.get("customer"):
            return ""
        plan = plan_by_id(str(meta.get("plan_id") or ""))
        if not plan or plan.tier != "paid":
            raise BillingError(400, "The checkout event named an unknown plan; check the server's plan settings.")
        _customer(c, uid, str(obj["customer"]))
        previous = c.execute(sa.select(db.billing_subscriptions.c.user_id)
                             .where(db.billing_subscriptions.c.stripe_subscription_id == sub)).scalar()
        if previous and previous != uid:
            raise BillingError(400, "That subscription belongs to a different account.")
        _save_sub(c, uid, "active", plan.id, str(obj["customer"]), sub, plan.price_id, None, False)
        return uid

    if kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        if not _UID.match(uid):
            return ""                      # not one of our subscriptions
        current = c.execute(sa.select(db.billing_subscriptions)
                            .where(db.billing_subscriptions.c.stripe_subscription_id == sid)).mappings().first()
        owner = current["user_id"] if current else ""
        if owner and owner != uid:
            raise BillingError(400, "That subscription belongs to a different account.")
        uid = owner or uid                  # the stored owner wins over metadata on later events
        if kind == "customer.subscription.deleted":
            if not current:
                return ""
            _save_sub(c, uid, "canceled", current["plan_id"], current["stripe_customer_id"] or "",
                      sid, current["stripe_price_id"] or "", current["current_period_end"], False)
            return uid
        items = obj.get("items") if isinstance(obj.get("items"), dict) else {}
        lines = items.get("data") if isinstance(items.get("data"), list) else []
        price = str((lines[0].get("price") or {}).get("id") or "") if lines and isinstance(lines[0], dict) else ""
        plan = plan_by_id(str(meta.get("plan_id") or "")) or plan_by_price(price)
        if not plan or plan.tier != "paid":
            raise BillingError(400, "The subscription event named an unknown plan; check the server's plan settings.")
        status = str(obj.get("status") or "inactive")[:30]
        period = obj.get("current_period_end")
        try:
            period = float(period) if period is not None else None
        except (ValueError, TypeError):
            period = None
        _save_sub(c, uid, status, plan.id, str(obj.get("customer") or ""), sid, price, period,
                  bool(obj.get("cancel_at_period_end")))
        return uid
    return ""


def handle_event(payload: bytes, header: str) -> dict:
    """Verify the signature, record the event id once, then apply it. Invalid events grant nothing."""
    if not verify(payload, header):
        raise BillingError(400, "The payment event's signature could not be verified.")
    try:
        event = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        raise BillingError(400, "The payment event was not valid JSON.")
    if not isinstance(event, dict):
        raise BillingError(400, "The payment event was not valid JSON.")
    eid, kind = str(event.get("id") or ""), str(event.get("type") or "")
    if not re.fullmatch(r"[A-Za-z0-9_]{4,120}", eid) or not re.fullmatch(r"[A-Za-z0-9_.]{3,60}", kind):
        raise BillingError(400, "The payment event was missing an id or type.")
    now = time.time()
    try:
        with db.engine.begin() as c:
            try:
                # A savepoint lets a duplicate be acknowledged without leaving the outer transaction in a
                # failed state (a swallowed bare INSERT IntegrityError breaks on SQLite and PostgreSQL).
                with c.begin_nested():
                    c.execute(db.billing_events.insert().values(id=eid, type=kind, created_at=now))
            except sa.exc.IntegrityError:
                return {"received": True, "duplicate": True, "user_id": None}
            who = _handle(c, event)
            c.execute(db.billing_events.update().where(db.billing_events.c.id == eid)
                      .values(user_id=who or None, processed_at=time.time()))
    except sa.exc.IntegrityError:
        raise BillingError(409, "That payment event conflicts with an existing record.")
    return {"received": True, "duplicate": False, "user_id": who or None}


def cancel(uid: str) -> dict:
    """Cancel at the end of the paid period; the webhook remains the authority for the final status."""
    row = _row(uid)
    if not row:
        raise BillingError(404, "You do not have a subscription to manage.")
    sid, cid = row["stripe_subscription_id"] or "", row["stripe_customer_id"] or ""
    if configured() and sid:
        _stripe(httpx.post, f"/v1/subscriptions/{sid}", {"cancel_at_period_end": "true"})
        value = True
    else:
        # No provider set up (or no remote id): only the local record can be managed here.
        value = True
    with db.engine.begin() as c:
        c.execute(db.billing_subscriptions.update().where(db.billing_subscriptions.c.user_id == uid)
                  .values(cancel_at_period_end=value, updated_at=time.time()))
    return {"status": row["status"], "cancel_at_period_end": value,
            "message": "Your plan stays active until the end of the billing period. "
                       "A cancellation is confirmed only by the payment service's event." if sid else
                       "The local subscription record was marked for cancellation."}
