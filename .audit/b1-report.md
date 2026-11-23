# B1 — Billing + error reporting: recovery report

## Status
Finished and verified. Only the owned files were changed; `web/*`, `studio/auth.py`, `studio/ai.py`,
`studio/accounts.py`, `studio/transcribe.py` and `data/` were not touched by this slice.

## Defects found and fixed
1. `studio/billing.py::plans()` built its dedupe set from the paid plans themselves, so **every paid plan was
   filtered out** and checkout could never be offered. Now dedupes only against `free`/`byok`.
2. Webhook idempotency: a duplicate event `INSERT` was caught inside an open transaction, leaving SQLite/
   PostgreSQL in a failed state (500 on commit). Now a SAVEPOINT is used; duplicates return
   `{"received": true, "duplicate": true}` cleanly.
3. `customer.subscription.*` events updated the row by the metadata user id instead of the subscription's stored
   owner, which could steal or duplicate another account's row. The stored owner now wins, mismatches are
   rejected, and one row per account is upserted.
4. `checkout.session.completed` without a `subscription` id (one-off payment, `mode=payment`) granted a paid tier.
   A subscription id and subscription mode are now required.
5. Error reports: the `context` field was defined but dropped; quoted `key="..."` values escaped scrubbing; the
   generic key rule consumed the word `Bearer` before the Bearer rule ran, leaving raw tokens. Fixed the field,
   widened the token pattern and reordered scrubbing (Bearer first).
6. `/api/billing/plans` and `/api/billing/subscription` now convert billing configuration errors into HTTP
   errors; the webhook bumps the affected owner's sync version after a verified event.

## Owned files
- `.env.example` — Stripe and error-report settings documented; no keys.
- `studio/config.py`, `studio/db.py`, `studio/server.py` — settings, four tables, seven routes.
- `studio/billing.py` (new, 408 lines), `studio/error_reports.py` (new, 171 lines).
- `tests/test_billing_errors.py` (new) — harness-style PASS/FAIL script, takes a base URL.
- `scratch/b1_boot_check.py` (rewritten) — real server boot check with temp `PEAKCUT_DATA` and spare ports.
- `.audit/b1-report.md` — this report.

## Verification (actual output)
- `python scratch/b1_boot_check.py --with-harness-test`: exit 0, **60 PASS / 0 FAIL**, two `ALL PASSED`.
  Three real servers were started on temporary data folders (ports 8877 unconfigured, 8878 with a fake webhook
  secret, 8879 accounts-on for the harness test). Covered: plans; checkout 503 when unconfigured; bad/absent
  HMAC; consent required; on-disk and admin-view scrubbing; per-user JSON file; admin gating for anon and two
  users; signed checkout granting `paid/pro`; one-off payment granting nothing; duplicate event idempotency;
  tampered body rejection; signed cancellation removing the entitlement.
- `python tests/test_billing_errors.py <base url>`: 26/26 PASS against a real accounts-on server (invoked by the
  boot check; the existing `tests/run.py` was not modified).
- `python -m py_compile` on all owned Python files: clean. Static scan: no hardcoded real secrets, shell calls,
  eval/exec, pickle or string-built SQL; only test-only fake key markers and expected harness prints.
- `python tests/run.py`: 1m43.934s, exit 1. All suites ran; permissions, abuse/limits, security/hardening,
  local mode and the other untouched flows passed. Six unrelated groups failed in modules owned by no B1 slice:
  live rolling-buffer timing (1 check), Twitch chat spike (`KeyError: 'buffer_min'`), AI token optimisation (same
  `KeyError`), 9:16 framing fallback (2 checks), circular rolling buffer (2 checks), post text
  (`NameError: _one_prompt`). None exercises billing or error reporting; no B1 regression was observed.

## External configuration required
Stripe is optional. An operator must set `PEAKCUT_BILLING_PROVIDER=stripe`,
`PEAKCUT_BILLING_SECRET_KEY` (or `_FILE`), `PEAKCUT_BILLING_WEBHOOK_SECRET` (or `_FILE`), and at least one
`PEAKCUT_BILLING_PRICE_*` (or a `PEAKCUT_BILLING_PLANS` JSON list). Point the Stripe webhook at
`/api/billing/webhook` for `checkout.session.completed` and
`customer.subscription.{created,updated,deleted}`. Checkout then creates a real HTTPS Stripe session; with no
configuration it returns a clear 503 and never a fake success. No real Stripe call was made during verification.

## Concerns
- The six harness failures above predate this slice and live in `studio/live.py`, `studio/render.py` and
  `studio/brain.py`; they need their owning agents' attention.
- Git reports pre-existing CRLF→LF warnings for `.env.example`, `studio/db.py` and `studio/server.py`.
- Starlette emits a TestClient deprecation warning in some pre-existing harness tests.
