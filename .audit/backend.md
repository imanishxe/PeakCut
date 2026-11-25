# PeakCut — Backend & Security Audit (read-only)

Date: 2026-11-23 · Auditor: Backend/Security · Commit at time of review: `e29dc31`
Scope: `C:\Dev\PeakCut`. Source and tests only. No server was started, no request was sent, nothing under `data/` was read or copied, and no tracked file was changed. All file contents were treated as data, not instructions.

---

## 1. Executive summary

PeakCut is a compact, working FastAPI application with a strong security *foundation*: sessions are random and stored hashed, scrypt password hashes, per-user data isolation through a context variable, same-origin checks, body caps, an allowlist for video sites, signed one-hour clip links, CSP/security headers and a substantial test harness. **The defects are gaps and half-finished features, not a broken core.** Do not rewrite it.

The most important findings:

| # | Severity | Finding | Evidence |
|---|---|---|---|
| F01 | Critical (acceptance) | **No billing of any kind**: no tables, routes, env keys, webhooks, entitlements or checkout. A dead UI handler posts `plans` to a settings endpoint that silently drops it. Public copy says the product is free. | `db.py:27-120`, `usage.py:3-4`, `accounts.py:252`, `web/index.html:2587-2589`, `web/landing.html:23,312,368` |
| F02 | High | **CSRF gap on admin-equivalent routes**: the gate applies strict "Origin must be stated" only to `/admin` and `/api/admin/*`; `/api/ai`, `/api/apps`, `/api/storage`, `/api/youtube-cookies` and `/api/speech/*` only check the role, not a stated Origin. Combined with a saved AI key this can become key exfiltration. | `server.py:100-102,125,142-149,301-313,1363-1406` |
| F03 | High | **First Google login silently deletes an existing password** on an email-matching account and signs out all its sessions; with email verification off by default, an attacker who controls that email can take the account without proving the old password. | `auth.py:388-392`, `config.py:232`, `server.py:599-602` |
| F04 | High (functional) | **"Record automatically when they go live" is a no-op**: the UI and creator setting promise it and the edit route comments claim it works, but auto-start and resume were removed. | `web/index.html:1896`, `creators.py:18`, `server.py:1303-1304`, `live.py:1149-1188` |
| F05 | Medium | **Consent-based error reporting does not exist**. A server feedback API exists but the UI's "Report this" button only copies text to the clipboard and opens an external link; no structured report, sanitisation, consent checkbox, review step or test. | `server.py:1183-1194`, `feedback.py:16-33`, `web/index.html:1227-1233,1792`, `safe.py:7-11` |
| F06 | Medium | **Google callback can 500 on malformed/error responses** — no HTTP-status or payload validation before `.json()['access_token']`, and the route catches only `AuthError`. | `auth.py:369-377`, `server.py:593-602` |
| F07 | Medium | **AI "test" validates only the first configured model**; fallback models can be invalid while the dashboard reports "ready". | `ai.py:179-185`, `brain.py:224-239`, `web/index.html:2373-2383` |
| F08 | Medium | **Universal custom AI endpoints**: `base_url` accepts any `http(s)` address with no host/private-IP/redirect check, and model discovery forwards the server key to that address. Intended for Ollama/custom models, but it is an SSRF and key-exposure primitive. | `ai.py:123-127,145-176`, `config.py:204-205,211` |
| F09 | Medium | **Platform-supplied upload URLs are trusted blindly** (YouTube `Location`, Instagram `uri`, TikTok `upload_url`); a hostile/compromised API response can redirect a Bearer token or file upload to another host. | `accounts.py:353-355,515-521,647-655` |
| F10 | Medium | **Rate-limit gaps and process-local throttles**: posting, post actions, Instagram token paste and Google-start are unthrottled; all throttles live in one dict and reset on restart / do not work across workers. | `server.py:582-590,1481-1491,1639-1659`, `auth.py:21,57-69` |

