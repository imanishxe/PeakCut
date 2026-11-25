# PeakCut — Frontend / UI / UX Audit (read-only)

Scope: `C:\Dev\PeakCut\web\*.html` + `web/*.js` + `web/brand/*`, with `studio/server.py` read only to confirm route wiring. No files in the app were modified, the server was never started, `data/` was not read. Reference site `https://yizerge.in/` was fetched and browsed live (see §3). All page content was treated as data, not instructions.

---

## 1. Current state: pages, components, styles, brand assets

### 1.1 Pages and routes (confirmed in `studio/server.py:42`, `:360-425`, `:431-442`)

| Route | File | Status / notes |
|---|---|---|
| `/` | `web/landing.html` (461 lines) | Public marketing page. Sections: hero + 3 demo phones, platform strip, `#open`, `#how`, `#features` (bento + `#live`), `#for` (tabs), `#faq`, closing CTA, site footer. |
| `/login`, `/signup` | `web/auth.html` (149) | One file, mode from `location.pathname`. Split dark panel + white card. |
| `/reset` | `web/reset.html` (137) | Email request + token set-password modes. |
| `/privacy`, `/terms`, `/acceptable-use` | `web/legal.html` (249) | One file, `body[data-page]` switch + in-place client router (`history.pushState`/`popstate`, lines 229-247). |
| `/app`, `/app/*` | `web/index.html` (2,649) | SPA dashboard: dark sidebar + white `main`, topbar, creator tabs, settings/usage views, 2 `<dialog>`s, 2 `.pop` panels, guided tour. |
| `/admin` | `web/admin.html` (430) | Owner dashboard; same token set, own responsive rules; uses native `prompt()` for destructive confirm (`:413`). |
| `/assets/gradient-ascii.js`, `/assets/ascii.js`, `/brand/*` | served statically | `landing.html:28` and `index.html:853` load `gradient-ascii.js` for the hero (`#heroAscii`, `#appAscii`). |

No `/features`, `/billing`, `/guides`, `/whats-new` route exists. That is the largest structural gap versus the brief.

### 1.2 Exact brand tokens to preserve (do not change these values)

From `web/index.html:12-20` (identical core values in `admin.html:13-21`, `auth.html:13-16`, `reset.html:13-16`, `landing.html:30-33`, `legal.html:12`):

```
--brand:#FF8B33      --brand-press:#F27A1F   --brand-ink:#2A1A12
--brand-soft:#FFF2E8 --brand-line:#FFD9BC    --brand-deep:#A9480A
--frame:#1E1612      --frame-2:#2C221D       --frame-line:rgba(255,255,255,.08)
--frame-text:#F4EEEA --frame-dim:#A99A91
--bg:#FFFFFF         --muted:#F7F4F1         --line:#EEE8E4     --line-2:#E1D9D3
--text:#211813       --dim:#6D6159           --faint:#A0948C
--good:#0F8A57       --good-soft:#E6F6EE     --bad:#D3343F     --bad-soft:#FDECEE
--live:#E5323F       --r-lg:16px             --r:12px          --r-sm:8px
--ease:cubic-bezier(.2,.7,.2,1)  (landing only)
```

Other hard-coded values that are part of the look: footer `#1E1612` / `#B9A597` / `#8C7B70` (`landing.html:38-49`), CTA hover `#FF9A4C`, banner `#FFF4E6` / `#7A3E0C`, live red `#E5323F`, caption highlights Bounce `#FFFF00`, Hype `#FF3C3C`, Clean `#6BD7FF` (`index.html:1425`).

### 1.3 Logo, typography, motion, media

