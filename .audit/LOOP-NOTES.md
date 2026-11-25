# LOOP notes — PeakCut audit, redesign and completion

## L — Lock the objective
Objective: audit, fix and complete the existing PeakCut application in place at C:\Dev\PeakCut,
adding a premium yizerge.in-inspired marketing surface (landing, Features, Billing & Plans, Guides,
What's New), preserving the original PeakCut brand/colors/logo, and making all listed workflows
actually work with verified tests.

## Constraints
- Work IN C:\Dev\PeakCut; preserve working features and existing data. No rewrite for its own sake.
- Preserve PeakCut brand identity; add the exact footer: "PixelDreamStudios — Engineered by Manish Nehra"
  and portfolio link https://manishnehra.vercel.app/ (explicitly requested by the user for this project).
- No fake functionality, placeholders, or hardcoded credentials. External keys via operator config.
- Max 2 concurrent subagents (shared model quota). Read-only audits first, disjoint file ownership for edits.
- LOOP phases: LOCK -> ORGANIZE -> OPERATE -> PROBE -> POLISH -> PROVE; stop when criteria pass.

## Acceptance criteria (verifiable)
1. Written audit of frontend/backend/security/UI with prioritised, file:line-located defects and a
   fix plan; original data untouched.
2. Public pages: landing + Features + Billing & Plans + Guides + What's New with consistent premium
   design, responsive layouts, translucent initially-hidden navbar appearing on scroll, exact footer.
3. Working functionality: guided tour (start/navigate/restart), Google OAuth + email auth/session/
   logout, billing plans/checkout/subscription management, AI provider config (custom endpoints, keys,
   models, validation, connection test), navbar/footer/routing, all popups positioned on-screen.
4. Consent-based error reporting: sanitised logs/stack/timestamp/action/repro + extra comments +
   user review before submission; no credentials or sensitive data exposed.
5. Verification: original `python tests/run.py` harness + browser checks of every new flow; regressions
   fixed; final report with changed files, tests/results and external configuration requirements.

## O — Organize
- Wave 1 (parallel, read-only): backend audit agent + frontend/UI audit agent. Controller inspects
  design reference and harness. Notes written here before fan-out (LOOP rule).
- Later waves: disjoint edit slices, then review + real execution.

## O/P log
- 2026-11-23: skill activated, objective/criteria locked, audit agents dispatched. Scores: pending.
- Important pre-existing state: `studio/transcribe.py` has 2 uncommitted lines (a real `w["e", ...]` bug fix and docstring repair). PRESERVE these changes; do not revert or overwrite them.
- Design reference extracted: yizerge.in uses premium dark hero, animated caption demos, numbered 01/02/03 feature blocks, comparison tables, FAQ, template gallery, sticky translucent navigation and strong CTA sections; user explicitly requires PeakCut brand/colors/logo preserved.
- Billing: no STRIPE/BILLING env keys found; billing likely missing and must be implemented with operator-supplied provider credentials (never hardcoded).

## O — Organize (post-audit, 2026-11-23)
Audit reports: .audit/backend.md (206 lines), .audit/frontend-ui.md (257 lines). Preserve
uncommitted studio/transcribe.py fix.

Slices (disjoint ownership, max 2 concurrent):
- F1 Public redesign: web/landing.html + new web/{features,billing,guides,whats-new}.html +
  web/public.css (new) + web/brand unchanged. Translucent scroll-revealed navbar, mobile hamburger,
  exact footer, yizerge-inspired composition, PeakCut palette/logo preserved.
- F2 App UI fixes: web/index.html, web/auth.html, web/reset.html, web/css or inline styles in those
  files. Tour overlay/restart, dropdown/popover/dialog positioning, AI settings validation, auth
  inline errors, error-report consent modal UI.
- B1 Billing + error reporting: studio/billing.py, studio/error_reports.py, new DB tables in db.py,
  config.py/.env.example, routes added in server.py (B1 owns server.py for this wave).
- B2 Auth/AI security: studio/auth.py, studio/ai.py, studio/accounts.py (no server.py), global CSRF
  changes must be prepared as a patch for controller to apply after B1 finishes.
- V Final verification: tests/run.py + browser checks, screenshots, fix regressions.

Wave 1 dispatched: F1 + B1. Wave 2: F2 + B2 (after server.py frees).
Scores: c1 3 (audits done), c2/c3/c4 0, c5 pending.
- Wave 1 agents failed (model temporarily unavailable) but left substantial valid partial work: landing/features redesign + billing/error-report services, routes and DB/config edits; py_compile clean. Recovery agents dispatched to finish and commit their owned files. Scores: c1 3, c2/c3/c4 1 in progress, c5 pending.
