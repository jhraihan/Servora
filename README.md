# ShebaLocal

A local service marketplace connecting customers with verified electricians,
plumbers, AC technicians and other tradespeople in Dhaka.

The point of this project is not the booking flow — that is a well-understood
problem. It is the **trust model**.

## The problem with star ratings

A provider with one 5-star review outranks a provider with two hundred jobs
averaging 4.8. Ratings cluster so tightly at 4.5–5.0 that they carry almost
no information. And they only measure jobs that were *completed* — a provider
who accepts ten bookings and abandons eight can hold a perfect score.

Consider two real profiles the system produces:

| | Kamal | Shakib |
|---|---|---|
| Star rating | 4.9 | 4.8 |
| Jobs completed | 4 of 4 | 18 of 30 |
| Cancellations | 0 | 12 (3 at under 4h notice) |
| Median response | 8 min | 6 hours |
| Verification | Full (NID + trade cert) | Phone only |
| **Trust score** | **84.2** | **53.5** |

On any conventional marketplace these two look nearly identical. Shakib
abandons 40% of the jobs he accepts and takes six hours to reply — and his
review score is the *highest* of his six factors, which is exactly the signal
a star rating would show you.

## How the trust score works

Six measurable factors, each derived from recorded platform events rather
than self-report:

| Factor | Weight | Captures |
|---|---|---|
| Verification depth | 20% | Has this person proven who they are? |
| Job volume | 15% | Is there enough evidence to judge them? |
| Completion reliability | 20% | When they commit, do they finish? |
| Cancellation discipline | 15% | How often do they break a commitment? |
| Responsiveness | 10% | How long does a customer wait? |
| Review quality | 20% | What do verified customers say? |

The three techniques that make it work:

- **Bayesian smoothing** on completion rate and reviews, so low-volume
  providers regress toward the platform mean instead of scoring 100 on a
  single job.
- **Damage-weighted, time-decayed cancellations** — cancelling an hour before
  costs 4× what cancelling two days ahead costs, and old cancellations fade
  with a 180-day half-life.
- **Logarithmic volume** saturating at 100 jobs, so farming trivial jobs has
  sharply diminishing returns.

Penalties for upheld disputes apply *after* the weighted sum, so one serious
incident cannot be diluted by strong performance elsewhere.

The full algorithm — formulas, anti-gaming design, worked examples — is in
[the PRD](docs/ShebaLocal-PRD.pdf), section 7. A runnable reference
implementation lives in [`docs/verify_trust_math.py`](docs/verify_trust_math.py)
and asserts every figure printed in the document.

## Stack

Django 5 · Django REST Framework · PostgreSQL 18 · React 18 (JavaScript) · Vite

No Docker, no Celery, no Redis in Phase 1. Recurring work runs as Django
management commands under Task Scheduler / cron; [PRD §8.5](docs/ShebaLocal-PRD.pdf)
defines the thresholds that justify adopting a task queue and keeps the
migration to one line per call site.

## Status

| Milestone | State |
|---|---|
| M1 Foundation — auth, OTP, JWT, roles | Done |
| M2 Catalogue — services, locations, seed | Done |
| M3 Providers — profiles, areas, availability, verification | Done |
| M4 Trust engine — six factors, snapshots, audit trail | Done |
| M5 Discovery — search, filters, trust ranking | Done |
| M6 Booking — request lifecycle, state machine | Done |
| M7 Reviews — double-blind, trust feedback | Done |
| M8 Money — cash settlement, commission, earnings | Next |
| M9–M10 | Planned |

414 tests passing. All six trust factors now run on real platform data. The trust engine reproduces both PRD worked examples
exactly (base scores 84.19 and 53.48), and search ranks by trust rather
than by price.

## Getting started

Requires Python 3.12, PostgreSQL 16+, and Node 20+.

```bash
# database (once, as the postgres superuser)
psql -U postgres -c "CREATE DATABASE shebalocal;"
psql -U postgres -c "CREATE USER sheba WITH PASSWORD 'your-password' CREATEDB;"
psql -U postgres -d shebalocal -c "ALTER SCHEMA public OWNER TO sheba;"
psql -U postgres -d shebalocal -c "CREATE EXTENSION cube; CREATE EXTENSION earthdistance; CREATE EXTENSION pg_trgm;"

# backend
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # fill in SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py seed_catalogue
python manage.py runserver
```

Full setup notes, including the PostgreSQL 15+ schema-grant that `migrate`
requires, are in [PRD §11](docs/ShebaLocal-PRD.pdf) and
[`backend/README.md`](backend/README.md).

## Repository layout

```
docs/       PRD (PDF + the source that generates it), trust math reference
backend/    Django project — see backend/README.md
frontend/   React client (not yet started)
```

## Documentation

- [Product Requirements Document](docs/ShebaLocal-PRD.pdf) — 40 pages, the full spec
- [`backend/README.md`](backend/README.md) — running it, endpoints, design notes
- [`docs/README.md`](docs/README.md) — how the PRD is generated and verified