Also worth fixing, but lower: Windows file permissions on secret files are only "best effort" (`ai.py:136-139`, `accounts.py:59-62`, `server.py:1633-1634`); the 20-second session cache can briefly serve a stale non-admin user (`auth.py:277-300`, `server.py:126-130`); the tour flag is DB-backed, so it is fine; the tour content itself is static (`web/index.html:952-968`).

---

## 2. Architecture map

### 2.1 Request pipeline (`studio/server.py`)

1. `app = FastAPI(...)` with docs/openapi disabled (`server.py:39`).
2. Middleware **Compress** (`217-229`) gzips text but passes media through for byte ranges.
3. Middleware **Gate** (`81-214`) is the security boundary. For every HTTP request it:
   - rejects non-GET requests whose `Origin`/`Sec-Fetch-Site` does not match (`100-102`, `301-313`);
   - caps body size (256 KB generally; upload only up to `MAX_UPLOAD_MB`) using `Content-Length` **and** a streaming byte counter (`103-122`);
   - resolves the visitor IP from the connection, or from a trusted proxy / Cloudflare header (`232-298`);
   - resolves the user from the session cookie, or uses one built-in owner when `PEAKCUT_ACCOUNTS=0` (`126-141`);
   - hides the whole admin area with 404 for non-admins (`142-149`);
   - pre-checks verification, job slots and quota before accepting an upload (`157-165`);
   - sets CSP, `nosniff`, frame/robots/referrer/HSTS/cache headers and handles conditional GETs (`169-199`);
   - sets `ctx._uid` for the request and short-circuits unchanged `/api/sync` calls (`201-209`).
4. Startup (`54-78`): DB init, stale upload cleanup, fonts, tool check, model fetch, then background threads for jobs, live, posting and update checks.

### 2.2 Route groups in `studio/server.py`

| Lines | Group | Representative routes |
|---|---|---|
| `348-449` | Public pages and metadata | `/`, `/login`, `/signup`, `/reset`, `/privacy`, `/terms`, `/acceptable-use`, `/app/{rest:path}`, `/admin/{rest:path}`, `/healthz`, `/robots.txt`, `/sitemap.xml` |
| `452-468` | Static brand/assets | `/brand/{name}`, `/assets/{name}`, `/favicon.ico` |
| `472-603` | Auth | `/api/public`, `/api/auth/signup`, `/resend-verification`, `/auth/verify`, `/forgot`, `/reset`, `/login`, `/logout`, `/me`, `/password`; `/auth/google/start`, `/auth/google/callback` |
| `605-620` | Dashboard status | `/api/status` (user, update, disk, AI brief, tour flag, connect readiness) |
| `623-989` | Videos, uploads, sync | `/api/sync`, `/api/jobs`, `/api/jobs/{jid}`, `/api/preview`, `POST /api/jobs`, `/api/upload`, `/api/upload/start`, `PUT/DELETE /api/upload/{upid}[/{n}|/finish]` |
| `992-1139` | Clips and account data | clip render/text/write/delete, `/api/bulk/delete`, `/api/clips.zip`, `/api/creators/{cid}` delete, `/api/account/delete`, `/media/{jid}/{name}` |
| `1141-1213` | Admin mail/feedback helpers | `/api/admin/email-preview`, `/api/admin/test-email`, `/api/feedback`, `/api/admin/feedback[/{fid}]` |
| `1215-1348` | Notices, creators and live | `/api/notifications[ /read]`, `/api/me/photo`, `/api/channel-preview`, `/api/creators[/{cid}|/{cid}/avatar|/{cid}/live]`, `/api/live/{jid}/stop|/clip` |
| `1352-1447` | AI and speech | `/api/usage`, `/api/ai`, `/api/ai/models`, `/api/ai/test`, `/api/speech[/{lang}]` |
| `1451-1637` | Social accounts and settings | `/api/overview`, `/api/settings`, `/api/accounts[/{aid}]`, `/api/accounts/instagram/token`, `/oauth/{platform}/start|callback`, `/pub/{token}.mp4`, `/api/storage[...]`, `/api/apps`, `/api/youtube-cookies` |
| `1639-1676` | Posting and alerts | `/api/posts`, `/api/posts/{pid}/{action}`, `/api/alerts/test` |
| `1681-1727` | Admin dashboard | `/api/admin/overview`, `/api/admin/users/{uid}`, `/.../disabled`, `/.../delete` |

