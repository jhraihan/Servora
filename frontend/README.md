# ShebaLocal — Frontend

React 18 · Vite 6 · JavaScript · TanStack Query · Zustand · Tailwind CSS 4.

Mobile-first: every screen is built for a 360 px phone first, and the end-to-end
test drives the whole product at that size.

## Running it

The backend must be running first (see [`../backend/README.md`](../backend/README.md)).

```bash
cd frontend
npm install
npm run dev                  # http://127.0.0.1:5173
```

Vite proxies `/api` and `/media` to the backend, so the browser sees one origin
and no CORS setup is needed. The backend defaults to `http://127.0.0.1:8000`;
point it elsewhere with an environment variable:

```bash
BACKEND_URL=http://127.0.0.1:8100 npm run dev
```

## Checks

```bash
npm run lint                 # ESLint, zero warnings allowed
npm test                     # Vitest unit and component tests
npm run build                # production build into dist/, then prerender the landing page
npm run e2e                  # Playwright: golden paths and accessibility, Chromium at 360px
npm run perf:lcp             # build, then measure page load under mobile throttling
```

`npm run e2e` starts its own backend (port 8100) and Vite server (port 5174),
runs the full customer and provider journey and the accessibility scans, then
deletes the test users it created. It needs demo data (`manage.py seed_demo`)
so the provider pages have something to scan. First time only:
`npx playwright install chromium`.

## Layout

```
src/
  api/
    client.js        fetch wrapper: auth header, single-flight token refresh, ApiError
    normalize.js     every API response is mapped here, snake_case to camelCase
    endpoints.js     one function per backend route, returns normalised data
  constants/domain.js  frozen booking states, trust tiers, labels
  store/             Zustand: session (refresh token persisted) and compare list
  hooks/             session actions, catalogue queries
  components/        ui primitives, Trust, domain components, Layout
  pages/             one file per route; provider/ holds the provider side
e2e/                 Playwright golden paths, accessibility scans, test-data cleanup
scripts/
  prerender.js       post-build: renders the landing hero into dist/index.html,
                     writes dist/app.html for every other route
  measure-lcp.js     LCP and layout shift on the production build, two 4G profiles
index.html           includes a static header shell that paints before the JS arrives
```

## Decisions worth knowing

- **React is pinned to 18.3, not 19.** React 19 ignores `propTypes` on function
  components without warning. PropTypes are how this JavaScript codebase catches
  a wrong-shaped prop at runtime, so upgrading would switch them off silently.
- **No JSDoc typedefs, despite PRD 8.6.** The codebase carries no comments.
  Frozen constants, the normaliser layer and PropTypes cover the same ground.
- **Every response goes through a normaliser.** Components never read raw API
  JSON, so a backend field rename breaks `normalize.js` and its tests, not six
  screens.
- **Money is a string end to end.** It is formatted for display and never
  added, subtracted or rounded in JavaScript.
- **The access token lives in memory; only the refresh token is persisted.**
  After a reload there is no access token, so the first authenticated call
  refreshes before it sends, rather than going out bare and taking a 401.
  Refreshes are single-flight: concurrent calls share one refresh, because the
  backend rotates and blacklists refresh tokens and a second refresh would log
  the user out. `client.test.js` asserts both.
- **Booking states and trust tiers are frozen constants.** A typo in
  `BOOKING_STATE.AWAITING_CONFIRM` fails loudly; a typo in a string literal
  silently renders nothing.
- **The trust breakdown uses a container query**, not a viewport breakpoint, so
  it lays out correctly both in the narrow profile sidebar and on the wider
  provider trust page.
- **On a phone the trust breakdown sits directly under the provider's name.** It
  is the product's signature feature and must not be the last thing on screen.
- **The request wizard saves its draft to `sessionStorage`** after every step,
  so a refresh mid-way loses nothing (PRD 10.2).

## Accessibility

