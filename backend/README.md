# ShebaLocal — Backend

Django 5 + DRF + PostgreSQL 18. See [`../docs/ShebaLocal-PRD.pdf`](../docs/ShebaLocal-PRD.pdf) for the full specification.

## Status

**M10 Harden — complete.** 568 tests passing.

| Milestone | State |
|---|---|
| M1 Foundation (auth, OTP, roles) | Done |
| M2 Catalogue (services, locations, seed) | Done |
| M3 Providers (profiles, areas, availability, verification) | Done |
| M4 Trust engine (six factors, snapshots, audit) | Done |
| M5 Discovery (search, filters, trust ranking) | Done |
| M6 Booking (request lifecycle, state machine) | Done |
| M7 Reviews (double-blind, trust feedback) | Done |
| M8 Money (cash settlement, commission, earnings) | Done |
| M9 Frontend (React client) | Done — see ../frontend |
| M10 Harden (security, jobs, performance, deploy) | Done — see ../deploy |

## Running it

```bash
cd backend
venv\Scripts\activate
python manage.py runserver
```

API at `http://127.0.0.1:8000/api/v1/`, admin at `/admin/`.

First time only — see PRD §11.2 for the database setup, then:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env     # then fill in SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py seed_catalogue     # 8 categories, 45 services, 38 locations
python manage.py createsuperuser
```

## Tests

```bash
python -m pytest              # all 568, about two minutes
python -m pytest -k otp       # one area
```

Tests run on `config.settings.test`, which swaps in a fast password hasher.
Production-strength PBKDF2 costs about a second per hash, and with a user or
two per test that made the suite take 14 minutes.

The test runner creates and drops `test_shebalocal`, so the `sheba` role
needs `CREATEDB`:

```sql
ALTER ROLE sheba CREATEDB;
```

## Endpoints in M1

| Method | Path | Auth |
|---|---|---|
| POST | `/api/v1/auth/register/` | — |
| POST | `/api/v1/auth/otp/send/` | — |
| POST | `/api/v1/auth/otp/verify/` | — |
| POST | `/api/v1/auth/login/` | — |
| POST | `/api/v1/auth/refresh/` | — |
| POST | `/api/v1/auth/logout/` | User |
| GET/PATCH | `/api/v1/me/` | User |
| POST | `/api/v1/me/switch-role/` | User |
| POST | `/api/v1/me/add-profile/` | User |

## Endpoints in M2 (all public, read-only)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/categories/` | With `service_count`, in display order |
| GET | `/api/v1/categories/{slug}/` | Services inlined |
| GET | `/api/v1/services/` | `?category=` `?search=` |
| GET | `/api/v1/locations/` | `?level=` `?parent=` |
| GET | `/api/v1/locations/tree/` | Whole tree, one request |

## Endpoints in M3

Public:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/providers/{id}/` | Profile with full trust breakdown |
| GET | `/api/v1/providers/{id}/availability/` | `?start=YYYY-MM-DD&days=N` |

Provider-only (requires a provider profile):

| Method | Path | Notes |
|---|---|---|
| GET/PATCH | `/api/v1/provider/profile/` | |
| POST | `/api/v1/provider/accepting-work/` | Instant on/off toggle |
| GET/POST | `/api/v1/provider/services/` | Offerings with pricing |
| PATCH/DELETE | `/api/v1/provider/services/{id}/` | |
| GET/PUT | `/api/v1/provider/service-areas/` | Thana or area level only |
| GET/PUT | `/api/v1/provider/availability/` | Weekly windows |
| POST | `/api/v1/provider/availability/exceptions/` | Leave / extra days |
| GET/POST | `/api/v1/provider/verification/` | NID, trade certificate |
| POST | `/api/v1/provider/work-photos/` | Max 10 |

Admin-only:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/admin/verifications/` | Pending queue |
| POST | `/api/v1/admin/verifications/{id}/decide/` | Approve or reject |