* `brand/logo.svg` — 797x220 wordmark, lettering fill **`#310001`** (dark), used on white surfaces.
* `brand/logo-light.svg` — same wordmark, fill **`#FBF7F8`**, used on `--frame` / footer.
* `brand/favicon.svg` — 220x220 rounded mark, background **`#FF8B33`**; `brand/logo-email.png` for mail.
* `brand/demo-{bounce,hype,clean}.{jpg,mp4}` — real product output; already used as hero phones and caption previews. Reuse in Features / What's New; do not substitute stock imagery.
* UI font: **Geist** 400/500/600/700 (landing also 800) from Google Fonts, fallback `"Segoe UI", system-ui, sans-serif`; body 14px/1.5 in app, 16px/1.55 in public pages; headings `letter-spacing:-.03em` to `-.045em`. `Inter:300` is requested in `index.html:10` but never used — safe cleanup.
* Caption fonts (must stay): `Archivo Black`, `Anton`, `Poppins ExtraBold`, with local TTFs in `studio/fonts/` (`index.html:1425-1429`).
* Hero ASCII gradient palette (keep): `#ffb27a, #ffffff, #ffd2ae, #ffe0c2, #fff1e6`, shape `horizon`, `lightMode:true`, low opacity (`landing.html:404`, `index.html:1355`).
* Motion: `prefers-reduced-motion` is respected on every page; preserve it in all new CSS/JS.

### 1.4 Component inventory

* Buttons: `.btn` + `.primary/.dark/.sm/.lg/.ghost/.danger`, pill CTA in landing nav/footer; heights 44 / 38 / 52 / 40 / 34 px across files — inconsistent (see §5).
* Cards: `.card`, `.tile`, `.cell`, `.plan`, `.panel`, `.ft`, `.trio`, `.mock`, `.ai-card`; radii 8/10/12/16/999 all in use.
* Overlays: `<dialog id="clipdlg">`, `<dialog id="formdlg">` (`index.html:846-847`); `#bellpop` (role=dialog), `#acctpop` (role=menu) (`:850-851`); `.pick-menu` custom listboxes (`:341-359`, `:1431-1476`, `:1754-1756`); toast containers; guided tour `#tour` (`:768-802`, `:947-1065`).
* Navigation: app sidebar (`#nav`, `#foot`), topbar (`#utabs` creator tabs), settings sub-nav, landing anchor nav, legal tab nav. **The app `#foot` is account controls, not a site footer**; public pages have the real footer.

---

## 2. Broken / incomplete interactions (prioritised)

Severity: **P0** blocks a core flow, **P1** major usability/quality, **P2** polish/maintenance.

### P0-1 — Guided tour eats clicks on the highlighted element
`index.html:770` `.tr-block{position:absolute;inset:0}` has no `pointer-events:none` and no click handler; `.tr-dim` (`:771`) also has none (only `.tr-ring` has `pointer-events:none`). `clip-path` cuts the visual hole but hit-testing falls through to `.tr-block`, so during every step the user cannot click the very control the tour points at. Fix: `.tr-block,.tr-dim{pointer-events:none}` and make `.tr-card` the only interactive layer; if overlay-click-to-close is wanted, put the handler on `.tr-dim` and keep the hole non-interactive deliberately.

### P0-2 — Tour cannot be reliably restarted; no restart affordance
`startTour()` bails on `if ($("#tour")) return;` (`:948`), while `close()` removes the root only after a 300 ms `setTimeout` (`:1040-1044`). "Take the tour" (`:1182`, `:2535`) clicked inside that window is a no-op. The final step's button is labelled "Start clipping" (`:1029`) and only closes; there is no "Restart tour" control. Fix: remove the root synchronously after fading via a `finished` flag / allow re-entry, and add a `Restart tour` button (or `data-tour="restart"` on the last step) that calls `close(true)` then `startTour()`.

### P0-3 — Public nav vanishes on tablets/phones
`landing.html:265` `header.nav nav{display:none}` at <=960 px, plus `:272` `header.nav .signin{display:none}` at <=560 px. No hamburger, no replacement menu: Features, How it works, Live clipping, Open source, FAQ become unreachable by navigation (only by scrolling). Fix: add a toggle button + `.nav-links` panel with `aria-expanded`/`aria-controls`, Escape close, and focus management; see §4.1.

### P0-4 — Tour steps 6-7 can point at nothing
`index.html:964,966` target `#foot .ai-card` and `#foot .me`; both are rendered only when `S.status.ai` / `S.status.user` exist (`drawShell`, `:1274-1278`). If the status payload is partial (offline/single-user edge), `rectOf()` returns null and the card floats centre-screen with no highlight. Fix: filter steps at start (`steps.filter(s => !s.sel || $(s.sel))`) and fall back to a real anchor; also force `#foot` visible on <=900 before measuring.