### 2.3 Modules

| Module | Role / important lines |
|---|---|
| `studio/auth.py` | Passwords/scrypt (`30-46`), throttles (`57-69`), email links (`110-171`), users/login (`184-221`), local owner (`244-259`), sessions (`267-337`), Google OAuth (`341-402`), profile photo (`408-439`) |
| `studio/accounts.py` | Server app credentials (`71-155`), connect OAuth state (`157-196`), signed clip links (`199-234`), per-user settings (`241-271`), platform accounts (`275-299`), YouTube/Instagram/TikTok API calls (`310-671`) |
| `studio/account.py` | Irreversible deletions, ZIP download (`22-117`), creator and account deletion (`121-174`) |
| `studio/admin.py` | Admin overview/user detail (`37-119`), disable (`123-140`), CLI grant/revoke (`144-175`) |
| `studio/ai.py` | Provider table (`25-36`), saved config (`43-107`), save/discover/test (`110-185`), errors (`188-249`), request builders (`327-500`) |
| `studio/posting.py` | Queue, gaps/daily caps (`55-88`), worker (`110-160`), stats (`163-188`), overview with view/earnings estimates (`211-248`) |
| `studio/ctx.py` | `ContextVar` user identity and per-user change counter (`11-70`) |
| `studio/db.py` | SQLAlchemy Core tables: users, sessions, usage, email_ok/tokens, feedback, notices, admin_log (`27-112`) |
| `studio/config.py` | Env/dotenv, data dirs, limits, AI/email/Google config (`8-261`) |
| `studio/jobs.py`, `live.py`, `profiles.py`, `creators.py`, `media.py`, `render.py`, `usage.py`, `feedback.py`, `safe.py`, `storage.py` | Pipeline, recording, creator workspaces, site allowlist, rendering, token accounting, feedback, error text sanitising, data-folder movement |
| `web/index.html` | Entire signed-in SPA: tour (`946-1065`), AI settings (`2363-2383`), action dispatcher (`2530-2619`) |

**Auth model.** Browser identity comes only from the `peakcut_session` cookie; the owner id is put into `ctx` by the gate and read via `ctx.uid()` (`ctx.py:18-22`, `server.py:201`). Background threads set it with `ctx.as_user(...)`. This is the right design and must be preserved. With accounts off there is one local owner (`auth.py:244-259`); the README explicitly warns not to expose that mode.

**Data model.** DB: accounts/sessions/usage/feedback/notices/admin log. Files: per-user folders under `users/<uid>` (creators, jobs, accounts JSON, photo), global `data/ai.json` (AI key), `apps.json` (OAuth client secrets), `posts.json` (queue), `link.key` (HMAC key for public clips), `youtube-cookies.txt`, `storage.json`.

---

## 3. Detailed findings

### 3.1 Billing / subscriptions — F01 (Critical, functional/acceptance)

* **Nothing exists.** There is no billing table in `db.py:27-120`; no `STRIPE`/billing variables in `.env.example`; no checkout, webhook, customer, plan, invoice or entitlement code anywhere in `studio/` or `web/`. `usage.py:3-4` states explicitly: "Nothing is charged for and nothing is limited here."
* **Dead UI:** `web/index.html:2587-2589` handles a `plansave` action that gathers `[data-plan]` inputs and PUTs `{plans: p}` to `/api/settings`. No `[data-plan]` element exists anywhere in the web pages, and `accounts.save_settings()` ignores every key not in `SETTING_DEFAULTS` (`accounts.py:248-266`, especially `252`). The save therefore silently does nothing and still toasts "Plans saved".
* **Contradictory public messaging:** `web/landing.html:23,312,368` says "free and open source… no plans, no seats and no limits". Introducing billing requires changing that copy.
* **Misleading earnings:** `posting.py:229` computes `earnings = views / 1000 * creator.rate_per_1k` (a campaign-rate field, `creators.py:24,96-97`) and shows it in the overview. It is an estimate, not money held or paid by PeakCut.
* **Fix (minimal, no rewrite):** keep the free/local mode and add an *optional* operator-configured billing layer: `PEAKCUT_BILLING_PROVIDER`, `*_SECRET_KEY`, `*_WEBHOOK_SECRET`, `*_PRICE_*` read from env (`config.py`); a new `billing.py` with a small plan catalog, checkout-session create, portal link and signed webhook verification; two new tables for customers/subscriptions (`db.py`, additive only); `/api/billing/*` routes plus one unauthenticated webhook route that verifies the provider signature instead of a session; an entitlement helper used by the gate for paid features; replace the dead `plansave` handler with real calls and update landing copy. Never hardcode keys.