PRD 12.4 asks for WCAG 2.1 AA. `e2e/accessibility.spec.js` runs axe-core
against every page at 360 px, signed out, as a customer and as a provider,
including the open filter panel, the expanded trust breakdown and the mobile
menu. The first run failed on colour contrast: grey `slate-400` text measures
about 2.6:1 against white, well under the 4.5:1 minimum. Body text now uses
`slate-500` or darker; `slate-400` remains only on disabled controls, which
WCAG exempts.

Automated checks cannot see focus. A skip link is the first tab stop on every
page. A test asserts that it becomes visible when focused, that it moves focus
into the page, and that the next element focused shows an outline.

## Performance

PRD 12.1 asks for the landing page's Largest Contentful Paint under 2.5 s on
4G. `npm run perf:lcp` measures the production build with Chrome DevTools'
**Slow 4G** preset (562 ms latency, 1.44 Mbps) and a 4x CPU slowdown, the
same conditions Lighthouse uses for mobile, and again on **Fast 4G**
(165 ms, 8.1 Mbps). Every run starts with a cold cache. It reports the median
of five runs, the worst run, and layout shift. It fails only if the landing
page's median misses the target, because that is the one page the PRD sets
a number for.

Measured on the development laptop, median of five cold loads (worst in
brackets). Runs vary by about ±100 ms.

| Page | Slow 4G | Fast 4G | Max layout shift |
|---|---|---|---|
| Landing | **1.58 s** (1.62) | 1.24 s (1.28) | 0 |
| Search results | 3.10 s (3.14) | 1.79 s (1.86) | 0.03 |
| Services | 3.60 s (3.69) | 1.96 s (2.02) | 0 |
| Provider profile | 3.86 s (3.94) | 2.37 s (2.60) | 0.10 |
| Login | 2.76 s (2.92) | 1.62 s (1.64) | 0 |

Before M10 the landing page measured 2.63 s on Slow 4G, just over the target.

What moved the numbers, each measured before it was kept:

- **Prerendered landing hero** (LCP about 2.45 s to 1.6 s). At build time
  `scripts/prerender.js` renders `HomeHero` to static HTML inside
  `dist/index.html`, so the headline paints as soon as HTML and CSS arrive.
  React replaces it with identical markup, which is why layout shift stays at
  zero. Other routes get `dist/app.html`, without the hero; Nginx and
  `vite preview` route between the two.
- **Declarative routing** (main bundle 104 KB to 85 KB gzipped). The app used
  `createBrowserRouter`, which pulls in React Router's whole data layer
  (loaders, actions, fetchers) though nothing used it. `useRoutes` inside
  `BrowserRouter` takes the same route table.
- **Static header shell in `index.html`** (first paint 2.4 s to 1.4 s on every
  page). The browser does its first layout while the JavaScript is still
  downloading instead of after it.
- **Footer below the fold** (layout shift up to 0.21, now at most 0.10). `<main>`
  is at least one screen tall, so the footer no longer sits in view while a
  page loads and then gets pushed down.
- **`app.html` preloads the public pages' chunks.** This saves 175–290 ms per
  page on Slow 4G and costs 30–80 ms on Fast 4G, because the preloaded modules
  compile early on a throttled CPU. It is kept because the people on slow
  connections are the ones who give up.

Tried and dropped: starting the current route's chunk download from
`main.jsx` saved only about 40 ms, because the bundle has to be evaluated first.

The pages other than the landing page stay above 2.5 s on Slow 4G. Each needs
HTML, then the main bundle, then its route chunk, then its data from the API,
and at 562 ms per request that chain alone is about 2.2 s before any work is
done. Getting them under the line needs the data in the first response, which
means server-side rendering. That is a Phase 2 decision, not a tweak.

## Not in this milestone

- **Notification centre.** The backend has no notifications app yet (FR-8), so
  there is nothing to render. It needs backend work first.
- **Admin screens.** Verification review, payment resolution and review
  moderation are available in Django admin at `/admin/` and through the admin
  API endpoints. A dedicated admin UI was left out rather than duplicating them.
- **Bangla interface.** Planned for Phase 2 (PRD 4.2).