## Endpoints in M4

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/providers/{id}/trust/` | Public | Full six-factor breakdown |
| GET | `/api/v1/provider/trust-history/` | Provider | Own score over time |
| GET | `/api/v1/admin/trust-audit/{id}/` | Admin | Snapshots with factor inputs |
| POST | `/api/v1/admin/trust-recompute/{id}/` | Admin | Force a recompute |

## Endpoints in M5

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/providers/` | Public | Trust-ranked search |

Filters: `service` `category` `location` `min_trust` `tier` `verified_only`
`price_min` `price_max` `available_on` `ordering`.

`ordering` accepts `-trust_score` (default), `price`, or `distance`.
Malformed filter values are ignored rather than rejected, so a bad query
string degrades to a broader result set instead of a 400.

## Endpoints in M6

Customer:

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/v1/requests/` | Create and list own requests |
| GET | `/api/v1/requests/{id}/` | With provider responses |
| POST | `/api/v1/requests/{id}/withdraw/` | Close an open request |
| POST | `/api/v1/bookings/{id}/confirm/` | Confirm completion |
| POST | `/api/v1/bookings/{id}/dispute/` | Open a dispute |

Provider:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/provider/inbox/` | Eligible open requests |
| POST | `/api/v1/requests/{id}/respond/` | Accept or decline |
| POST | `/api/v1/bookings/{id}/start/` | Mark in progress |
| POST | `/api/v1/bookings/{id}/complete/` | Record final price |

Either party:

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/bookings/` | Role-scoped, `?state=` |
| GET | `/api/v1/bookings/{id}/` | With full event timeline |
| POST | `/api/v1/bookings/{id}/cancel/` | Reason required |

## Endpoints in M7

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/providers/{id}/reviews/` | Public | Published, unhidden only |
| GET/POST | `/api/v1/reviews/` | Customer | Own reviews; create one |
| PATCH | `/api/v1/reviews/{id}/` | Customer | Within 24h of posting |
| POST | `/api/v1/reviews/{id}/reply/` | Provider | One reply per review |
| GET | `/api/v1/provider/reviews/` | Provider | Reviews received |
| POST | `/api/v1/provider/rate-customer/` | Provider | The other blind half |
| POST | `/api/v1/admin/reviews/{id}/hide/` | Admin | Reason required |
| POST | `/api/v1/admin/reviews/{id}/unhide/` | Admin | |

## Endpoints in M8

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/payments/` | User | Role-scoped; customers never see commission |
| GET | `/api/v1/provider/earnings/` | Provider | `?period=day\|week\|month&start=&end=` |
| GET | `/api/v1/provider/ledger/` | Provider | `?kind=` |
| GET | `/api/v1/provider/dashboard/` | Provider | Trust, requests, bookings, earnings |
| GET | `/api/v1/admin/payments/flagged/` | Admin | Amount mismatches awaiting review |
| POST | `/api/v1/admin/payments/{id}/resolve/` | Admin | Settle at a decided amount |
| POST | `/api/v1/admin/providers/{id}/settlements/` | Admin | Provider paid what they owe |

In development the OTP is **printed to the server log** rather than sent —
there is no SMS provider yet. Look for `OTP for +8801... is 123456`.

## Layout

```
config/settings/     base.py, dev.py, prod.py, test.py (fast password hashing for tests)
apps/common/         base models, exceptions, pagination, throttling
apps/accounts/       User, profiles, OTP, JWT, roles
apps/catalogue/      ServiceCategory, Service, Location, seed data
apps/providers/      offerings, service areas, availability, verification
apps/trust/          factors.py (pure math), engine.py (DB), TrustSnapshot
apps/bookings/       ServiceRequest, Booking, BookingEvent, state_machine.py
apps/reviews/        Review, ProviderReply, CustomerRating, ReviewEdit
apps/payments/       Payment, LedgerEntry, earnings, reconciliation
apps/operations/     JobRun, the job schedule, demo seeder, benchmark