### 3.2 Auth, Google OAuth and sessions

* **F03 — Google linking (High).** `auth.py:388-392`: when a Google `sub` signs in with an email that already has a password account but no `google_sub`, the code sets `google_sub` and `password_hash=None` and deletes all sessions, with no confirmation step. Because `VERIFY_EMAIL` defaults to `0` (`config.py:232`), that password account's email may never have been verified. Anyone who controls that Google identity can take over the account. The "different Google identity cannot claim the same email" check at `auth.py:386-387` only helps *after* the first link. **Fix:** require `email_verified` (already checked, `auth.py:376`) **and** either a previously verified email in `email_ok`, or an explicit "link accounts" flow that asks for the existing password; otherwise create a separate account or refuse with a clear message. Add a test for the refused case.
* **F06 — Google callback robustness (Medium).** `auth.py:369-375` posts the code, checks only `status_code != 200` for the token, then reads `tok.json()['access_token']` and calls `userinfo` without checking its status. A 200-with-unexpected-body or a provider error page yields `KeyError`/`JSONDecodeError`, which `server.py:600` does not catch (only `auth.AuthError`) → HTTP 500. **Fix:** wrap both responses in a helper that validates status and required fields and raises `AuthError("Google sign-in failed…")`; log the reason server-side without tokens. Add tests with malformed 200 responses.
* **F02 — CSRF on admin-equivalent endpoints (High).** The gate's strict `must_say=True` check is limited to `admin_area = /admin or /admin/ or /api/admin/` (`server.py:125,142-149`). `_from_here(..., must_say=False)` returns `True` when no `Origin` header is present (`server.py:310-313`). Admin-only endpoints outside that prefix (`/api/ai` at `1363-1406`, `/api/apps` `1596-1608`, `/api/storage` `1553-1593`, `/api/youtube-cookies` `1613-1636`, `/api/speech` `1418-1447`) therefore accept a state-changing request that states no origin. A cross-site request that can suppress `Origin` could set `base_url` to an attacker host while `ai.save` preserves the existing key for the same provider (`ai.py:128-135`), so the next AI call sends the key to that host. **Fix:** add those prefixes to `admin_area` (smallest safe change) or apply `must_say=True` to every mutating method; keep the existing direct-route `_admin()` checks. Update any non-browser clients/tests that omit `Origin`.
* **Session handling is otherwise sound.** Random 32-byte tokens, SHA-256 storage only (`auth.py:263-274`), HttpOnly/SameSite=Lax/secure-when-HTTPS cookies (`335-337`), invalidated on disable/revoke/password change (`admin.py:134-140`, `auth.py:224-236`), hashed one-time links with TTL (`auth.py:110-133`), per-IP/per-email throttles (`server.py:485-550`), dummy-hash timing defence (`auth.py:46,214-216`). **Preserve.**
* **Residual notes.** Throttles are process-local (`auth.py:21,57-69`): a restart clears them and multiple workers would not share them. `_sess` caches a user row for 20 seconds (`auth.py:277-300`), so a role change that bypasses `auth.forget()` could be briefly stale; CLI revoke and admin disable do call forget (`admin.py:139,152`). Switching accounts off promotes the oldest account to admin (`auth.py:250-255`) — an intentional migration path, but it must be documented as a privileged operation.