### P1-5 — Required footer credit is absent everywhere
No occurrence of `PixelDreamStudios`, `Manish Nehra` or `manishnehra.vercel.app` in `web/`. Current bottom bars: `landing.html:396`, `legal.html:226` ("© … PeakCut / Free and open source."), auth/reset side footer `auth.html:88`, `reset.html:82`. Add the exact string and portfolio link to all four public templates (§4.4).

### P1-6 — Translucent, scroll-revealed navbar not implemented
`landing.html:74-76` is `position:sticky; background:#fff` and `:403` only adds a `.stuck` border. `index.html:74-75` + `:2624` do the same for the app topbar. Requirement asks for initially hidden/translucent on scroll. Fix in §4.1.

### P1-7 — Custom dropdowns can clip / open off-screen
`index.html:73` `main{overflow-y:auto}` (the other axis computes to `auto`, so horizontal overflow is clipped/scrollable); `:345` `.pick-menu{position:absolute;top:calc(100% + 6px);left:0}` opens **down and right only**; the only guard is `max-width:calc(100vw - 48px)` at <=640 (`:806`). The "File under creator" picker in `.composer-bar` (`:1380`) and `.evpick` in live stats (`:1754`) sit near right edges; with long creator names (min-width 230/240) the menu is cut by `main`. Fix: JS flip above/left on open using `getBoundingClientRect()` vs viewport/`main` rect; set `right:0` when `rect.right + 240 > mainRight - 8`; `max-height:min(280px, calc(100vh - rect.top - 16px))`; close on `scroll` of `#main` as well as outside click.

### P1-8 — `.pop` panels positioned once, never repositioned
`openPop()` (`index.html:1153-1159`) writes inline `left`/`bottom` from the current sidebar/anchor rect; there is no `resize`/scroll recompute. The <=900 rule forces `left:12px!important;bottom:74px!important` (`:653`), so between 901-1100 px with a collapsed sidebar or after a resize the panel can overlap, hang below the fold, or detach from its trigger. `#bellpop` declares `role=dialog` / `aria-haspopup=dialog` (`:850`) but focus stays on the trigger, there is no focus trap and no `aria-modal` (correct for a popover — change the role to consistent dialog or menu semantics). Fix: central `positionPop()` called on open, `resize` and `#main` scroll; clamp with `Math.min(Math.max(...))`; return focus on close.

### P1-9 — Dialogs overflow short viewports
`index.html:608-616`: `dialog{max-width:calc(100vw - 32px)}`, `.dlg{width:450px}`, but no `max-height`/`overflow` on the generic dialog; `.editor` is 2-column until 900 with `max-height:calc(100vh - 48px)` and only `.panel` scrolls. `admin.html:125` does it correctly for `.dlg.wide`. At 740x360 or with long update notes (`updateHow`, `:1234-1245`) the confirm/update content runs off-screen. Fix: `dialog{max-height:calc(100dvh - 32px);overflow:auto}` globally, `.editor{grid-template-columns:1fr}` at <=900 (already) and `stage{min-height:0}`.

### P1-10 — AI settings: stale key on provider switch, weak validation
`index.html:2336` clears `#ai_model` and `#ai_base` when the provider changes but **not `#ai_key`** (`:2084`); the old provider's key is then sent to the new provider by `aisave` (`:2376`) and `aimodels` (`:2366`). When a key is already saved, the placeholder says "Saved… Paste a new key to replace it" but "Find models" still posts the empty input, relying on server-side fallback. Model is a free-text comma list (`:2086-2087`) with no empty/format check, and every failure is only a transient `toast()` (`:929-934`, `:2373-2383`) with no inline field error. Fix: clear the key on provider change (or explicitly show "using saved key for <provider>" and send `key:null` when untouched), add `aria-describedby` inline error spans + `aria-invalid`, disable Save while empty, show test result in the panel not only in a toast.

