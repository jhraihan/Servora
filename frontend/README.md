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
npm run build                # production build into dist/
npm run e2e                  # Playwright golden paths in Chromium at 360px
```

`npm run e2e` starts its own backend (port 8100) and Vite server (port 5174),
runs the full customer and provider journey, then deletes the test users it
created. First time only: `npx playwright install chromium`.

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
e2e/                 Playwright golden paths and test-data cleanup
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
- **The access token lives in memory; only the refresh token is persisted.** On
  a reload the first request gets a 401, refreshes, and retries. Refreshes are
  single-flight: concurrent 401s share one refresh call, because the backend
  rotates and blacklists refresh tokens and a second refresh would log the user
  out. `client.test.js` asserts this, and it is visible in the E2E server log.
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

## Not in this milestone

- **Notification centre.** The backend has no notifications app yet (FR-8), so
  there is nothing to render. It needs backend work first.
- **Admin screens.** Verification review, payment resolution and review
  moderation are available in Django admin at `/admin/` and through the admin
  API endpoints. A dedicated admin UI was left out rather than duplicating them.
- **Bangla interface.** Planned for Phase 2 (PRD 4.2).
