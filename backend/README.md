# ShebaLocal — Backend

Django 5 + DRF + PostgreSQL 18. See [`../docs/ShebaLocal-PRD.pdf`](../docs/ShebaLocal-PRD.pdf) for the full specification.

## Status

**M3 Providers — complete.** 192 tests passing.

| Milestone | State |
|---|---|
| M1 Foundation (auth, OTP, roles) | Done |
| M2 Catalogue (services, locations, seed) | Done |
| M3 Providers (profiles, areas, availability, verification) | Done |
| M4 Trust engine | Next |

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
python -m pytest              # all 192
python -m pytest -k otp       # one area
```

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

In development the OTP is **printed to the server log** rather than sent —
there is no SMS provider yet. Look for `OTP for +8801... is 123456`.

## Layout

```
config/settings/     base.py, dev.py, prod.py
apps/common/         base models, exceptions, pagination, throttling
apps/accounts/       User, profiles, OTP, JWT, roles
apps/catalogue/      ServiceCategory, Service, Location, seed data
apps/providers/      offerings, service areas, availability, verification

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
(PRD §8.4):

```bash
python manage.py purge_otps          # expired OTP rows
python manage.py purge_documents     # verification files past retention
python manage.py seed_catalogue      # idempotent; safe to re-run
```

Register with Task Scheduler locally, cron in production — see PRD §11.3
and §11.5.

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
- **Every provider-owned endpoint scopes by `provider_id` in the query**, not
  just by object id, so one provider cannot read or mutate another's rows.
  The 404-on-foreign-object behaviour is tested per endpoint.
- **Locations are a three-level tree** (city > thana > area) with a centroid
  on every node. `Location.descendant_ids()` expands downward, so a provider
  serving "Dhanmondi" matches a request in "Dhanmondi 27". Proximity sorting
  uses the `<@>` earthdistance operator — verified working against the seed
  data.
