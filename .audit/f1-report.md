# F1 report — public marketing slice (recovery)

Status: COMPLETE. Commit `56e9077` — `feat(web): finish public marketing pages with shared premium design`
(5 files changed, 1845 insertions, 402 deletions). Only F1-owned files were staged.

## Files
- `web/landing.html` — patched partial redesign: fixed shared CSS parse bug, nav order/mobile CTA, exact footer.
- `web/features.html` — patched partial page: same CSS/nav/footer fixes, self-link changed to guides CTA.
- `web/billing.html` (new) — Free + BYOK cards, backend-driven checkout state, honest disabled state, hosted-Stripe flow explanation, FAQ.
- `web/guides.html` (new) — six real workflows sourced from the app UI: source, options, AI, clip review, creator/live, posting.
- `web/whats-new.html` (new) — five dated changelog entries grounded in repository commit dates.
- `web/public.css` — deliberately NOT created: no static CSS route exists in `studio/server.py` (`/assets/{name}` serves `.js` only), so an external stylesheet would 404. Shared CSS is inlined consistently in all five pages.

## Defect found and fixed
The partial shared CSS contained `.page-hero{...padding:calc(var(--nav-h) + clamp(64px,9vw,120px) 0 clamp(64px,8vw,104px)}` — an unclosed `calc()`. Chromium silently discarded every later rule (CSSOM dropped from 132 rules to 81), killing the mobile `@media (max-width:960px)` block, translucent-nav styles, reveals and footer styles. Corrected to `padding:calc(var(--nav-h) + clamp(64px,9vw,120px)) 0 clamp(64px,8vw,104px)}` in all five pages. Verified: CSSOM rule count back to 132; hamburger computed `display:grid` at <=960px.

## Structural verification (actual output)
`grep -c 'PixelDreamStudios — Engineered by Manish Nehra' web/{landing,features,billing,guides,whats-new}.html`
→ 1 / 1 / 1 / 1 / 1. Portfolio URL `https://manishnehra.vercel.app/` → 1 in each.
`grep -c 'id="navtoggle"'` → 1 each; `grep -c 'checkReveal'` → 4 each.
`grep -n 'Checkout requires configured payment credentials' web/billing.html` → default status banner at line 237 plus two failure branches (lines 364, 367).
Python `html.parser` check (ids, links, anchors, brand tokens, honest billing, 6 guide anchors, 5 dated entries):
```
landing.html    lines= 468 links= 38 PASS
features.html   lines= 362 links= 33 PASS
billing.html    lines= 383 links= 31 PASS
guides.html     lines= 363 links= 35 PASS
whats-new.html  lines= 328 links= 29 PASS
STRUCTURAL OVERALL: PASS
```
All local `/brand/*` assets referenced by the pages exist on disk.

## Browser verification (real Chromium, local static server on 127.0.0.1:8765)
- 1440 / 1024 / 768 / 390 px, all 5 pages: `scrollWidth - clientWidth = 0` (no horizontal overflow); exact footer text and portfolio link present in rendered text.
- At load: navbar `transform: matrix(1,0,0,1,0,-71.28)` (hidden), background `rgba(255,255,255,0.82)`; after scroll with dispatched scroll event: class `nav show`, `transform: none`.
- Hamburger: `display:none` at 1440/1024, `display:grid` at 768/390; click sets `aria-expanded=true`, menu `display:flex`, mobile CTA visible; second click and Escape close it.
- Reveal elements enter `.in` on scroll (e.g. features 5 → 10, billing 4 → 7); reduced-motion fallback rule present.
- Billing without API: status = "Checkout requires configured payment credentials… the plan catalogue could not be loaded from this server"; checkout button `disabled=true`; no redirect.
- Billing with mocked backend catalogue (`configured:true`, `checkout_available:true`, one Pro plan): status switched to "Checkout is available…", one paid card rendered with backend price/limits, placeholder hidden; clicking checkout surfaced the backend's 503 message ("Billing is not set up on this server.") and stayed on the page — no fake success, no fabricated redirect.

## Concerns / hand-off
1. `studio/server.py` still lacks routes for `/features`, `/billing`, `/guides`, `/whats-new` (`PAGES` unchanged) and `sitemap.xml` does not list them. The pages are correct files but will 404 in the real app until the controller wires routes. Not fixed here because `server.py` is outside F1 ownership.
2. `/api/billing/plans` is not in `OPEN`, so anonymous visitors get redirected to `/login`; the page handles that with an honest "Sign in to see your plan and checkout state" message. Making the catalogue public is a controller decision.
3. `studio/transcribe.py` pre-existing uncommitted fix was never staged or touched; it remains modified in the worktree.
4. The `write_file`/`patch` helpers failed in this environment (shell-quoting wrapper errors); files were written with direct Python file I/O instead. Contents were re-read and verified structurally and in-browser.
5. Billing backend landed in a separate concurrent commit `202d06f`; F1 only consumes its documented public API.