### 3.3 AI provider configuration

* **F07 — Test covers one model only (Medium).** `ai.test()` calls `call(ms[0], ...)` (`ai.py:181-185`) and the UI toasts "Saved… the AI is ready" from that single result (`web/index.html:2376-2381`). `brain.ask_ai()` loops over all models (`brain.py:224-239`), so a bad second/third fallback only fails during real work. **Fix:** iterate all configured models in `test()` with a short timeout, return per-model results and set `ready` accordingly; extend `tests/test_ai.py` with a two-model case where the second fails.
* **F08 — Custom endpoint SSRF/key exposure (Medium).** `ai.save()` accepts any `https?://\S+` address (`ai.py:123-127`); `ai.list_models()` accepts a `base_url` from the request body and, when the provider matches, attaches the saved key (`ai.py:145-176`). There is no host allowlist, no blocking of link-local/private addresses (except the documented Ollama loopback case), no redirect policy and no DNS-rebinding protection. This is partly intentional ("custom OpenAI-compatible address", README:92), but the least safe form of it. **Fix:** for `list_models`, ignore a client-supplied base URL unless the provider is `custom` and the address matches the saved one; require an explicitly typed key when using an unsaved address; disable redirects on all AI `httpx` calls; reject resolved private/link-local IPs except an explicit `PEAKCUT_AI_ALLOW_LOCAL=1` (Ollama path).
* **Config validation that works — preserve:** provider allowlist, model-id regex, max 5 models, key required unless Ollama/custom (`ai.py:113-131`); key redaction in `_fail`, `list_models` errors and `_ai_error` (`ai.py:163,246`, `server.py:1359-1360`); key never returned by `/api/ai` except a 4-character hint (`ai.py:99-107`, asserted in `tests/test_local.py:68`); model discovery filters non-chat Gemini models (`ai.py:165-176`); schema fallback for models that reject `responseSchema` (`ai.py:402-415`); error explanations (`ai.py:200-219`).
* **Design gap:** in accounts-on mode every AI route requires `_admin()` (`server.py:1365,1371,1385,1399`), so ordinary users cannot choose their own provider/key; there is one global key. If per-user keys are a requirement, that is new work — say so explicitly rather than implying it exists.
* **Secret at rest:** `ai.json` is written with `chmod 600` (`ai.py:135-140`), which is only advisory on Windows. Keep the file outside the web root (it is) and document Windows ACL expectations.

### 3.4 Error reporting — F05 (Medium)

* The server half exists: `POST /api/feedback` accepts `kind`, `message`, `page`, `context`, throttles to 10/hour and stores it in the `feedback` table with admin notices (`server.py:1183-1194`, `feedback.py:16-33`, `db.py:77-88`). `feedback.py:21-22` only length-checks the message.
* The user half does **not** use it: `openFeedback()` (`web/index.html:1227-1233`) copies `context` to the clipboard and opens `status.links.follow` (Instagram) in a new tab. The "Report this" button on a failed video (`web/index.html:1792`) only supplies a text string "Video failed: … | error". There is no stack, timestamp, action/repro metadata, no structured payload, no consent toggle, no preview/review before sending, no redaction of keys/tokens/URLs and no automated test.
* `safe.friendly()` strips server-like paths and trims text (`safe.py:7-11`) but is used for *displayed* errors, not for a report format, and does not redact secrets.
* **Fix (minimal):** add `POST /api/errors` with a strict schema `{message, stack?, timestamp, action, repro, comments, consent: true}`; validate `consent is True`, cap every field, run a new `safe.redact_error()` that removes `Authorization:`/`Bearer` values, `apikey`/query tokens, known AI key values, e-mail addresses and user paths; store in a new `error_reports` table; admin listing route. In `web/index.html`, replace `openFeedback` with a dialog that pre-fills the sanitised report, shows it for review and requires a consent checkbox before enabling Send. Add `tests/test_error_report.py` (redaction, consent refusal, oversized input, non-admin authz).