# within each app:
  models.py          persistence only, no business rules
  services.py        ALL write logic lives here
  selectors.py       read queries (kept out of views)
  serializers.py     I/O shape only
  views.py           HTTP only — delegates to services
  management/commands/
```

### The rule that matters

Business logic lives in `services.py`, never in views, serializers, or
`save()`. Three constraints keep the later move to Celery a one-line change
per call site (PRD §8.5):

1. Services take **IDs, not model instances** — a queue message must be JSON-serializable.
2. Services **never touch `request`** — no worker has one.
3. Services are **idempotent** — a retry must be harmless.

## Scheduled jobs

Phase 1 has no Celery or Redis. Recurring work runs as management commands
(PRD §8.4). The schedule is defined once, in `apps/operations/jobs.py`:

| Job | Runs | Does |
|---|---|---|
| `expire_requests` | every 15 min | closes requests unanswered past 24h |
| `auto_confirm` | hourly | confirms jobs 72h after completion |
| `reveal_reviews` | hourly | publishes reviews past the 14-day window |
| `recompute_all_trust` | 03:00 | time decay keeps scores moving |
| `reconcile_earnings` | 03:30 | fails if any ledger disagrees with its bookings |
| `purge_otps` | every 10 min | deletes expired OTP rows |
| `purge_documents` | 04:00 | deletes verification files past retention |

```bash
python manage.py run_scheduled_jobs              # run every job once, in order
python manage.py run_scheduled_jobs --only purge_otps
python manage.py crontab                         # print the production crontab
```

Every run is recorded as a `JobRun` row (start, finish, rows affected,
error). Admins can see the health of every job at
`GET /api/v1/admin/job-runs/`: a job is **overdue** if it has not succeeded
within twice its interval, and **stuck** if any run has been `running` for
longer than its interval. A cron job that silently stops is the classic way
this kind of system rots, and this is the check that catches it.

The production crontab is generated from the schedule, not typed by hand;
see [`../deploy/DEPLOY.md`](../deploy/DEPLOY.md).

## Demo data and benchmarks

```bash
python manage.py seed_demo                   # 18 providers, 6 archetypes, real bookings
python manage.py seed_demo --reset           # wipe the demo rows and start again
python manage.py seed_demo --bulk 10000      # add lightweight providers for load tests
python manage.py benchmark                   # API latency against PRD 12.1
```

Every demo account uses the password `demo-pass-2026`. The customer is
`+8801300050000`; provider #1 (`+8801300000001`) is the veteran, #2 is
Kamal and #3 is Shakib from the PRD's worked example. `seed_demo` refuses
to run when `DEBUG` is off, because it creates accounts with a published
password.

The 18-provider demo is built through the real services, not raw inserts:
every booking walks the state machine, every payment writes ledger entries,
and every review goes through the double-blind flow, so `reconcile_earnings`
passes on it. `--bulk` providers are inserted directly for speed; they have
offerings, areas and scores but no bookings.

Results with 10,018 providers, 200 requests per endpoint, `DEBUG` off:

| Measure | p95 | PRD target |
|---|---|---|
| Provider search | 100 ms (7–8 queries) | 400 ms |
| Provider detail | 42 ms | 250 ms |
| Trust breakdown | 16 ms | 250 ms |
| One trust recompute (busiest provider) | 72 ms | 2 s |
| Nightly recompute of all 10,018 | 175 s | 15 min |

## Notes for whoever picks this up

- **`.env` is gitignored** and must never be committed. `.env.example`
  documents every key.
- **Trust fields on `ProviderProfile` are read-only everywhere** — serializer,
  admin, and API. Only the trust engine (M4) writes them.
- **OTP codes are stored hashed**, salted with the phone number and
  `SECRET_KEY`. The plaintext is never persisted or returned.
- **`verify_phone_otp` is deliberately not wrapped in one atomic block.**
  A failed attempt must commit its counter increment; sharing a transaction
  with the raised error would roll the increment back and defeat the attempt
  limit entirely. There is a regression test for this.
- **`annotate()` silently discards `Meta.ordering`.** It adds a GROUP BY,
  which drops the ORDER BY entirely. `selectors.active_categories()`
  re-applies ordering explicitly; without it the landing page rendered
  categories in arbitrary order. Two regression tests cover it.
- **Verification documents are stored OUTSIDE public media.** They use
  `apps/common/storage.PrivateMediaStorage`, which writes to
  `PRIVATE_MEDIA_ROOT` and raises on `.url()`. An early version used the
  default storage, which put NID scans under `MEDIA_ROOT` where Django (in
  DEBUG) and Nginx (in production) would serve them to anyone who guessed
  the path. Four tests assert the boundary.
- **`identity_verified` requires BOTH NID sides approved.** Flags are derived
  in `_sync_verification_flags` from approved documents; they are never set
  directly, and no serializer exposes them as writable.
- **A customer's address is withheld until a provider accepts.** The provider
  inbox uses `InboxRequestSerializer`, which omits the address and keeps the
  area. Before this fix the inbox used the customer-facing serializer, so a
  broadcast request showed the customer's home address to every eligible
  provider nearby. Once a provider accepts, the booking detail reveals the
  address, name and phone to that provider only.
- **Every provider-owned endpoint scopes by `provider_id` in the query**, not
  just by object id, so one provider cannot read or mutate another's rows.
  The 404-on-foreign-object behaviour is tested per endpoint.
- **`apps/trust/factors.py` is pure math with no database access.** That is
  what lets the same code be verified against `docs/verify_trust_math.py`.
  Given the PRD section 7.4 inputs it reproduces base scores of 84.19 and
  53.48 exactly, asserted by two tests.
- **All six trust factors now run on real data.** F4 reads actual `Booking`
  rows for notice hours; F6 reads published, unhidden `Review` rows. No
  factor uses a placeholder any more.
- **Reviews are double-blind.** A review stays unpublished until the provider
  also rates the customer, or until the 14-day `reveal_deadline` passes and
  `reveal_reviews` publishes it. This is the review-extortion countermeasure
  from PRD 7.5 — neither side can condition their rating on the other's.
- **Unpublished reviews do not move trust.** `_gather_reviews` filters on
  `published_at__isnull=False`, so a score cannot shift because of a review
  nobody can see yet. There is a test asserting the score is unchanged.
- **Hidden reviews are excluded from trust and from the public list.**
  Verified live: hiding a 5-star review moved F6 from 83.3 back to the
  platform prior of 80.0.
- **The ledger is signed, append-only, and money never leaves Decimal.** A
  cash job writes `EARNING +2000`, `COMMISSION -240`, and `CASH_RETAINED
  -2000`; the balance of -240 is what the provider owes the platform. An
  online payment in Phase 2 simply omits `CASH_RETAINED`, so the same model
  covers both without a migration (FR-7.5).
- **Payments are recorded inside the booking's confirmation transaction**,
  not in `on_commit`. A completed booking and its payment either both exist
  or neither does. Trust recomputation stays in `on_commit` because it may
  fail independently without leaving money in an inconsistent state.
- **A disputed amount never enters the ledger.** When the provider-recorded
  and customer-confirmed amounts differ, the payment is flagged and no
  entries are written until an admin resolves it with a note.
- **Commission is rounded half-up to the paisa and the rate is snapshotted
  on the payment**, so changing `PLATFORM_COMMISSION_PERCENT` never rewrites
  past earnings.
- **Idempotency is enforced by the database, not just the code.** Partial
  unique constraints allow one cash payment per booking and one accrual of
  each kind per booking; a second insert raises `IntegrityError`.
- **Money leaves the API as strings.** DRF's encoder turns a raw `Decimal`
  into a float, so summaries go through `DecimalField` serializers.
- **`reconcile_earnings` catches what append-only cannot.** `save()` and
  `delete()` are blocked on ledger rows, but a queryset `.update()` bypasses
  both. The reconciler compares the ledger against payments and exits
  non-zero on any difference, so a cron job or CI step fails loudly.
- **Public reviews show an abbreviated customer name** ("Rumana A.", not the
  full name), so leaving an honest review does not expose the reviewer.
- **Every booking state change goes through `_transition`**, which validates
  against `state_machine.ALLOWED_TRANSITIONS`, writes a `BookingEvent`, and
  saves in one transaction. An illegal move raises `InvalidStateTransition`
  (HTTP 409), never a 500. A test walks all 49 state pairs and asserts the
  39 illegal ones raise.
- **`BookingEvent` is append-only** like `TrustSnapshot`, so the timeline
  shown to a customer cannot be rewritten after the fact.
- **Accepting a job lowers trust until it is completed.** Acceptance
  increments `jobs_accepted` immediately while `jobs_completed` only moves on
  confirmation, so F3 dips in between. That is intended: a provider who
  accepts and never finishes should not look good.
- **Trust score and tier are separate concepts.** Score drives ranking; tier
  communicates confidence. A provider can score 84 and still sit in "Rising"
  because the tier gate needs 10 completed jobs. Collapsing them would
  reintroduce the small-sample problem the whole design exists to avoid.
- **`TrustSnapshot` is append-only** — `AppendOnlyModel` raises on save to an
  existing row and on delete. Every score is reconstructible from its
  recorded factors and `algo_version`, which is what makes the number
  defensible when a provider disputes it.
- **Search returns a constant 2 queries regardless of result count.** The
  nested `service_areas` serializer was an N+1 — 13 queries for 4 providers,
  which would have been ~200 for a full page. A `Prefetch` on the base
  queryset fixed it, and `test_search_query_count_is_constant` asserts the
  count at two different result sizes so a regression fails loudly.
- **Verified providers outrank unverified at equal trust** (FR-4.6). Every
  ordering ends with `-identity_verified` then `pk`, so ties are broken
  deterministically and pagination cannot show the same provider twice.
- **Location matching expands both directions.** A provider serving a thana
  matches a request in any area inside it, and a provider registered to a
  specific area matches a thana-level search.
- **Locations are a three-level tree** (city > thana > area) with a centroid
  on every node. `Location.descendant_ids()` expands downward, so a provider
  serving "Dhanmondi" matches a request in "Dhanmondi 27". Proximity sorting
  uses the distance in degrees between centroids, in plain SQL. At Dhaka's
  scale that ranks the same way as great-circle distance.
- **The database needs no PostgreSQL extensions.** Early setup notes
  installed `cube`, `earthdistance` and `pg_trgm`, but nothing uses them.
  `earthdistance` can only be created by a superuser, so a dump that contains
  it cannot be restored by the app's own role. The restore drill in
  `deploy/scripts/restore-check.sh` found this.
- **Rate limits key on the real client address.** DRF reads the client IP
  from `X-Forwarded-For` only when `TRUSTED_PROXY_COUNT` says a proxy is
  there (0 in development, 1 behind Nginx). Before this, a client could send
  a fresh fake header on every request and never hit the login limit; a test
  proved the right password succeeding on the sixth attempt.
- **Uploads are checked by content, not by name.** A verification document
  must start with the magic bytes of JPEG, PNG or PDF, and they must agree
  with the extension. An HTML file renamed to `.jpg` used to be accepted.
- **Every API route is covered by an access audit.**
  `apps/common/tests/test_access_control.py` walks Django's URL table: every
  route not on the public allowlist must refuse an anonymous caller, and every
  admin route must refuse an ordinary customer. A new endpoint that forgets
  its permission class fails the suite without anyone writing a test for it.
- **Dependencies are audited.** `pip-audit` and `npm audit` run in CI; the
  M10 audit upgraded Django 5.1 to 5.2 LTS and cleared 37 known
  vulnerabilities.