### P1-11 — Auth and reset forms: validation/feedback gaps
`auth.html:97-146` uses `novalidate` and only checks "email and password present"; no inline field errors, no focus to `#err`, no email-format or signup-name feedback; Google button starts `hidden` and silently stays hidden if `fetch('/api/public')` fails (`:131-133`); password toggle exists (`:120-126`) but the reset page's new-password fields (`reset.html:93-98`) have no show/hide control or `aria-describedby` for the "At least 8 characters" hint. `next` redirection is safely restricted (`auth.html:111`) — keep that. Fix: shared field-error helper, `err.focus()` on failure, show a graceful "Email sign-in only" fallback when `/api/public` fails, add password toggle to reset.

### P1-12 — Tour keyboard focus leaks on resize / last step
`keys()` (`:1049-1056`) traps Tab inside the card, but `show()` re-focuses `Next` on every step (`:1029`) including Back, which is disorienting; `Escape`, arrows and resize are handled globally while the tour is open and removed on close, which is correct. `setTimeout(() => root.classList.add("on"), 60)` (`:1063`) can re-show a card after `close()` in a background tab. Guard with `if (!closed)`.

### P2-13 — Responsive breakpoints are fragmented
15+ distinct widths: 1100, 960, 900, 860, 760, 700, 640, 560 plus `max-height:700` (`index.html:752,767,800-806`, `landing.html:263-273`, `auth.html:74`, `admin.html:139-155`). Same concepts switch at different widths (sidebar at 900 vs nav at 960 vs footer at 760). Consolidate to 1100 / 900 / 700 / 480 with documented intent; keep `max-height:700` only for tour art.

### P2-14 — Routing/content gaps and a copy contradiction
* No routes/anchors for Features (only `#features` on home), Billing & Plans, Guides, What's New.
* `landing.html:312,368,396` says "no plans or fees" / "Free to use", while the brief asks for Billing & Plans + checkout/subscription management. The app's `plans` settings (`index.html:2587-2590`) are cost-hint inputs, not paid tiers. Resolve with product owner; recommended honest "Billing & Plans — free software, you pay your AI provider" page, **no fake checkout**.
* `admin.html:413` uses `prompt()` for account deletion — breaks the design system and is hard to automate; replace with the existing `confirmDialog` plus typed confirmation inside `#dlg`.

### P2-15 — Toast/notification layering and semantics
`#toasts{z-index:50}` (`index.html:619`) sits below `.pop{z-index:60}` and `#tour{z-index:200}`, so critical "Report" / error toasts are hidden during the tour; `.ntoast` has `role=status` (`:1205`) while containing a button — use a non-interactive live region plus a separate focusable container. Minor, but affects perceived brokenness.

---

## 3. Design gap versus https://yizerge.in/ (live reference, not copied)

Observed on the live site (browser + extraction, 23 Nov 2026):

* **Canvas/type:** near-black `#141414` body, text `#F2F2F0`, `Google Sans Variable`, huge h1 (~76 px/600), h2 ~34 px, tight tracking, generous `clamp(56px,7vw,96px)` section rhythm. Cobalt-blue accent, white/blue headline split, muted grey body copy.
* **Structure:** blue 2-message announcement bar at very top; translucent dark nav with Features / **What's new (1.3 badge)** / Changelog / **Guides (dropdown)** / Find my download / theme icon / blue pill CTA. Hero = avatar social-proof pill -> oversized headline -> floating real product preview cards -> one-line value prop -> wide email+CTA bar with two buttons.
* **Pages:** `/#features`, `/#bento`, `/#compare`, `/#faq`, `/pay` (secure checkout, "what's included", instant delivery, 3 reassurance items), `/explore` (version showcase + before/after slider + numbered feature list + "by the numbers"), `/changelog` (version timeline with New/Better/Fixed tags), Guides dropdown to concrete how-to pages, footer "© 2026 … Engineered by [name]" with links.
* **Principles worth adopting:** one idea per section; real product screenshots over illustration; version badge + dated timeline for freshness; explicit reassurance (delivery/secure/no-watermark); comparison table with honest rows; announcement bar that links to What's New; consistent pill CTAs; footer engineering credit.