### 3.5 Tour — implemented, preserve

* A complete guided tour exists: 8 steps, keyboard support, spotlight, card placement, close/restart (`web/index.html:946-1065`); first-login auto-start (`2643`); "Take the tour" menu action (`1182`, `2535`).
* Backing flag: `tour_done` default `False` (`accounts.py:26-27`), exposed by `/api/status` (`server.py:612`), persisted via `/api/settings` (the key *is* in `SETTING_DEFAULTS`, `accounts.py:254`), and covered by `tests/test_permissions.py:75-78`.
* Gaps: no test drives the DOM tour itself (only the flag); if public pages gain Billing/Guides/What's New, the tour steps do not mention them and `tour_done` will suppress auto-start for existing users. **Fix:** add versioned tour steps (e.g. `tour_version`) rather than resetting `tour_done`, and have the frontend audit agent add browser checks of start/next/back/restart.

### 3.6 Creator / live

* **F04 — auto-record is gone but still advertised (High functional).** Creator default `auto_watch: True` exists (`creators.py:18`) and the setup UI says "Record automatically when they go live — Checks straight away, then every two minutes" (`web/index.html:1896`). The edit route still says "if they are live right now, recording starts within seconds" (`server.py:1303-1304`). But `live.py:1160-1169` only refreshes live *status*, `_watch_one`'s docstring says auto-start was removed, `_resume_recordings()` is a no-op (`1186-1188`), and `profiles.py` contains no `start_session` call. `posting.py:223` still reports state `waiting` for `auto_watch` creators. **Fix:** decide one behaviour. Smallest safe change: relabel the setting to "Watch live status" and remove the two misleading comments/state label; if auto-record must work, restore a throttled `live.start_session()` call in `_watch_one` behind `config.MAX_LIVE_PER_USER`/`MAX_LIVE_TOTAL` (already enforced at `live.py:1116-1119`) and test that a second poll does not start a duplicate.
* Manual live flow is complete and guarded: URL validation (`live.py:1104-1111`), per-user/global limits and load checks (`1116-1119`), language model check (`1123-1126`), ownership on stop/clip (`live.py:107-110`, `server.py:1327-1348`), clipping throttle (`server.py:1341-1343`).
* Site allowlist is string-based (`media.py:70-78`) and applies to `/api/preview`, job creation, channel preview and live start. It blocks the obvious `youtube.com.evil`, userinfo and metadata-IP tricks (`tests/test_abuse.py:59-62`) but not DNS rebinding or a whitelisted site that redirects to an internal address; yt-dlp follows redirects by default. **Fix (Low/Medium):** after DNS resolution reject private/link-local IPs unless explicitly allowed, and add a redirect host check in `_ydl`/`live.resolve`.

### 3.7 Posting / connected accounts

* Queue is per-user (`posting.py:19-21,191-208`), gaps and daily caps are applied in `_next_slot` (`55-64`), the worker runs as the owning user (`145-160`), and failed posts retry twice. Preserve.
* **F09 — trusting remote upload URLs (Medium).** `accounts.py:353-355` PUTs the file **with a Bearer token** to `start.headers["Location"]` from YouTube; `accounts.py:515-521` POSTs an OAuth token to `box.get("uri")` from Meta; `accounts.py:652-655` PUTs to `box["upload_url"]` from TikTok. None of these URLs is host-checked. **Fix:** a shared `_trusted_upload_url(url, allowed_hosts)` helper in `accounts.py` that enforces `https` (or loopback for tests) and an exact/allowlisted hostname before any credential or file is sent; call it at the three sites.
* **Rate limits (F10, Medium).** `POST /api/posts` (`server.py:1639-1648`) and `/api/posts/{pid}/{action}` (`1651-1659`) have no throttle; `post_action`'s `pid` is not shape-checked before being used in the lookup (ownership still enforced by `posting._mine()`). `POST /api/accounts/instagram/token` (`1481-1491`) has no throttle and calls Meta with an arbitrary user-supplied token. `GET /auth/google/start` (`582-590`) has no throttle (callback does, `598`). **Fix:** add `_throttle("posts:"+ctx.uid(), 30, 600)`, a tighter limit for `now=True`, and throttles for token-paste and Google-start; validate `pid` with `[0-9a-f]{16}`.
* `account.py:34-49` correctly confines clip deletion to paths inside the job/clips directories; `jobs.get()` is user-scoped (`jobs.py:290-293`); `/media` and `/pub` validate file names and signed links (`server.py:1122-1137`, `accounts.py:215-234`). Preserve.

