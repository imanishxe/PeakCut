"""Consent-based error reports: scrub secrets, keep a per-user JSON copy, and let admins read the reports.

The browser sends the report for review first; the server does the scrubbing again. No raw text, key, token,
password, email address or secret-bearing URL is ever returned to a browser or written to a log here.
"""
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import sqlalchemy as sa

from . import auth, config, db

STORE = "error-reports"          # folder inside the data folder; one JSON file per account
MAX_REPORTS = 100                # per account, oldest ones dropped first
FIELDS = {"action": 200, "repro": 4000, "reproduction_steps": 4000, "steps": 4000,
          "stack": 8000, "stack_trace": 8000, "comments": 4000,
          "message": 1000, "page": 200, "context": 1000}

_SENSITIVE = ("token", "apikey", "api_key", "api-key", "secret", "password", "passwd", "pwd",
              "authorization", "client_secret", "signature", "sig=", "cookie", "session", "sessionid", "code", "credential")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_KV = re.compile(r"(?i)\b(authorization|access[_-]?token|refresh[_-]?token|api[_-]?key|apikey|client[_-]?secret|"
                 r"secret|password|passwd|pwd|token|key|signature|sig|cookie|session|credential)"
                 r"\s*[:=]\s*['\"]?([^\s,;\"']+)['\"]?")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_TOKENS = re.compile(r"\b(?:sk|rk|pk)_[A-Za-z0-9_]{8,}\b|\bwhsec_[A-Za-z0-9_]{8,}\b|"
                     r"\bAIza[A-Za-z0-9_-]{10,}\b|\bghp_[A-Za-z0-9]{10,}\b|"
                     r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b|\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_PATH = re.compile(r"(?<=[\s\"'(])(?:[A-Za-z]:)?[\\/][^\s'\"\\/]*(?:[\\/][^\s'\"\\/]+)+")


class Refused(ValueError):
    pass


def _known_secrets() -> list:
    """Values the operator has configured: remove them even if they appear without a key name."""
    found = []

    def add(value):
        text = str(value or "").strip()
        if len(text) >= 4 and text not in found:
            found.append(text)

    for getter in (config.billing_secret, config.billing_webhook_secret, config.ai_key, config.smtp_password):
        try:
            add(getter())
        except Exception:  # noqa: BLE001 - a broken secret file must never break an error report
            pass
    try:
        add(config.google_client()[1])
    except Exception:  # noqa: BLE001
        pass
    for key, value in os.environ.items():
        if any(word in key.upper() for word in ("SECRET", "PASSWORD", "TOKEN", "API_KEY", "PRIVATE_KEY")):
            add(value)
    return sorted(found, key=len, reverse=True)


def redact(value, limit: int = 8000) -> str:
    """Scrub a piece of user text. Keys, tokens, passwords, emails and secret-bearing URLs never survive."""
    text = str(value if value is not None else "")[:limit * 4]
    secrets = _known_secrets()

    def sweep():
        nonlocal text
        for secret in secrets:
            if secret in text:
                text = text.replace(secret, "[redacted]")

    sweep()

    def url_case(match):
        url = match.group(0)
        parts = urlparse(url)
        low = url.lower()
        if parts.username or parts.password or any(word in low for word in _SENSITIVE):
            return "[redacted-url]"
        return url

    text = _URL.sub(url_case, text)
    # Bearer first: otherwise _KV eats the word "Bearer" and leaves the token as bare text.
    text = _BEARER.sub(lambda m: m.group(1) + " [redacted]", text)
    text = _KV.sub(lambda m: m.group(1) + "=[redacted]", text)
    text = _TOKENS.sub("[redacted]", text)
    text = _EMAIL.sub("[email]", text)
    text = _PATH.sub("[path]", text)
    sweep()
    # A sweep can shorten text; cutting once more keeps every field inside its database/JSON budget.
    return text[:limit]


def _stamp(value) -> str:
    text = redact(value, 80)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        when = datetime.fromisoformat(text)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when.astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _store_path(uid: str):
    if not re.fullmatch(r"[A-Za-z0-9_]{6,40}", uid or ""):
        raise Refused("There is no account to save this report for.")
    folder = config.DATA_DIR / STORE
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{uid}.json"


def submit(uid: str, body: dict) -> dict:
    """Validate consent, scrub every field, then keep the report in this user's JSON file and the admin index."""
    if body.get("consent") is not True:
        raise Refused("Please tick the consent box before sending a report.")
    auth.throttle("error-report:" + uid, 10, 3600)  # raises auth.AuthError -> 429 in the route
    report = {"id": "err_" + uuid.uuid4().hex[:16], "received_at": datetime.now(timezone.utc).isoformat(),
              "timestamp": _stamp(body.get("timestamp")), "action": "", "reproduction_steps": "",
              "stack_trace": "", "comments": "", "message": "", "page": "", "context": ""}
    for key in ("action", "comments", "message", "page", "context"):
        if key in report:
            report[key] = redact(body.get(key), FIELDS[key])
    report["reproduction_steps"] = redact(body.get("repro", body.get("reproduction_steps", body.get("steps", ""))),
                                          FIELDS["repro"])
    report["stack_trace"] = redact(body.get("stack", body.get("stack_trace", "")), FIELDS["stack"])
    if not any(report[k] for k in ("action", "reproduction_steps", "stack_trace", "comments", "message", "context")):
        raise Refused("Write at least one detail so we know what went wrong.")

    path = _store_path(uid)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = []
    if not isinstance(existing, list):
        existing = []
    existing.append(report)
    existing = existing[-MAX_REPORTS:]
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(existing, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(path))

    with db.engine.begin() as c:
        c.execute(db.error_reports.insert().values(id=report["id"], user_id=uid, t=time.time(),
                                                   action=report["action"][:200], store=path.name,
                                                   payload=json.dumps(report, ensure_ascii=False)))
    # The reply never contains the report text: no chance of reflecting a secret back to the sender.
    return {"id": report["id"], "received_at": report["received_at"]}


def listing(limit: int = 200) -> dict:
    """Admin-only view of the scrubbed reports, newest first."""
    with db.engine.connect() as c:
        rows = c.execute(sa.select(db.error_reports).order_by(db.error_reports.c.t.desc())
                         .limit(min(max(1, int(limit)), 500))).mappings().all()
    items = []
    for r in rows:
        try:
            saved = json.loads(r["payload"])
        except (ValueError, TypeError):
            saved = {}
        items.append({"id": r["id"], "user_id": r["user_id"], "t": r["t"],
                      "action": r["action"], "report": saved})
    return {"items": items, "count": len(items)}