**Direction for PeakCut (transform principles, not the blue brand):** keep PeakCut's orange `#FF8B33` + Geist + the three real demo clips. Build a **cinematic dark hero on `--frame` `#1E1612`** with an orange highlighted headline, one primary "Get clips free" pill and one secondary "See how it works", floating demo-phone cards and trust notes; then alternate white/warm-tint sections for Features, Comparison, Billing & Plans, Guides, What's New, FAQ, closing CTA. This matches the reference's confidence and hierarchy while remaining unmistakably PeakCut. Target page set:

1. **Landing `/`** — announcement strip ("Clips while the stream is still live -> #live"), hero, proof strip, How it works, Features, comparison, FAQ, closing CTA.
2. **Features `/features`** — deeper bento from `landing.html:344-357` + caption styles using the three demo assets + live recording + AI accounting.
3. **Billing & Plans `/billing`** — truthful: free/open source, "you pay your AI provider", cost calculator using existing usage data concepts, provider links; clearly state no PeakCut subscription. Flag the contradiction in §2 P2-14 before adding any paid-tier UI.
4. **Guides `/guides`** — quickstart, add a streamer, caption styles, connect accounts, self-hosting; link to existing FAQ content and docs.
5. **What's New `/whats-new`** — version timeline sourced from the existing update payload (`S.status.update` / `up.notes`, `index.html:1234-1245`); tag New/Better/Fixed; link to Changelog if added.

---

## 4. Concrete DOM + CSS changes (minimal, safe)

### 4.1 Translucent navbar, hidden initially, revealed on scroll

`web/landing.html` — replace `:74-76` and `:403`; add a mobile toggle inside `header.nav .wrap` (before `nav`):

```html
<button class="navtoggle" id="navtoggle" aria-label="Open menu" aria-controls="navlinks" aria-expanded="false">icon</button>
<nav id="navlinks" aria-label="Sections">existing links, plus Guides / What's new / Billing</nav>
```

```css
header.nav{position:fixed;inset:0 0 auto;z-index:40;transform:translateY(-110%);
  background:rgba(255,255,255,.78);backdrop-filter:blur(16px) saturate(150%);
  border-bottom:1px solid rgba(42,26,18,.08);
  transition:transform .32s var(--ease),background-color .2s ease,border-color .2s ease}
header.nav.show,header.nav:focus-within{transform:none}
body{--nav-h:60px}
.hero{padding-top:calc(var(--nav-h) + clamp(40px,7vh,96px))}  /* no layout jump when nav is hidden */
@media (max-width:960px){
  .navtoggle{display:grid;place-items:center;width:44px;height:44px;border:0;background:transparent}
  #navlinks{position:absolute;top:100%;left:0;right:0;display:none;flex-direction:column;
    padding:8px 16px 16px;background:rgba(255,255,255,.96);backdrop-filter:blur(16px)}
  header.nav.mopen #navlinks{display:flex}
}
```

```js
const navEl=document.getElementById("nav"), navToggle=document.getElementById("navtoggle");
const onScroll=()=>navEl.classList.toggle("show", scrollY>24 || navEl.contains(document.activeElement));
addEventListener("scroll", onScroll, {passive:true}); onScroll();           // replaces line 403
navToggle?.addEventListener("click",()=>{const open=navEl.classList.toggle("mopen");
  navToggle.setAttribute("aria-expanded",String(open));});
addEventListener("keydown",e=>{if(e.key==="Escape"){navEl.classList.remove("mopen");navToggle?.setAttribute("aria-expanded","false");}});
```

Apply translucency only to `index.html:74` (`background:rgba(255,255,255,.82);backdrop-filter:blur(14px)`), **keep the app topbar visible** — it holds the page title and primary actions and must not be hidden. Keep its existing `.stuck` border logic (`:2624`).

### 4.2 Tour fixes (`web/index.html`)

```css
.tr-block,.tr-dim{pointer-events:none}
.tr-card{max-height:calc(100dvh - 24px);overflow:auto}
```

In `startTour()`: `const steps = [...].filter(s => !s.sel || $(s.sel));` and add a `data-tour="restart"` button on the last step; in `close()` remove `root` immediately after adding the fade class plus a `let finished=false` guard, remove the `:1063` stale timeout, and route restart as `close(); requestAnimationFrame(startTour);`. Focus the first step's `Next` once, not on Back (`:1029`).

### 4.3 Popups, dropdowns, dialogs (`web/index.html`, `web/admin.html`)