---

## 4. Security issue inventory and test coverage

| Area / issue | Severity | Existing test coverage | Gap |
|---|---|---|---|
| Role escalation via signup body, role changes, admin 404 | High | `tests/test_permissions.py:36-58,80-114` | none material |
| Cross-user data isolation (creators, jobs, overview, notices, usage, avatars) | High | `tests/test_permissions.py:60-78`; `tests/test_ai.py:101-114` | no coverage for cross-user post IDs or `/api/jobs/{id}/clips/...` mutations with someone else's ids (routes are user-scoped by code) |
| CSRF with explicit hostile `Origin` | High | `tests/test_permissions.py:58,97-98`; `tests/test_local.py:42-49,65`; `tests/test_connect.py:40-41` | **no test for missing `Origin`/no `Sec-Fetch-Site` on `/api/ai`, `/api/apps`, `/api/storage`, `/api/youtube-cookies` (F02)** |
| Password storage, session hashing, one-time links | High | `tests/test_hardening.py:31-39`; code inspection | no test for reset-token reuse/expiry; no test for Google link takeover (F03) |
| Google OAuth | High | `tests/test_hardening.py:41-65`; `tests/test_abuse.py:65-66` (state cookie) | **malformed Google responses (F06), throttle of `/auth/google/start`** |
| AI config, keys, model discovery, custom endpoints | Medium | `tests/test_local.py:53-119`; `tests/test_ai.py:63-171` | **no SSRF/base_url-host test, no fallback-model test (F07/F08)** |
| Path traversal / ID validation | Medium | `tests/test_permissions.py:70-71`; `tests/test_upload_parts.py` | good; no fuzz test for `clip.file` from stored job JSON |
| SSRF via video links | Medium | `tests/test_abuse.py:59-62` | DNS rebinding / redirect chains not covered |
| Body-size caps / chunked abuse | Medium | `tests/test_abuse.py:23-35` | good |
| Rate limits | Medium | `tests/test_abuse.py:154-159` | only creator-edit and login throttles are exercised |
| Secret leakage to browser | Medium | `tests/test_local.py:68`; `tests/test_connect.py:47,60` | good for AI key, app secrets, YouTube cookies; no test for error-report redaction (none exists) |
| Billing | Critical | none (feature absent) | new tests needed |
| Consent error reporting | Medium | none (feature absent) | new tests needed |
| Tour | Low | `tests/test_permissions.py:75-78` (flag only) | no DOM/browser test |
| Posting uploads | Medium | `tests/test_connect.py` (mocked platforms) | no test that a hostile upload URL is rejected |

Harness: `tests/run.py:48-83` runs 36 test files against a throwaway server/empty data folder. It is healthy and must be extended, not replaced.

---

## 5. What must be changed vs what must be preserved

**Must change**
1. Add billing as an optional, operator-configured layer; remove the dead `plansave` handler and fix public "no plans" copy (F01).
2. Add a consent-based, sanitised error-reporting flow (F05).
3. Close the CSRF gap on admin-equivalent routes (F02).
4. Make Google↔password account linking explicit/safe and make the callback robust (F03, F06).
5. Validate every configured AI model in "test" and constrain custom endpoints/redirects (F07, F08).
6. Resolve the auto-record promise vs implementation (F04).
7. Validate platform-returned upload URLs and add the missing throttles (F09, F10).
8. Add focused tests for all of the above.