```css
dialog{max-height:calc(100dvh - 32px);overflow:auto}
.pop{max-height:min(520px,calc(100dvh - 100px))}
.pick-menu{max-height:min(280px,calc(100dvh - 80px))}
```
Add a shared `positionPop(p, anchor)` used by `openPop()` and bound to `resize` + `#main` `scroll`; clamp `left` to `[12, innerWidth - p.offsetWidth - 12]` and `bottom` to `[12, innerHeight - p.offsetHeight - 12]`. For `.pick-menu`, flip with `.pick.flip-up .pick-menu{top:auto;bottom:calc(100% + 6px)}` and `.pick.flip-left .pick-menu{left:auto;right:0}`, set from the button rect on open. Add `document.querySelector("#main").addEventListener("scroll", closePicks, {passive:true})`. In `admin.html:413`, replace `prompt()` with a typed input inside `#dlg`.

### 4.4 Exact footer — all public pages

Bottom bar of `landing.html:396`, `legal.html:226`, and the `.side small` lines in `auth.html:88` / `reset.html:82`:

```html
<span>© <span class="fy"></span> PeakCut</span>
<span>PixelDreamStudios — Engineered by <a href="https://manishnehra.vercel.app/" target="_blank" rel="noopener noreferrer">Manish Nehra</a></span>
```

Keep the em dash with spaces exactly as written. In `auth.html`/`reset.html` the credit sits in the dark side panel: add `color:inherit` on the link, same text.

### 4.5 Spacing / buttons / cards / typography consistency

Add one token block per public template (copy from `index.html:12-20` for parity):

```css
:root{--s-1:4px;--s-2:8px;--s-3:12px;--s-4:16px;--s-6:24px;--s-8:32px;--s-12:48px;--s-16:64px;
      --btn-sm:38px;--btn:44px;--btn-lg:52px;
      --shadow-card:0 1px 2px rgba(42,26,18,.05),0 10px 28px rgba(42,26,18,.06)}
.btn{height:var(--btn);padding:0 var(--s-6);border-radius:var(--r)}
.btn.sm{height:var(--btn-sm);padding:0 var(--s-4)}
.btn.lg{height:var(--btn-lg);padding:0 26px}   /* add to landing.html/legal.html */
.card,.cell,.tile,.panel{border:1px solid var(--line);border-radius:var(--r-lg);
  padding:var(--s-6);box-shadow:var(--shadow-card)}
h1,h2{text-wrap:balance} h1{font-size:clamp(44px,6vw,76px);line-height:1.04;letter-spacing:-.045em}
h2{font-size:clamp(28px,3.2vw,40px);line-height:1.1;letter-spacing:-.035em}
section{padding:var(--s-16) 0}  /* landing currently 64px; 96px reads more premium */
```

Use `--s-*` for all new gaps; convert the footer CTA radius 10 px and nav CTA pill 999 px into explicit `.btn.cta` / `.fcta` variants rather than ad-hoc overrides. Remove the unused `Inter:300` request from `index.html:10`.

### 4.6 Route wiring (handshake with backend owner; no changes made here)

Add `"/features": "features.html"` etc. to `studio/server.py:42` or implement one templated `pages.html` with `body[data-page]` like `legal.html`; keep `Cache-Control` and `{{SITE}}` placeholder substitution consistent with `_LANDING`/`_LEGAL_HTML` (`server.py:360-425`). Titles/meta/JSON-LD need one block per new page; do not duplicate the FAQ schema outside the FAQ page.

---

## 5. File-by-file implementation plan (minimal safe changes)

| File | Changes | Risk / note |
|---|---|---|
| `web/landing.html` | §4.1 nav (fixed/translucent/reveal + mobile toggle), §4.4 footer, §4.5 tokens/type, new announcement strip and section links to `/features`, `/billing`, `/guides`, `/whats-new`; dark hero variant using `--frame` + orange `.hl`. | Keep existing section IDs and `#live` anchor; keep the three demo videos and GradientASCII call at `:404-405`. Replace only the `.stuck` listener at `:403`. |
| `web/index.html` | §4.2 tour, §4.3 popups/dropdowns/dialogs, translucent topbar only, AI key/validation fixes (`:2061-2090`, `:2336`, `:2363-2383`), remove unused Inter font. | File is a monolith; change in small diffs and re-run app smoke tests. Do not touch `go()`/routing or renderer logic. |
| `web/auth.html` | Inline field errors + focus, Google fallback, `next` preserved (keep `:111`), password toggle aria state, footer credit. | Keep endpoint names and `dest` regex. |
| `web/reset.html` | Password show/hide + `aria-describedby`, inline errors, footer credit. | Keep the two-mode token flow. |
| `web/legal.html` | Footer credit + shared tokens; leave `data-page` router intact. | Legal text must stay byte-identical. |
| `web/admin.html` | Dialog max-height, replace `prompt()`, footer credit if a site footer is added. | Owner-only surface; low traffic. |
| `web/features.html`, `web/billing.html`, `web/guides.html`, `web/whats-new.html` (new) | Reuse `landing.html` header/footer/tokens; sections assembled from existing content; no invented prices or metrics. | Confirm Billing copy with product owner first (§2 P2-14). |
| `studio/server.py` | Only route/PAGES map + template placeholders for the four new pages. | Coordinate with backend auditor; no data access. |

---

## 6. Playwright / browser verification checklist

Local app was **not** launched for this audit (read-only instruction); run this after implementation. Viewports: 1440x900, 1024x768, 900x700, 768x1024, 390x844, 360x640, 740x360 (landscape).

1. **Tour:** click "Take the tour" -> `#tour` visible; all 8 steps reachable with Next/Back and arrow keys; card `boundingBox` fully inside viewport at every size; click the highlighted `#url` while step 2 is open -> `#url` receives focus; last-step Restart works; Escape closes, focus returns; click Restart within 300 ms of closing works.
2. **Nav:** at `scrollY=0` public navbar is off-screen (`transform`), after `scrollTo(0,40)` it is visible with computed `backdrop-filter`; keyboard Tab into hidden nav reveals it; <=960 hamburger opens/closes, Escape closes, all new routes return 200.
3. **Footer:** exact text `PixelDreamStudios — Engineered by Manish Nehra` and `href=https://manishnehra.vercel.app/` present on `/`, `/login`, `/signup`, `/reset`, `/terms`, `/privacy`, `/acceptable-use`, and the 4 new pages.
4. **Popups:** open bell + account menu at every viewport; assert rect inside viewport; resize while open -> still anchored; `#main` scroll closes them; Escape closes; aria-expanded toggles; no `document.body` horizontal scroll.
5. **Dropdowns:** open "File under creator" with a 30-character creator name at 1440 and 768; assert menu rect inside `main` and viewport, `scrollWidth<=clientWidth` on `#main`; open a picker near the viewport bottom -> it flips up; ArrowDown/Up/Escape work.
6. **Dialogs:** trigger confirm/update dialog at 740x360 -> dialog rect inside viewport, scrollable, buttons reachable; editor dialog at 900 and 390 -> single column, video visible, close works.
7. **Auth:** empty submit -> inline error + focus; bad email -> inline error; password toggle flips `type` and `aria-pressed`; `?next=/app/settings/ai` survives sign-in; Google button appears when `/api/public` reports it and shows a fallback when that fetch fails; reset with token -> mismatched passwords show inline error.
8. **AI settings:** switch provider -> key field cleared/labelled correctly; "Find models" with saved key populates the datalist; Save with empty model shows inline error; test failure appears in the panel; Save button re-enables after each request.
9. **Responsive/content:** no horizontal overflow on any page at 360 px; headings use the new scale; cards share 16 px radius and 24 px padding; all 5 public pages cross-link correctly and `history.back()` restores the right view; reduced-motion emulation removes transitions.
10. **Console/network:** zero uncaught errors or failed requests on each page after load and after each interaction above; verify with `page.on("console")`/`page.on("pageerror")`.

**Audit verification status:** reference site inspected live via fetch + browser (nav, colours, typography, sections, `/pay`, `/explore`, `/changelog`); all PeakCut findings are from static source with exact line references. No local server, Playwright run, screenshot of the local app, or data-file access was performed, per the read-only constraint.