**Must preserve**
- The Gate architecture, body caps, header set and proxy-IP logic (`server.py:81-313`).
- `ctx.uid()` ownership model and `ctx.bump()`/cheap `/api/sync` fast path (`ctx.py`, `server.py:691-715`).
- scrypt hashes, hashed sessions/cookies, one-time hashed links and the admin-only role source (`auth.py`, `admin.py`).
- The existing guided tour and its persisted flag (`web/index.html:946-1065`, `accounts.py:27`).
- AI provider abstraction, model discovery, key redaction and usage accounting (`ai.py`, `usage.py`).
- Signed clip links, site allowlist, post queue spacing/caps, rolling live buffer and the deletion guards.
- The whole `tests/run.py` harness and all 36 existing tests. The team notes in `.audit/LOOP-NOTES.md:37` also flag uncommitted changes in `studio/transcribe.py`; do not revert or overwrite them.

---

## 6. File-by-file fix plan (smallest safe changes)

| File | Change | Severity |
|---|---|---|
| `studio/server.py` | Add admin-equivalent prefixes to `admin_area` (`:125`) so `must_say=True` applies to `/api/ai`, `/api/speech`, `/api/storage`, `/api/apps`, `/api/youtube-cookies`; add `POST /api/errors`; add billing routes + signature-verified webhook allowlist entry; add throttles at `:582`, `:1481`, `:1639`, `:1651`; validate `pid`; correct the misleading comment at `:1303` or restore auto-start. | F02,F01,F05,F04,F10 |
| `studio/auth.py` | Validate Google token/userinfo responses and raise `AuthError` (`:369-377`); require verified email or explicit re-auth before dropping a password (`:388-392`). | F06,F03 |
| `studio/ai.py` | Test all configured models with per-model results (`:179-185`); harden `save()`/`list_models()` address rules and disable redirects (`:123-127`, `:145-176`). | F07,F08 |
| `studio/accounts.py` | Add shared `https`+host allowlist check before using remote upload URLs (`:353`, `:515`, `:652`); if billing lands, add entitlements lookup — do **not** silently accept `plans` in `save_settings()` (`:252`). | F09,F01 |
| `studio/live.py` | Either restore a throttled auto-start in `_watch_one` (`:1160-1169`) or make the docstrings/no-op explicit (`:1186-1188`); keep `:1104-1119` limits. | F04 |
| `studio/creators.py` | If auto-record is removed, rename/retire `auto_watch` default/UI label (`:18`); keep `plan` as metadata only unless billing enforces it. | F04,F01 |
| `studio/db.py` | Additive tables only: `error_reports`, and `billing_customers`/`billing_subscriptions` if billing is enabled (`:115-116` already does `create_all`). | F01,F05 |
| `studio/config.py` | Add opt-in `PEAKCUT_BILLING_*`, `PEAKCUT_ERROR_REPORTING`, `PEAKCUT_AI_ALLOW_LOCAL` env settings (`:207-232`); no keys in code. | F01,F05,F08 |
| `studio/safe.py` | Add `redact_error()` (keys, tokens, auth headers, URLs with secrets, paths, length cap) next to `friendly()` (`:7-11`). | F05 |
| `studio/feedback.py` | Optionally reuse for `kind="error"` only if the schema fits; otherwise leave untouched and add a dedicated `error_reports` writer. | F05 |
| `web/index.html` | Replace `plansave` (`:2587-2589`) with real billing calls; replace `openFeedback()` (`:1227-1233`) with a review+consent error dialog; update auto-record label (`:1896`); add versioned tour steps (`:952-968`). | F01,F05,F04 |
| `web/landing.html` | Remove/qualify "no plans or fees" (`:23,312,368`) if billing is introduced. | F01 |
| `tests/` | New `test_error_report.py`, `test_billing.py` (mocked provider), `test_csrf_hardening.py`, `test_google_errors.py`, `test_auto_watch.py`; extend `run.py:48-83`. Keep all current tests green. | all |

**Ordering suggestion:** F02 → F03/F06 → F07/F08/F09/F10 → F04 → F05 → F01 (the last one is the largest and should not block the security fixes). Run `python tests/run.py` after each slice; it uses a throwaway folder and needs no keys.
