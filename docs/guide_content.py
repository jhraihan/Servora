# -*- coding: utf-8 -*-
"""
Content source for the ServoraBd Engineering & Interview Guide.

Same (kind, payload) format as prd_content.py, rendered by build_guide.py.

Kinds:
    h1, h2, h3   -- headings
    p            -- paragraph (supports <b>/<i>/<font> inline markup)
    bullets      -- list of strings
    numbers      -- ordered list of strings
    table        -- {"cols": [...], "widths": [...], "rows": [[...]]}
    code         -- monospace block (list of lines)
    callout      -- {"title": str, "body": str}
    pagebreak    -- None
    spacer       -- height in points
"""

TITLE = "ServoraBd"
SUBTITLE = "Local Service Marketplace"
DOC_TYPE = "Engineering & Interview Guide"
VERSION = "1.0"
STATUS = "Complete through M10"
DATE = "29 September 2026"
AUTHOR = "Jahid H. R."

PITCH = (
    "A complete walkthrough of the system &mdash; how to run it, how every "
    "layer works, why each decision was made, and how to defend all of it "
    "in a technical interview."
)

DOC = []


def add(*items):
    DOC.extend(items)


# ======================================================================
# PART I -- ORIENTATION
# ======================================================================

add(
    ("h1", "1. How to read this guide"),

    ("p", "This document explains the ServoraBd codebase from the outside in. "
          "It is written for one reader: the person who built it and now has to "
          "explain it under questioning. Everything here is traceable to a real "
          "file in the repository, and file paths are given so you can open the "
          "code alongside the prose."),

    ("h2", "1.1 The three questions this guide answers"),

    ("table", {
        "cols": ["Question", "Where it is answered"],
        "widths": [0.42, 0.58],
        "rows": [
            ["How do I get it running on a fresh machine?",
             "Section 3. Setup, database, seeding, both servers."],
            ["How does the code actually work, end to end?",
             "Sections 4&ndash;12. Architecture, each backend app, the trust "
             "engine, the frontend, security, operations."],
            ["How do I defend it in an interview?",
             "Sections 13&ndash;16. Question bank with model answers, the "
             "weaknesses an interviewer will find, and a 90-second pitch."],
        ],
    }),

    ("h2", "1.2 What the project is, in one paragraph"),

    ("p", "ServoraBd is a two-sided marketplace for home services &mdash; "
          "electricians, plumbers, AC technicians &mdash; in Dhaka. A customer "
          "posts a request; providers in that area who offer that service see "
          "it and can accept; accepting creates a booking that moves through a "
          "state machine to completion, payment and a double-blind review. The "
          "distinguishing feature is not the booking flow, which is a solved "
          "problem. It is the <b>trust score</b>: a six-factor, statistically "
          "smoothed, time-decayed measure of a provider's reliability, "
          "computed from recorded platform events rather than self-report, and "
          "shown to customers broken down factor by factor."),

    ("callout", {
        "title": "The one thing to lead with",
        "body": "Star ratings are broken. A provider with one 5-star review "
                "outranks one with two hundred jobs at 4.8, and ratings only "
                "measure jobs that were <i>completed</i> &mdash; a provider who "
                "accepts ten bookings and abandons eight can hold a perfect "
                "score. ServoraBd measures what star ratings cannot: whether "
                "the person finishes what they start.",
    }),

    ("h2", "1.3 The headline numbers"),

    ("table", {
        "cols": ["Measure", "Value"],
        "widths": [0.55, 0.45],
        "rows": [
            ["Backend tests", "569, passing"],
            ["Frontend tests", "47 unit and component, plus Playwright E2E"],
            ["Django apps", "9 (common, operations, accounts, catalogue, "
                            "providers, trust, bookings, reviews, payments)"],
            ["API endpoints", "60+ under <font face='Courier'>/api/v1/</font>"],
            ["Provider search p95, 10,018 providers", "100 ms (target 400 ms)"],
            ["Nightly trust recompute, 10,018 providers",
             "175 s (target 15 min)"],
            ["Landing page LCP, Slow 4G, 4&times; CPU throttle",
             "1.58 s (target 2.5 s)"],
            ["Accessibility", "axe-core: zero WCAG 2.1 AA violations"],
            ["Known vulnerabilities", "0 (pip-audit, npm audit, in CI)"],
        ],
    }),

    ("pagebreak", None),

    # ------------------------------------------------------------------
    ("h1", "2. The domain in plain language"),

    ("p", "Before any code, understand the nouns. Almost every interview "
          "question resolves to one of these eight concepts, and being fluent "
          "in them makes every later answer shorter."),

    ("h2", "2.1 The actors"),

    ("table", {
        "cols": ["Actor", "What they do", "How the code models them"],
        "widths": [0.17, 0.44, 0.39],
        "rows": [
            ["Customer", "Posts service requests, confirms completion, pays "
                         "cash, writes reviews.",
             "<font face='Courier'>CustomerProfile</font>, one-to-one with "
             "<font face='Courier'>User</font>."],
            ["Provider", "Lists services and prices, picks service areas and "
                         "hours, accepts requests, does the job, gets a trust "
                         "score.",
             "<font face='Courier'>ProviderProfile</font>, one-to-one with "
             "<font face='Courier'>User</font>."],
            ["Admin", "Reviews verification documents, resolves flagged "
                      "payments, hides abusive reviews, watches scheduled "
                      "jobs.",
             "<font face='Courier'>User.is_staff</font>; Django admin plus "
             "admin API routes."],
            ["System", "Expires unanswered requests, auto-confirms stale "
                       "jobs, reveals reviews, recomputes trust nightly.",
             "Management commands run by cron; actor recorded as "
             "<font face='Courier'>system</font> in the event log."],
        ],
    }),

    ("h2", "2.2 The core objects"),

    ("bullets", [
        "<b>Service</b> &mdash; a thing that can be bought, e.g. &lsquo;Ceiling "
        "fan installation&rsquo;. Belongs to a <b>ServiceCategory</b>. Carries "
        "a suggested price band so the UI can flag a quote as low, normal or "
        "high.",

        "<b>Location</b> &mdash; a three-level self-referential tree: city "
        "&rarr; thana &rarr; area. A provider's coverage is stored at thana or "
        "area level; a search on a thana matches providers registered in any of "
        "its areas, and vice versa.",

        "<b>ServiceRequest</b> &mdash; a customer asking for work. Either "
        "<i>broadcast</i> (every eligible provider in the area sees it) or "
        "<i>direct</i> (aimed at one provider). Expires unanswered after 24 "
        "hours.",

        "<b>Booking</b> &mdash; created the moment a provider accepts a "
        "request. Holds the agreed price and moves through a seven-state "
        "machine. Every transition is written to an append-only "
        "<b>BookingEvent</b> log.",

        "<b>Payment</b> and <b>LedgerEntry</b> &mdash; cash settlement. Both "
        "sides record the amount; if they disagree the payment is flagged for "
        "an admin instead of being silently trusted.",

        "<b>Review</b> &mdash; double-blind. Neither side sees the other's "
        "words until both have submitted, or 14 days pass.",

        "<b>TrustSnapshot</b> &mdash; an append-only record of a provider's "
        "score every time it was recomputed, including the full factor "
        "breakdown and which event triggered it. This is the audit trail.",
    ]),

    ("h2", "2.3 The happy path, end to end"),

    ("numbers", [
        "A customer registers with a Bangladeshi phone number and receives a "
        "six-digit OTP.",
        "They browse services, search providers, and compare up to three side "
        "by side on trust rather than price.",
        "They post a request through a six-step wizard: service, where, "
        "problem, when, who, confirm.",
        "Every provider who offers that service, covers that area, is "
        "accepting work and is not under review has "
        "<font face='Courier'>requests_received</font> incremented &mdash; the "
        "denominator of the responsiveness factor.",
        "A provider accepts. The request closes, a booking is created at the "
        "agreed price, and the provider's "
        "<font face='Courier'>jobs_accepted</font> goes up.",
        "The provider starts the job, then completes it with a final price.",
        "The customer confirms. That single call increments "
        "<font face='Courier'>jobs_completed</font>, records the payment, "
        "writes three ledger entries, and queues a trust recompute.",
        "Both sides review each other. When the second one lands, both are "
        "published at once and trust is recomputed again.",
    ]),

    ("callout", {
        "title": "Why the counters matter",
        "body": "<font face='Courier'>requests_received</font>, "
                "<font face='Courier'>jobs_accepted</font>, "
                "<font face='Courier'>jobs_completed</font> and "
                "<font face='Courier'>jobs_cancelled</font> on "
                "<font face='Courier'>ProviderProfile</font> are denormalised "
                "counters maintained with atomic "
                "<font face='Courier'>F()</font> expressions. They are the raw "
                "inputs to the trust engine, which is why trust can be "
                "recomputed for ten thousand providers in under three minutes "
                "rather than by walking every booking.",
    }),

    ("pagebreak", None),
)


# ======================================================================
# PART II -- RUNNING IT
# ======================================================================

add(
    ("h1", "3. Setting up and running the project"),

    ("h2", "3.1 What you need installed"),

    ("table", {
        "cols": ["Tool", "Version", "Why"],
        "widths": [0.22, 0.2, 0.58],
        "rows": [
            ["Python", "3.12", "Django 5.2 LTS targets it; CI pins it."],
            ["PostgreSQL", "16 or newer",
             "No extensions needed. CI runs 18. Check constraints and "
             "partial unique indexes are used, so SQLite is not a substitute."],
            ["Node", "20 or newer",
             "Vite 6 and the React toolchain. CI runs 24."],
            ["Git", "any", "Cloning; the repo uses "
                            "<font face='Courier'>.gitattributes</font> for "
                            "line endings."],
        ],
    }),

    ("h2", "3.2 Database first"),

    ("p", "Run these once as the postgres superuser. The third line is the one "
          "people miss: since PostgreSQL 15 a non-owner role cannot create "
          "tables in the <font face='Courier'>public</font> schema, so "
          "<font face='Courier'>migrate</font> fails with a permission error "
          "without it."),

    ("code", [
        'psql -U postgres -c "CREATE DATABASE servorabd;"',
        'psql -U postgres -c "CREATE USER sheba WITH PASSWORD \'your-password\' CREATEDB;"',
        'psql -U postgres -d servorabd -c "ALTER SCHEMA public OWNER TO sheba;"',
    ]),

    ("p", "The <font face='Courier'>CREATEDB</font> privilege is not optional. "
          "pytest creates and drops a <font face='Courier'>test_servorabd</font> "
          "database on every run; without it the whole suite refuses to start."),

    ("h2", "3.3 Backend"),

    ("code", [
        "cd backend",
        "python -m venv venv",
        "venv\\Scripts\\activate            # macOS/Linux: source venv/bin/activate",
        "pip install -r requirements.txt",
        "copy .env.example .env             # then edit it",
        "python manage.py migrate",
        "python manage.py seed_catalogue    # 8 categories, 45 services, 38 locations",
        "python manage.py seed_demo         # optional: 18 providers with real history",
        "python manage.py createsuperuser",
        "python manage.py runserver",
    ]),

    ("p", "The API is then at <font face='Courier'>http://127.0.0.1:8000/api/v1/</font> "
          "and Django admin at <font face='Courier'>/admin/</font>."),

    ("h3", "What goes in .env"),

    ("table", {
        "cols": ["Variable", "Meaning"],
        "widths": [0.33, 0.67],
        "rows": [
            ["<font face='Courier'>SECRET_KEY</font>",
             "Required, no default. Also salts the OTP hash, so changing it "
             "invalidates every outstanding code."],
            ["<font face='Courier'>DATABASE_URL</font>",
             "e.g. <font face='Courier'>postgres://sheba:pw@localhost:5432/servorabd</font>"],
            ["<font face='Courier'>DEBUG</font>",
             "Defaults to False. The dev settings module forces it True."],
            ["<font face='Courier'>OTP_TTL_SECONDS</font>", "Default 300 (five minutes)."],
            ["<font face='Courier'>OTP_MAX_SENDS_PER_HOUR</font>", "Default 3 per phone number."],
            ["<font face='Courier'>OTP_MAX_VERIFY_ATTEMPTS</font>", "Default 5 per code."],
            ["<font face='Courier'>JWT_ACCESS_MINUTES</font>", "Default 15."],
            ["<font face='Courier'>JWT_REFRESH_DAYS</font>", "Default 14."],
            ["<font face='Courier'>PLATFORM_COMMISSION_PERCENT</font>", "Default 12."],
            ["<font face='Courier'>TRUSTED_PROXY_COUNT</font>",
             "Default 0. Critical security setting &mdash; see section 11.2."],
            ["<font face='Courier'>USE_OBJECT_STORAGE</font>",
             "Production only. Switches file storage to S3-compatible object storage."],
        ],
    }),

    ("h2", "3.4 Frontend"),

    ("p", "In a second terminal, with the backend already running:"),

    ("code", [
        "cd frontend",
        "npm install",
        "npm run dev                        # http://127.0.0.1:5173",
    ]),

    ("p", "Vite proxies <font face='Courier'>/api</font> and "
          "<font face='Courier'>/media</font> to "
          "<font face='Courier'>http://127.0.0.1:8000</font>, so the browser "
          "sees a single origin and there is no CORS configuration to get "
          "wrong in development. Point it elsewhere with "
          "<font face='Courier'>BACKEND_URL=http://127.0.0.1:8100 npm run dev</font>."),

    ("h2", "3.5 Logging in during development"),

    ("callout", {
        "title": "Where is the OTP?",
        "body": "There is no SMS provider wired up. In development "
                "<font face='Courier'>OTP_ECHO_TO_LOG</font> is True, so the "
                "code is printed to the runserver console: look for "
                "<font face='Courier'>OTP for +8801... is 123456</font>. "
                "In production that flag is False and the log records only "
                "that a code was issued &mdash; never the code itself.",
    }),

    ("h2", "3.6 Every command you might need"),

    ("table", {
        "cols": ["Command", "What it does"],
        "widths": [0.4, 0.6],
        "rows": [
            ["<font face='Courier'>python -m pytest</font>",
             "All 569 backend tests, about two minutes."],
            ["<font face='Courier'>python -m pytest -k otp</font>",
             "One area by keyword."],
            ["<font face='Courier'>python manage.py seed_catalogue</font>",
             "Idempotent: categories, services, the Dhaka location tree."],
            ["<font face='Courier'>python manage.py seed_demo</font>",
             "18 providers across archetypes, with bookings, reviews and "
             "cancellations, so the trust engine has real data to chew on."],
            ["<font face='Courier'>python manage.py benchmark</font>",
             "Times search, provider detail, trust breakdown and the nightly "
             "recompute against the PRD targets."],
            ["<font face='Courier'>python manage.py run_scheduled_jobs</font>",
             "Runs every due scheduled job once &mdash; the local stand-in for cron."],
            ["<font face='Courier'>python manage.py crontab</font>",
             "Prints the crontab lines to install on a server."],
            ["<font face='Courier'>python manage.py check_proxy_count &lt;url&gt;</font>",
             "Probes a live deployment for the forged-header rate-limit bypass "
             "(section 11.2)."],
            ["<font face='Courier'>npm run lint</font>", "ESLint, zero warnings allowed."],
            ["<font face='Courier'>npm test</font>", "Vitest unit and component tests."],
            ["<font face='Courier'>npm run e2e</font>",
             "Playwright: both golden paths and the accessibility scan, "
             "Chromium at 360 px."],
            ["<font face='Courier'>npm run perf:lcp</font>",
             "Production build, then LCP under Slow 4G and Fast 4G throttling."],
        ],
    }),

    ("h3", "Why the test settings module exists"),

    ("p", "<font face='Courier'>config/settings/test.py</font> swaps in a fast "
          "password hasher. Production-strength PBKDF2 costs about a second per "
          "hash, and with a user or two created per test that alone took the "
          "suite from two minutes to fourteen. This is a standard Django "
          "technique and a good thing to mention unprompted &mdash; it shows you "
          "profiled your own test suite."),

    ("pagebreak", None),
)


# ======================================================================
# PART III -- ARCHITECTURE
# ======================================================================

add(
    ("h1", "4. Architecture and code structure"),

    ("h2", "4.1 The shape of the repository"),

    ("code", [
        "Local-Service/",
        "|-- backend/            Django project",
        "|   |-- config/",
        "|   |   |-- settings/   base.py, dev.py, prod.py, test.py",
        "|   |   |-- urls.py     mounts every app under /api/v1/",
        "|   |   +-- wsgi.py, asgi.py",
        "|   |-- apps/",
        "|   |   |-- common/     base models, exceptions, pagination, throttling, storage",
        "|   |   |-- operations/ scheduled-job registry and run log",
        "|   |   |-- accounts/   User, profiles, OTP, JWT, roles",
        "|   |   |-- catalogue/  categories, services, location tree",
        "|   |   |-- providers/  offerings, areas, availability, verification, search",
        "|   |   |-- trust/      the six-factor engine and snapshots",
        "|   |   |-- bookings/   requests, responses, bookings, state machine",
        "|   |   |-- reviews/    double-blind reviews and replies",
        "|   |   +-- payments/   cash settlement, commission, ledger",
        "|   +-- manage.py, requirements.txt, conftest.py",
        "|-- frontend/           React 18 + Vite client",
        "|-- docs/               PRD (PDF + generator), trust math reference",
        "|-- deploy/             Nginx, gunicorn, systemd, backup scripts, guides",
        "|-- render.yaml         Render blueprint",
        "+-- .github/workflows/  CI",
    ]),

    ("h2", "4.2 The layered pattern every app follows"),

    ("p", "This is the single most important structural fact about the backend, "
          "and the thing that will most impress an interviewer. Every app is "
          "split the same way, and each layer has exactly one job."),

    ("table", {
        "cols": ["File", "Responsibility", "Rule"],
        "widths": [0.2, 0.42, 0.38],
        "rows": [
            ["<font face='Courier'>models.py</font>",
             "Database shape, constraints, indexes, and small derived "
             "properties.",
             "No business logic that spans more than one object."],
            ["<font face='Courier'>selectors.py</font>",
             "Read queries. Everything the API needs to <i>show</i>.",
             "Never writes. Owns the "
             "<font face='Courier'>select_related</font> / "
             "<font face='Courier'>prefetch_related</font> that kills N+1."],
            ["<font face='Courier'>services.py</font>",
             "Write operations and business rules. The only place state "
             "changes.",
             "Three hard rules &mdash; see below."],
            ["<font face='Courier'>serializers.py</font>",
             "Input validation and output shaping.",
             "Validation of <i>format</i>; services own validation of "
             "<i>meaning</i>."],
            ["<font face='Courier'>views.py</font>",
             "HTTP: parse the request, check permission, call one service, "
             "return a response.",
             "Thin. A view that contains an <font face='Courier'>if</font> "
             "about business rules is a bug."],
            ["<font face='Courier'>permissions.py</font>",
             "Who may call this at all.",
             "Role checks, not object checks."],
        ],
    }),

    ("h3", "The three service-layer rules"),

    ("p", "These come from PRD &sect;8.5 and are load-bearing. They exist so "
          "that moving any service call onto a task queue later is a one-line "
          "change at the call site rather than a rewrite."),

    ("numbers", [
        "<b>Services take IDs, not model instances.</b> A queue message has to "
        "be JSON-serialisable; a Django model instance is not. Every service "
        "signature in the codebase is "
        "<font face='Courier'>def thing(*, booking_id, provider_id, ...)</font>.",

        "<b>Services never touch <font face='Courier'>request</font>.</b> A "
        "background worker does not have one. The view extracts "
        "<font face='Courier'>request.user.id</font> and passes it down; the "
        "service never reaches up.",

        "<b>Services are idempotent.</b> A retried job or a double-fired cron "
        "must be harmless. <font face='Courier'>record_completion_payment</font> "
        "returns the existing payment if one is already there rather than "
        "creating a second.",
    ]),

    ("callout", {
        "title": "Interview gold",
        "body": "Being able to say &lsquo;every service takes IDs rather than "
                "instances so that adopting Celery later is one line per call "
                "site, and here is the PRD section that defines the load "
                "thresholds that would justify it&rsquo; demonstrates "
                "architectural thinking, not just Django familiarity. It also "
                "pre-empts the obvious question, &lsquo;why no Celery?&rsquo;",
    }),

    ("h2", "4.3 Keyword-only arguments everywhere"),

    ("p", "Every service function uses the bare "
          "<font face='Courier'>*</font> marker, forcing callers to name every "
          "argument. The reason is concrete: "
          "<font face='Courier'>cancel_booking(booking_id, customer_id, provider_id)</font> "
          "has three integer parameters, and getting them in the wrong order "
          "would silently cancel the wrong person's job. Naming them makes that "
          "class of bug impossible."),

    ("h2", "4.4 The two abstract base models"),

    ("p", "In <font face='Courier'>apps/common/models.py</font>:"),

    ("bullets", [
        "<b>TimeStampedModel</b> &mdash; gives every table "
        "<font face='Courier'>created_at</font> (indexed) and "
        "<font face='Courier'>updated_at</font>.",

        "<b>AppendOnlyModel</b> &mdash; overrides "
        "<font face='Courier'>save()</font> to raise if "
        "<font face='Courier'>self.pk</font> is already set, and "
        "<font face='Courier'>delete()</font> to always raise. Used by "
        "<font face='Courier'>BookingEvent</font>, "
        "<font face='Courier'>TrustSnapshot</font>, "
        "<font face='Courier'>LedgerEntry</font> and "
        "<font face='Courier'>ReviewEdit</font>.",
    ]),

    ("p", "The append-only base is the audit story in four lines of code. When "
          "an interviewer asks how you would prove a provider's score was not "
          "quietly edited, the answer is that the model physically refuses the "
          "write &mdash; it is not a convention anyone has to remember."),

    ("h2", "4.5 The error envelope"),

    ("p", "Every error the API returns, from a validation failure to an "
          "unhandled exception, comes back in one shape. This is enforced by a "
          "custom DRF exception handler in "
          "<font face='Courier'>apps/common/exceptions.py</font>, registered "
          "once in settings."),

    ("code", [
        "{",
        '  "error": {',
        '    "code": "invalid_state_transition",',
        '    "message": "A booking in state \'completed\' cannot move to \'in_progress\'.",',
        '    "details": {"from_state": "completed", "to_state": "in_progress"}',
        "  }",
        "}",
    ]),

    ("p", "The domain exceptions form a small hierarchy, each carrying its own "
          "HTTP status, so a service can raise a meaning and the HTTP layer "
          "translates it without a single "
          "<font face='Courier'>try/except</font> in any view:"),

    ("table", {
        "cols": ["Exception", "Status", "Used for"],
        "widths": [0.32, 0.14, 0.54],
        "rows": [
            ["<font face='Courier'>DomainError</font>", "400",
             "Base class. A business rule said no."],
            ["<font face='Courier'>InvalidStateTransition</font>", "409",
             "The state machine refused. 409 Conflict, not 400, because the "
             "request was well-formed &mdash; the resource was simply in the "
             "wrong state."],
            ["<font face='Courier'>RateLimited</font>", "429",
             "OTP send or verify budget exhausted."],
            ["<font face='Courier'>VerificationError</font>", "400",
             "Wrong, expired or missing OTP."],
            ["<font face='Courier'>NotFound</font>", "404", "No such object."],
        ],
    }),

    ("p", "The handler also catches the case DRF returns "
          "<font face='Courier'>None</font> for &mdash; a genuinely unhandled "
          "exception &mdash; logs it with a stack trace, and returns a generic "
          "500 envelope. The client never sees an internal error message, and "
          "the frontend never has to parse two different error formats."),

    ("pagebreak", None),
)


# ======================================================================
# PART IV -- THE BACKEND, APP BY APP
# ======================================================================

add(
    ("h1", "5. Accounts: identity, OTP and JWT"),

    ("p", "<font face='Courier'>backend/apps/accounts/</font>. This app owns "
          "the custom user model, phone verification, login, and the dual-role "
          "system. It is the app most likely to be probed in an interview "
          "because authentication is where security bugs live."),

    ("h2", "5.1 The custom User model"),

    ("p", "<font face='Courier'>User</font> extends "
          "<font face='Courier'>AbstractBaseUser</font> and "
          "<font face='Courier'>PermissionsMixin</font>. There is no "
          "<font face='Courier'>username</font>; "
          "<font face='Courier'>USERNAME_FIELD</font> is "
          "<font face='Courier'>phone</font>. Both "
          "<font face='Courier'>phone</font> and "
          "<font face='Courier'>email</font> are nullable and unique, with a "
          "database-level check constraint guaranteeing at least one is "
          "present:"),

    ("code", [
        "models.CheckConstraint(",
        "    condition=models.Q(phone__isnull=False)",
        "    | models.Q(email__isnull=False),",
        '    name="user_has_phone_or_email",',
        ")",
    ]),

    ("p", "That constraint is the answer to &lsquo;what stops a user row with "
          "neither identifier?&rsquo; &mdash; the database does, not the "
          "application. Serializer validation can be bypassed by a management "
          "command or a shell session; a check constraint cannot."),

    ("h2", "5.2 Phone normalisation"),

    ("p", "Bangladeshi numbers get typed six different ways. "
          "<font face='Courier'>normalise_bd_phone()</font> in "
          "<font face='Courier'>validators.py</font> funnels them all into one "
          "canonical form before anything touches the database."),

    ("table", {
        "cols": ["User types", "Stored as"],
        "widths": [0.5, 0.5],
        "rows": [
            ["<font face='Courier'>01712345678</font>", "<font face='Courier'>+8801712345678</font>"],
            ["<font face='Courier'>8801712345678</font>", "<font face='Courier'>+8801712345678</font>"],
            ["<font face='Courier'>+880 1712-345678</font>", "<font face='Courier'>+8801712345678</font>"],
            ["<font face='Courier'>1712345678</font>", "<font face='Courier'>+8801712345678</font>"],
        ],
    }),

    ("p", "The regex <font face='Courier'>^\\+8801[3-9]\\d{8}$</font> then "
          "validates the result. The <font face='Courier'>[3-9]</font> is not "
          "arbitrary: Bangladeshi mobile prefixes run 013 to 019, so 010 to 012 "
          "are rejected as impossible numbers rather than accepted and later "
          "found undeliverable."),

    ("p", "Normalisation happens in three places, deliberately: in the "
          "serializer's <font face='Courier'>PhoneField</font>, in "
          "<font face='Courier'>User.clean()</font>, and in "
          "<font face='Courier'>UserManager._create_user()</font>. Belt and "
          "braces &mdash; a user created from a management command is "
          "normalised the same way as one created through the API, so the "
          "uniqueness constraint actually means something."),

    ("h2", "5.3 How OTP works"),

    ("p", "The <font face='Courier'>PhoneOTP</font> model never stores a code. "
          "It stores a SHA-256 hash of "
          "<font face='Courier'>phone:code:SECRET_KEY</font>."),

    ("code", [
        "@staticmethod",
        "def hash_code(phone, code):",
        "    payload = f'{phone}:{code}:{settings.SECRET_KEY}'.encode()",
        "    return hashlib.sha256(payload).hexdigest()",
        "",
        "def matches(self, code):",
        "    return secrets.compare_digest(",
        "        self.code_hash, self.hash_code(self.phone, code)",
        "    )",
    ]),

    ("p", "Three details worth knowing by heart:"),

    ("numbers", [
        "<b>The phone number is inside the hash.</b> Without it, a code issued "
        "for one number would verify against another &mdash; the hash would be "
        "identical.",

        "<b><font face='Courier'>SECRET_KEY</font> acts as a pepper.</b> An "
        "attacker with a dump of the OTP table cannot brute-force a million "
        "six-digit codes offline without also having the application secret.",

        "<b><font face='Courier'>secrets.compare_digest</font>, not "
        "<font face='Courier'>==</font>.</b> Constant-time comparison. A normal "
        "string compare short-circuits on the first differing byte, which leaks "
        "how much of the value was correct through response timing.",
    ]),

    ("p", "Codes are generated with "
          "<font face='Courier'>secrets.randbelow(1_000_000)</font> &mdash; the "
          "cryptographically secure generator, not "
          "<font face='Courier'>random</font>, whose Mersenne Twister state can "
          "be reconstructed from a handful of outputs."),

    ("h3", "The three rate limits on OTP"),

    ("table", {
        "cols": ["Limit", "Default", "Enforced where"],
        "widths": [0.34, 0.16, 0.5],
        "rows": [
            ["Sends per phone per hour", "3",
             "<font face='Courier'>send_phone_otp</font> counts rows in the "
             "last hour &mdash; per <i>phone number</i>, so rotating IPs does "
             "not help."],
            ["Verify attempts per code", "5",
             "An <font face='Courier'>attempts</font> counter on the row, "
             "incremented inside "
             "<font face='Courier'>select_for_update</font>."],
            ["Requests per IP per hour", "10 send / 30 verify",
             "DRF <font face='Courier'>ScopedRateThrottle</font> at the view."],
        ],
    }),

    ("p", "Two independent axes. The per-phone limit stops one attacker "
          "hammering one victim's number from many addresses; the per-IP limit "
          "stops one machine spraying many numbers. Either alone leaves a hole."),

    ("h3", "The locking subtlety in verify"),

    ("p", "<font face='Courier'>verify_phone_otp</font> uses two separate "
          "transactions on purpose. The first takes "
          "<font face='Courier'>select_for_update</font> on the OTP row, checks "
          "it, and on a mismatch increments "
          "<font face='Courier'>attempts</font> and <i>commits</i>. Only then "
          "is the exception raised, outside the transaction. If the increment "
          "and the raise shared one atomic block, the rollback would undo the "
          "increment &mdash; and the attempt counter would never move, giving "
          "an attacker unlimited guesses. This is a genuinely subtle bug and "
          "worth pointing to."),

    ("p", "Sending a new code also consumes every outstanding unconsumed code "
          "for that phone and purpose, so a user cannot accumulate valid codes "
          "by pressing &lsquo;resend&rsquo; repeatedly."),

    ("h2", "5.4 JWT authentication"),

    ("p", "SimpleJWT, configured in "
          "<font face='Courier'>config/settings/base.py</font>:"),

    ("table", {
        "cols": ["Setting", "Value", "Reason"],
        "widths": [0.3, 0.16, 0.54],
        "rows": [
            ["<font face='Courier'>ACCESS_TOKEN_LIFETIME</font>", "15 min",
             "Short enough that a leaked token expires before it is much use."],
            ["<font face='Courier'>REFRESH_TOKEN_LIFETIME</font>", "14 days",
             "Long enough that a customer who books once a month is not logged out."],
            ["<font face='Courier'>ROTATE_REFRESH_TOKENS</font>", "True",
             "Every refresh issues a new refresh token."],
            ["<font face='Courier'>BLACKLIST_AFTER_ROTATION</font>", "True",
             "The old one is immediately invalid. Together with rotation this "
             "gives refresh-token reuse detection: a stolen token works once, "
             "and the moment either party uses the old one it fails."],
        ],
    }),

    ("p", "The token payload is customised in "
          "<font face='Courier'>ServoraTokenObtainPairSerializer</font> to carry "
          "<font face='Courier'>roles</font>, "
          "<font face='Courier'>active_role</font> and "
          "<font face='Courier'>phone_verified</font>. This lets the frontend "
          "render the right navigation immediately without a second round trip. "
          "It is presentation only &mdash; every permission check on the server "
          "reads the database, never the claim."),

    ("callout", {
        "title": "A question you should expect",
        "body": "&lsquo;You put roles in the JWT. What if someone edits "
                "them?&rsquo; The token is signed with "
                "<font face='Courier'>SECRET_KEY</font>, so editing it breaks "
                "the signature. But the real answer is that it would not matter "
                "if they could: <font face='Courier'>IsProvider</font> checks "
                "<font face='Courier'>hasattr(user, 'provider_profile')</font> "
                "against the database on every single request. The claim is a "
                "UI hint, not an authorisation source.",
    }),

    ("h2", "5.5 The dual-role system"),

    ("p", "One human can be both a customer and a provider &mdash; an "
          "electrician still needs a plumber. Rather than duplicating accounts, "
          "one <font face='Courier'>User</font> can hold both profiles."),

    ("bullets", [
        "<font face='Courier'>User.roles</font> is a computed property, derived "
        "from which profile objects exist plus "
        "<font face='Courier'>is_staff</font>. There is no roles column to drift "
        "out of sync.",

        "<font face='Courier'>active_role</font> is the UI mode the user is "
        "currently in. Switching it via "
        "<font face='Courier'>POST /me/switch-role/</font> is refused unless "
        "they actually hold that profile.",

        "Permission classes never consult "
        "<font face='Courier'>active_role</font>. "
        "<font face='Courier'>IsProvider</font> asks whether a "
        "<font face='Courier'>provider_profile</font> exists. A customer "
        "&lsquo;mode&rsquo; does not remove a provider's access to provider "
        "endpoints &mdash; it only changes what the interface offers.",
    ]),

    ("h2", "5.6 The custom authentication backend"),

    ("p", "<font face='Courier'>PhoneOrEmailBackend</font> lets a user log in "
          "with either identifier: if the string contains "
          "<font face='Courier'>@</font> it is looked up as an email, otherwise "
          "normalised as a phone number. One line in it matters "
          "disproportionately:"),

    ("code", [
        "except User.DoesNotExist:",
        "    User().set_password(password)",
        "    return None",
    ]),

    ("p", "When the user does not exist, it hashes the password anyway and "
          "throws the result away. Without this, a login for a non-existent "
          "user returns in microseconds while one for a real user takes the "
          "full PBKDF2 cost &mdash; a timing oracle that lets an attacker "
          "enumerate which phone numbers are registered. This is the standard "
          "mitigation and Django's own backend does the same thing."),

    ("h2", "5.7 The login throttle"),

    ("p", "<font face='Courier'>LoginRateThrottle</font> in "
          "<font face='Courier'>apps/common/throttling.py</font> allows five "
          "attempts per 15 minutes per client. It exists as a custom class "
          "because DRF's rate string grammar only understands "
          "<font face='Courier'>second</font>, "
          "<font face='Courier'>minute</font>, "
          "<font face='Courier'>hour</font> and "
          "<font face='Courier'>day</font> &mdash; there is no way to express "
          "&lsquo;5 per 15 minutes&rsquo;, so "
          "<font face='Courier'>parse_rate</font> is overridden to return the "
          "pair directly."),

    ("pagebreak", None),

    # ------------------------------------------------------------------
    ("h1", "6. Catalogue: services and the location tree"),

    ("p", "<font face='Courier'>backend/apps/catalogue/</font>. Entirely "
          "public, entirely read-only through the API. Content is managed in "
          "Django admin and seeded by "
          "<font face='Courier'>seed_catalogue</font>."),

    ("h2", "6.1 Categories and services"),

    ("p", "<font face='Courier'>ServiceCategory</font> &rarr; "
          "<font face='Courier'>Service</font>, with slugs auto-generated on "
          "save. Slug uniqueness is scoped to the category, not global, so "
          "&lsquo;Installation&rsquo; can exist under both Electrical and "
          "Plumbing."),

    ("p", "Each service carries "
          "<font face='Courier'>suggested_price_min</font> and "
          "<font face='Courier'>suggested_price_max</font>, guarded by a check "
          "constraint that max is not below min. The "
          "<font face='Courier'>price_flag()</font> method turns a provider's "
          "quote into <font face='Courier'>low</font>, "
          "<font face='Courier'>normal</font> or "
          "<font face='Courier'>high</font>, which the UI renders as a badge. "
          "That is a small feature with a real purpose: it gives the customer "
          "price context without the platform setting prices."),

    ("h2", "6.2 The location tree"),

    ("p", "<font face='Courier'>Location</font> is a self-referential model "
          "with three levels: city, thana, area. Two methods carry the weight:"),

    ("bullets", [
        "<font face='Courier'>ancestors()</font> &mdash; walks up via "
        "<font face='Courier'>parent</font>, returning the chain root-first.",

        "<font face='Courier'>descendant_ids()</font> &mdash; walks down "
        "breadth-first, collecting every id beneath a node.",
    ]),

    ("p", "Together they implement the matching rule that makes search feel "
          "right. A provider registers coverage for Dhanmondi (a thana). A "
          "customer searches from Kalabagan (an area inside Dhanmondi). The "
          "search expands the customer's location into "
          "<font face='Courier'>descendant_ids() + ancestors()</font>, "
          "filtering out the city level, so the Dhanmondi provider matches. "
          "Without the ancestor half, a provider covering a whole thana would "
          "be invisible to anyone searching a specific street in it."),

    ("p", "The city level is excluded from the ancestor expansion deliberately. "
          "Including it would mean anyone who registered &lsquo;Dhaka&rsquo; "
          "matched every search in the city, which is how coverage spam starts. "
          "For the same reason "
          "<font face='Courier'>set_service_areas</font> refuses to store a "
          "city-level area at all."),

    ("h2", "6.3 The check constraint on hierarchy"),

    ("code", [
        "models.CheckConstraint(",
        '    condition=models.Q(level="city") | models.Q(parent__isnull=False),',
        '    name="location_non_city_requires_parent",',
        ")",
    ]),

    ("p", "An orphaned thana is unreachable from any tree walk and would "
          "silently never match a search. The database refuses to store one."),

    ("pagebreak", None),
)


# ======================================================================
# PROVIDERS
# ======================================================================

add(
    ("h1", "7. Providers: offerings, coverage, hours and verification"),

    ("p", "<font face='Courier'>backend/apps/providers/</font>. The largest "
          "app. It owns what a provider sells, where, when, and the documents "
          "that prove who they are &mdash; plus the search that ranks them."),

    ("h2", "7.1 The four things a provider configures"),

    ("table", {
        "cols": ["Model", "Holds", "Constraint worth noting"],
        "widths": [0.24, 0.38, 0.38],
        "rows": [
            ["<font face='Courier'>ProviderService</font>",
             "One service this provider offers, with their price and estimated "
             "duration.",
             "Unique on (provider, service) &mdash; you cannot list the same "
             "service twice at two prices."],
            ["<font face='Courier'>ServiceArea</font>",
             "One location covered, with an optional travel surcharge.",
             "Unique on (provider, location). City level rejected in the "
             "service layer."],
            ["<font face='Courier'>Availability</font>",
             "A recurring weekly window, e.g. Tuesday 09:00&ndash;17:00.",
             "Check constraint that end is after start; unique on "
             "(provider, weekday, start_time)."],
            ["<font face='Courier'>AvailabilityException</font>",
             "One specific date overriding the weekly pattern &mdash; a day "
             "off, or extra hours on a normally closed day.",
             "Unique per (provider, date). A check constraint forces hours to "
             "be present when <font face='Courier'>is_available</font> is true."],
        ],
    }),

    ("h3", "How availability is resolved"),

    ("p", "<font face='Courier'>resolve_availability()</font> encodes the "
          "precedence in six lines: if an exception exists for that date it "
          "wins outright &mdash; either &lsquo;closed&rsquo; (empty list) or "
          "the exception's own hours. Only when no exception exists does the "
          "weekly pattern for that weekday apply. Exceptions are absolute, not "
          "additive, which is what a provider intends when they mark a day off."),

    ("p", "Overlap detection when saving a weekly schedule uses the standard "
          "interval test &mdash; two windows overlap when "
          "<font face='Courier'>start &lt; other_end and other_start &lt; end</font> "
          "&mdash; and the whole set is validated before anything is written, "
          "so a partially-saved schedule is impossible."),

    ("h2", "7.2 Verification: the document pipeline"),

    ("p", "Four document types map onto three verification flags:"),

    ("table", {
        "cols": ["Documents approved", "Flag set", "Trust points"],
        "widths": [0.44, 0.32, 0.24],
        "rows": [
            ["NID front <b>and</b> NID back",
             "<font face='Courier'>identity_verified</font>", "40"],
            ["Trade certificate",
             "<font face='Courier'>skill_verified</font>", "20"],
            ["Address proof",
             "<font face='Courier'>address_verified</font>", "10"],
            ["(phone OTP, from the accounts app)",
             "<font face='Courier'>phone_verified</font>", "30"],
        ],
    }),

    ("p", "Note that identity requires <i>both</i> NID sides. "
          "<font face='Courier'>_sync_verification_flags()</font> recomputes "
          "all three flags from scratch from the set of currently-approved "
          "documents, rather than incrementally toggling them. That means "
          "revoking a document correctly un-verifies the provider, which an "
          "incremental approach would get wrong."),

    ("p", "Every approval or rejection also queues a trust recompute, because "
          "verification is 20% of the score."),

    ("h2", "7.3 Document storage is deliberately not public"),

    ("p", "This is one of the strongest security stories in the project and "
          "worth walking an interviewer through slowly."),

    ("p", "National ID scans must never be reachable by URL. "
          "<font face='Courier'>VerificationDocument.file</font> uses a "
          "separate storage backend, "
          "<font face='Courier'>PrivateMediaStorage</font>, which writes to "
          "<font face='Courier'>PRIVATE_MEDIA_ROOT</font> &mdash; a directory "
          "outside anything the web server serves. Its "
          "<font face='Courier'>url()</font> method does not return a path; it "
          "raises:"),

    ("code", [
        "def url(self, name):",
        "    raise NotImplementedError(",
        '        "Private media has no public URL. Serve it through an "',
        '        "authenticated view."',
        "    )",
    ]),

    ("p", "So if anyone ever writes a serializer that tries to expose the file "
          "URL, the code crashes loudly in a test rather than quietly leaking "
          "identity documents. The failure mode is an exception, not a breach."),

    ("p", "Admins view documents through "
          "<font face='Courier'>GET /api/v1/admin/verifications/{id}/file/</font>, "
          "which is <font face='Courier'>IsAdminUser</font>-gated and streams "
          "the file back with four deliberate headers:"),

    ("table", {
        "cols": ["Header", "Purpose"],
        "widths": [0.4, 0.6],
        "rows": [
            ["<font face='Courier'>Cache-Control: no-store</font>",
             "The document never lands in a browser or proxy cache."],
            ["<font face='Courier'>X-Content-Type-Options: nosniff</font>",
             "The browser must not second-guess the declared content type."],
            ["<font face='Courier'>Content-Security-Policy: default-src 'none'; sandbox</font>",
             "Even if a malicious file somehow rendered, it can load nothing "
             "and run nothing."],
            ["<font face='Courier'>Content-Disposition: inline</font>",
             "The admin sees it in-browser rather than downloading NID scans "
             "onto their laptop."],
        ],
    }),

    ("p", "Content type is derived from a whitelist dictionary keyed by "
          "extension, defaulting to "
          "<font face='Courier'>application/octet-stream</font> &mdash; never "
          "from the uploaded file's own claimed type."),

    ("h3", "Retention"),

    ("p", "On review, <font face='Courier'>purge_after</font> is set to 90 days "
          "out. The <font face='Courier'>purge_documents</font> job then "
          "deletes the file bytes while keeping the decision record. The "
          "platform retains proof that identity <i>was</i> verified and by "
          "whom, without retaining the NID scan indefinitely. That is data "
          "minimisation, and it is a good answer to any privacy question."),

    ("h2", "7.4 Upload validation: magic bytes, not extensions"),

    ("p", "<font face='Courier'>VerificationUploadSerializer.validate_file</font> "
          "reads the first 16 bytes of the upload and checks them against the "
          "real file signature for the claimed extension:"),

    ("code", [
        "MAX_BYTES = 5 * 1024 * 1024",
        "FORMATS = (",
        '    ({"jpg", "jpeg"}, b"\\xff\\xd8\\xff"),',
        '    ({"png"},         b"\\x89PNG\\r\\n\\x1a\\n"),',
        '    ({"pdf"},         b"%PDF-"),',
        ")",
    ]),

    ("p", "Both the extension and the content must agree. An HTML file renamed "
          "to <font face='Courier'>.jpg</font> &mdash; the classic stored-XSS "
          "vector &mdash; fails, because its bytes do not begin with the JPEG "
          "signature. A real JPEG renamed to "
          "<font face='Courier'>.pdf</font> also fails, because the pairing is "
          "checked, not just membership."),

    ("callout", {
        "title": "This was a real M10 finding",
        "body": "The original implementation checked only the extension. The "
                "security review caught it, and this is worth saying out loud "
                "in an interview: &lsquo;the first version trusted the "
                "extension; the M10 review found it and now the magic bytes "
                "are checked.&rsquo; Describing a bug you found in your own "
                "code reads as maturity, not weakness.",
    }),

    ("h2", "7.5 Provider search"),

    ("p", "<font face='Courier'>apps/providers/search.py</font>. One function, "
          "<font face='Courier'>search_providers()</font>, builds a single "
          "queryset. It measures 100 ms at p95 against 10,018 providers."),

    ("h3", "The base set"),

    ("p", "Before any filter: accepting work, user active, not suspended, and "
          "not in the <font face='Courier'>under_review</font> tier. That last "
          "exclusion is a product decision with teeth &mdash; a provider under "
          "investigation is not merely ranked lower, they are removed from "
          "discovery entirely and cannot receive broadcast requests."),

    ("h3", "Why EXISTS instead of a join"),

    ("p", "Filtering by service could be written as a join to "
          "<font face='Courier'>ProviderService</font>. It is written as "
          "<font face='Courier'>Exists(...)</font> instead, for two reasons: a "
          "join multiplies rows when a provider offers several matching "
          "services, forcing a "
          "<font face='Courier'>DISTINCT</font> that costs a sort; and "
          "PostgreSQL can short-circuit an "
          "<font face='Courier'>EXISTS</font> as soon as one row matches."),

    ("h3", "The matched-price subquery"),

    ("p", "Sorting by price is not sorting by a column &mdash; a provider has "
          "many prices. A correlated "
          "<font face='Courier'>Subquery</font> annotates each provider with "
          "the <i>lowest price among the services that matched this search</i>. "
          "A plumber whose drain-cleaning is cheap but whose bathroom "
          "installation is expensive sorts by the one the customer actually "
          "searched for. This is the query most likely to be asked about in an "
          "interview, and being able to explain why it is a subquery rather "
          "than an aggregate is the whole answer."),

    ("h3", "Ordering"),

    ("table", {
        "cols": ["ordering", "Sort", "Tie-breaks"],
        "widths": [0.22, 0.4, 0.38],
        "rows": [
            ["<font face='Courier'>-trust_score</font> (default)",
             "Trust descending.", "identity_verified, then pk."],
            ["<font face='Courier'>price</font>",
             "Matched price ascending, with "
             "<font face='Courier'>Coalesce</font> to 0 for nulls.",
             "identity_verified, trust, pk."],
            ["<font face='Courier'>distance</font>",
             "Manhattan distance in degrees from the search origin.",
             "trust, pk."],
        ],
    }),

    ("p", "Every ordering ends in <font face='Courier'>pk</font>. Without a "
          "unique final tie-break, PostgreSQL may return rows in a different "
          "order between two queries with the same "
          "<font face='Courier'>ORDER BY</font>, which makes pagination "
          "duplicate and drop rows. That is a classic, real bug and the "
          "<font face='Courier'>pk</font> at the end is the fix."),

    ("p", "Distance uses <font face='Courier'>abs(&Delta;lat) + abs(&Delta;lon)</font> "
          "rather than a proper haversine. Within one city the error is tiny, "
          "it needs no PostGIS extension, and it stays inside the database "
          "where the sort happens. The honest framing is: it is an "
          "approximation chosen deliberately, and PostGIS is the upgrade path "
          "if the product ever goes national."),

    ("h3", "Malformed filters degrade rather than fail"),

    ("p", "<font face='Courier'>?min_trust=abc</font> returns a broader result "
          "set, not a 400. For a public search endpoint a bad query parameter "
          "&mdash; usually from a stale bookmark or a crawler &mdash; should "
          "show results, not an error page."),

    ("pagebreak", None),
)


# ======================================================================
# TRUST -- the centrepiece
# ======================================================================

add(
    ("h1", "8. The trust engine"),

    ("p", "<font face='Courier'>backend/apps/trust/</font>. This is the heart "
          "of the project and the thing to spend the most interview time on. "
          "It is deliberately split in two: "
          "<font face='Courier'>factors.py</font> is pure arithmetic with no "
          "Django imports at all, and <font face='Courier'>engine.py</font> "
          "connects it to the database."),

    ("callout", {
        "title": "Why that split matters",
        "body": "<font face='Courier'>factors.py</font> imports only "
                "<font face='Courier'>math</font> and "
                "<font face='Courier'>dataclasses</font>. Every formula can be "
                "unit-tested with a plain dataclass and no database at all, "
                "which is why the trust tests run in milliseconds and why "
                "<font face='Courier'>docs/verify_trust_math.py</font> can be a "
                "standalone reference implementation that reproduces the same "
                "numbers.",
    }),

    ("h2", "8.1 The six factors"),

    ("table", {
        "cols": ["Factor", "Weight", "Question it answers"],
        "widths": [0.3, 0.12, 0.58],
        "rows": [
            ["F1 Verification depth", "20%", "Has this person proven who they are?"],
            ["F2 Job volume", "15%", "Is there enough evidence to judge them?"],
            ["F3 Completion reliability", "20%", "When they commit, do they finish?"],
            ["F4 Cancellation discipline", "15%",
             "How often do they break a commitment, and how badly?"],
            ["F5 Responsiveness", "10%", "How long does a customer wait for an answer?"],
            ["F6 Review quality", "20%", "What do verified customers say?"],
        ],
    }),

    ("p", "Each returns 0&ndash;100. The weighted sum is the base score; "
          "penalties are subtracted after; the result is clamped to 0&ndash;100."),

    ("h2", "8.2 F1 &mdash; Verification depth"),

    ("p", "Simple additive points: phone 30, identity 40, skill 20, address 10. "
          "The weighting is intentional. Identity is worth more than a trade "
          "certificate because knowing who someone is matters more for "
          "accountability than knowing they passed a course. A fully verified "
          "provider scores 100; phone-only scores 30."),

    ("h2", "8.3 F2 &mdash; Job volume, logarithmic"),

    ("code", [
        "def f2_volume(inputs):",
        "    completed = inputs.jobs_completed",
        "    if completed <= 0:",
        "        return 0.0",
        "    raw = 100.0 * log(1 + completed) / log(1 + 100)",
        "    return min(raw, 100.0)",
    ]),

    ("p", "Logarithmic with saturation at 100 jobs. The shape is the point: "
          "going from 1 to 5 jobs moves the factor about 26 points; going from "
          "50 to 100 moves it about 15. Early evidence is worth much more than "
          "late evidence, because the first few jobs tell you most of what you "
          "will ever learn, and farming hundreds of trivial jobs to inflate the "
          "score has sharply diminishing returns."),

    ("h2", "8.4 F3 &mdash; Completion, with Bayesian smoothing"),

    ("code", [
        "k, mu = 10, 0.90",
        "return 100.0 * (jobs_completed + k * mu) / (jobs_accepted + k)",
    ]),

    ("p", "This is the single most important formula in the project. The naive "
          "version is <font face='Courier'>completed / accepted</font>, and it "
          "is badly broken: a provider who accepted one job and finished it "
          "scores 100% &mdash; a perfect score on one data point."),

    ("p", "The smoothing adds a prior: ten imaginary jobs at the 90% platform "
          "average. A new provider therefore starts near 90 and moves toward "
          "their real rate as evidence accumulates. Work it through:"),

    ("table", {
        "cols": ["Real record", "Naive", "Smoothed"],
        "widths": [0.34, 0.2, 0.46],
        "rows": [
            ["1 of 1 completed", "100.0", "<b>90.9</b> &mdash; good, not proven"],
            ["5 of 5 completed", "100.0", "<b>93.3</b> &mdash; earning it"],
            ["50 of 50 completed", "100.0", "<b>98.3</b> &mdash; genuinely proven"],
            ["0 of 1 completed", "0.0", "<b>81.8</b> &mdash; one bad job is not a verdict"],
        ],
    }),

    ("p", "It is symmetric, and that symmetry is the fairness argument: it "
          "protects a newcomer from one unlucky job as much as it stops one "
          "lucky job looking like a track record. <font face='Courier'>k=10</font> "
          "is the strength of the prior &mdash; how many real jobs it takes "
          "before the provider's own record outweighs the platform average."),

    ("h2", "8.5 F4 &mdash; Cancellations, damage-weighted and decayed"),

    ("p", "Two providers each cancel 10% of jobs. One always gives two days' "
          "notice; the other no-shows. Treating those the same is wrong, so "
          "each cancellation is weighted by how much damage it did:"),

    ("table", {
        "cols": ["Notice given", "Weight", "Why"],
        "widths": [0.34, 0.16, 0.5],
        "rows": [
            ["24 hours or more", "1.0", "Annoying; the customer can rebook."],
            ["4 to 24 hours", "2.0", "The day is disrupted."],
            ["Under 4 hours", "4.0", "The customer has taken time off work."],
            ["No-show", "6.0", "They waited and nobody came."],
        ],
    }),

    ("p", "Each is then multiplied by exponential time decay with a 180-day "
          "half-life &mdash; <font face='Courier'>0.5 ** (days_ago / 180)</font> "
          "&mdash; so a cancellation from six months ago counts half, and one "
          "from a year ago counts a quarter. People improve, and a score that "
          "never forgives gives nobody a reason to."),

    ("p", "The weighted total is divided by jobs accepted, capped at 1.0, and "
          "then raised to the power 1.5:"),

    ("code", [
        "rate = weighted / float(jobs_accepted)",
        "return 100.0 * (1 - min(rate, 1.0)) ** 1.5",
    ]),

    ("p", "The exponent makes the penalty convex. A 10% weighted rate costs "
          "about 15 points, but a 30% rate costs about 41 &mdash; more than "
          "double, for triple the rate. Occasional cancellation is human; "
          "habitual cancellation is a different kind of provider, and the curve "
          "says so."),

    ("h2", "8.6 F5 &mdash; Responsiveness"),

    ("p", "A piecewise-linear curve over the median response time:"),

    ("table", {
        "cols": ["Median response", "Score"],
        "widths": [0.5, 0.5],
        "rows": [
            ["5 minutes or less", "100"],
            ["5 to 60 minutes", "100 down to 70"],
            ["1 to 4 hours", "70 down to 40"],
            ["4 to 24 hours", "40 down to 0"],
            ["Over 24 hours", "0"],
        ],
    }),

    ("p", "Two guards matter. Fewer than five recorded responses returns a "
          "neutral 60 rather than a real score, because a median of two data "
          "points is noise. And the median is used rather than the mean, over "
          "the last 30 responses only, so one holiday does not define a "
          "provider forever."),

    ("h2", "8.7 F6 &mdash; Review quality"),

    ("p", "Bayesian smoothing again, this time on a 1&ndash;5 scale with a "
          "prior of 4.2 at strength 5, and each review additionally weighted by "
          "365-day time decay:"),

    ("code", [
        "weighted_sum   = sum(rating * decay(days_ago, 365) for ...)",
        "weighted_count = sum(decay(days_ago, 365) for ...)",
        "bayes = (weighted_sum + 5 * 4.2) / (weighted_count + 5)",
        "return 100.0 * (bayes - 1) / 4.0",
    ]),

    ("p", "The final line rescales 1&ndash;5 to 0&ndash;100 linearly, so a "
          "1-star average maps to 0 rather than 20. Note that the decay applies "
          "to both numerator and denominator &mdash; old reviews lose "
          "influence rather than being deleted, which is mathematically the "
          "right way to age evidence."),

    ("p", "Only reviews that are published and not hidden are gathered, which "
          "is what makes the double-blind mechanism and admin moderation "
          "actually affect the score."),

    ("h2", "8.8 Penalties, applied after the weighted sum"),

    ("table", {
        "cols": ["Condition", "Penalty"],
        "widths": [0.6, 0.4],
        "rows": [
            ["An upheld dispute in the last 90 days", "&minus;15"],
            ["Two or more upheld disputes in 180 days", "&minus;25"],
            ["A no-show in the last 30 days", "&minus;10"],
            ["Currently under investigation", "&minus;20"],
        ],
    }),

    ("p", "These stack, and they are subtracted <i>after</i> the weighted sum "
          "rather than folded into a factor. That ordering is the whole point: "
          "if a dispute were one component of a weighted average, a provider "
          "with excellent numbers elsewhere would dilute it to almost nothing. "
          "A flat subtraction cannot be diluted. One serious incident costs the "
          "same fifteen points whether you are excellent or mediocre."),

    ("h2", "8.9 The worked example that sells the whole idea"),

    ("p", "Two providers the seeded data actually produces:"),

    ("table", {
        "cols": ["", "Kamal", "Shakib"],
        "widths": [0.4, 0.3, 0.3],
        "rows": [
            ["Star rating", "4.9", "4.8"],
            ["Jobs completed", "4 of 4", "18 of 30"],
            ["Cancellations", "0", "12 (3 under 4h notice)"],
            ["Median response", "8 minutes", "6 hours"],
            ["Verification", "Full (NID + trade cert)", "Phone only"],
            ["<b>Trust score</b>", "<b>84.19</b>", "<b>53.48</b>"],
        ],
    }),

    ("p", "On any conventional marketplace these two look identical &mdash; "
          "4.9 against 4.8. Shakib abandons 40% of the jobs he accepts and "
          "takes six hours to reply, and his review score is the "
          "<i>highest</i> of his six factors, which is precisely the one signal "
          "a star rating would have shown you. That is the pitch in two "
          "sentences, and both numbers are reproduced exactly by the test suite."),

    ("h2", "8.10 Tiers"),

    ("table", {
        "cols": ["Tier", "Requires"],
        "widths": [0.26, 0.74],
        "rows": [
            ["New", "Fewer than 3 completed jobs. Shown honestly as new."],
            ["Rising", "3+ jobs, any score below the Established bar."],
            ["Established", "Score &ge; 70, 10+ jobs, <b>and</b> identity verified."],
            ["Trusted Pro", "Score &ge; 85, 25+ jobs, <b>and</b> identity verified."],
            ["Under review", "Set by an admin. Overrides everything; removes "
                             "the provider from search and from broadcast requests."],
        ],
    }),

    ("p", "Identity verification is a hard gate on the top two tiers, not a "
          "contributor. No amount of good behaviour reaches Established while "
          "anonymous. Tiers exist because &lsquo;84.19&rsquo; means nothing to "
          "a customer at a glance while &lsquo;Trusted Pro&rsquo; does; the "
          "number is there for anyone who wants to look closer."),

    ("h2", "8.11 Snapshots: the audit trail"),

    ("p", "Every recompute writes a <font face='Courier'>TrustSnapshot</font>: "
          "the score, the tier, the full factor breakdown as JSON, the "
          "algorithm version, and the trigger that caused it. The model extends "
          "<font face='Courier'>AppendOnlyModel</font>, so it cannot be edited "
          "or deleted."),

    ("p", "Seven triggers are recorded: booking completed, booking cancelled, "
          "review changed, verification decided, dispute changed, nightly "
          "batch, and manual. This means a provider who asks &lsquo;why did my "
          "score drop on Tuesday?&rsquo; gets a real answer, and an admin "
          "reviewing an appeal can see exactly what the inputs were at the time."),

    ("p", "<font face='Courier'>algo_version</font> is stored on every "
          "snapshot. If the weights change to v1.1, historical snapshots remain "
          "interpretable under the version that produced them. This is "
          "unglamorous and it is exactly the kind of thing a senior engineer "
          "notices is present."),

    ("h2", "8.12 When trust is recomputed"),

    ("p", "Event-driven plus nightly. The event-driven half uses a pattern "
          "worth explaining precisely:"),

    ("code", [
        "transaction.on_commit(",
        "    lambda: engine.recompute(provider_id, trigger=mapped)",
        ")",
    ]),

    ("p", "<font face='Courier'>on_commit</font> defers the recompute until "
          "the surrounding transaction has actually committed. Two reasons. "
          "First, if the booking transaction rolls back, no snapshot is written "
          "for an event that never happened. Second, the recompute reads the "
          "provider's counters &mdash; running it inside the same transaction "
          "could read a state the rest of the world never sees."),

    ("p", "<font face='Courier'>recompute()</font> itself takes "
          "<font face='Courier'>select_for_update</font> on the provider row, "
          "so two bookings completing simultaneously cannot interleave and "
          "write inconsistent snapshots."),

    ("p", "The nightly batch exists because <b>time decay moves even when "
          "nothing happens</b>. A cancellation ages, a review ages, and the "
          "score must reflect that. It iterates with "
          "<font face='Courier'>.values_list('pk', flat=True).iterator()</font> "
          "&mdash; ids only, streamed &mdash; so memory stays flat at ten "
          "thousand providers. It measures 175 seconds against a 15-minute "
          "target."),

    ("h2", "8.13 Anti-gaming, summarised"),

    ("p", "Every formula choice is a defence. Worth having this list ready as "
          "one answer:"),

    ("table", {
        "cols": ["Attack", "Defence"],
        "widths": [0.44, 0.56],
        "rows": [
            ["Create an account, do one perfect job, look flawless",
             "Bayesian priors on F3 and F6; the New tier below 3 jobs; "
             "logarithmic F2."],
            ["Farm many tiny jobs to inflate volume",
             "Logarithmic F2 saturating at 100 jobs."],
            ["Accept everything, deliver selectively",
             "F3 uses accepted as the denominator, not completed."],
            ["Cancel late but often, hiding behind good reviews",
             "F4 damage weighting up to 6&times;, convex exponent 1.5."],
            ["Wait out a bad incident",
             "Decay exists but is slow (180 and 365-day half-lives), and "
             "penalties sit outside the weighted sum."],
            ["Fake reviews from friends",
             "A review requires a completed booking, which requires an "
             "accepted request and a confirmed completion; reviews are "
             "double-blind and admins can hide them."],
            ["Stay anonymous while scoring highly",
             "Identity verification is a hard gate on Established and "
             "Trusted Pro."],
        ],
    }),

    ("pagebreak", None),
)


# ======================================================================
# BOOKINGS
# ======================================================================

add(
    ("h1", "9. Bookings: the request and job lifecycle"),

    ("p", "<font face='Courier'>backend/apps/bookings/</font>. Four models and "
          "a state machine. This is where most of the concurrency thinking "
          "lives."),

    ("h2", "9.1 The four models"),

    ("bullets", [
        "<b>ServiceRequest</b> &mdash; a customer asking for work. States: "
        "open, accepted, withdrawn, expired. Kinds: broadcast or direct.",

        "<b>RequestPhoto</b> &mdash; up to five photos of the problem.",

        "<b>ProviderResponse</b> &mdash; one provider's accept or decline, "
        "with <font face='Courier'>response_seconds</font> recorded. Unique per "
        "(request, provider).",

        "<b>Booking</b> &mdash; created when a provider accepts. One-to-one "
        "with the request.",

        "<b>BookingEvent</b> &mdash; append-only log of every transition: from "
        "state, to state, actor, actor user, reason, metadata.",
    ]),

    ("h2", "9.2 The state machine"),

    ("p", "In <font face='Courier'>state_machine.py</font>, transitions are a "
          "single dictionary. Being able to point at one 25-line file and say "
          "&lsquo;every legal move in the system is here&rsquo; is worth a lot "
          "in an interview."),

    ("table", {
        "cols": ["From", "May move to"],
        "widths": [0.32, 0.68],
        "rows": [
            ["<font face='Courier'>scheduled</font>",
             "in_progress, cancelled_customer, cancelled_provider"],
            ["<font face='Courier'>in_progress</font>",
             "awaiting_confirm, cancelled_customer, cancelled_provider"],
            ["<font face='Courier'>awaiting_confirm</font>", "completed, disputed"],
            ["<font face='Courier'>completed</font>", "disputed"],
            ["<font face='Courier'>cancelled_customer</font>",
             "&mdash; terminal"],
            ["<font face='Courier'>cancelled_provider</font>",
             "&mdash; terminal"],
            ["<font face='Courier'>disputed</font>",
             "completed (after resolution)"],
        ],
    }),

    ("p", "Three design points to call out:"),

    ("numbers", [
        "<b>A cancellation is final.</b> Both cancelled states have empty "
        "transition sets. Undoing a cancellation would mean the provider's "
        "cancellation counter and the customer's expectations had already "
        "diverged from reality &mdash; the correct response is a new request, "
        "not a resurrection.",

        "<b><font face='Courier'>completed</font> can still become "
        "<font face='Courier'>disputed</font>.</b> Bad work is often only "
        "discovered later, and auto-confirmation after 72 hours means "
        "&lsquo;completed&rsquo; sometimes means &lsquo;nobody objected&rsquo;.",

        "<b>The state machine is enforced in one place.</b> "
        "<font face='Courier'>_transition()</font> calls "
        "<font face='Courier'>assert_can_transition</font> before any write, so "
        "no service function can move a booking illegally even by mistake.",
    ]),

    ("h3", "One transition helper, one event log"),

    ("p", "Every state change funnels through "
          "<font face='Courier'>_transition()</font>, which validates, sets the "
          "state, applies any extra field updates, saves with an explicit "
          "<font face='Courier'>update_fields</font>, and writes the "
          "<font face='Courier'>BookingEvent</font>. Because there is exactly "
          "one path, the audit log cannot have gaps &mdash; a developer would "
          "have to deliberately bypass the helper to create one."),

    ("h2", "9.3 Who is eligible for a broadcast request"),

    ("p", "<font face='Courier'>matching_provider_ids()</font> is the matching "
          "engine. For a direct request it is exactly one provider. For a "
          "broadcast it is every provider who:"),

    ("bullets", [
        "has a service area in the requested location's expanded tree "
        "(descendants plus non-city ancestors),",
        "actively offers that specific service,",
        "is accepting work,",
        "has an active, unsuspended user account,",
        "and is not in the <font face='Courier'>under_review</font> tier.",
    ]),

    ("p", "The same function answers both &lsquo;who should see this?&rsquo; "
          "and &lsquo;may this provider respond?&rsquo; via "
          "<font face='Courier'>can_provider_respond()</font>. One definition, "
          "so the inbox and the authorisation check can never disagree &mdash; "
          "which is the kind of drift that causes real security bugs."),

    ("h2", "9.4 The responsiveness denominator"),

    ("p", "When a request is created, "
          "<font face='Courier'>_bump_requests_received()</font> increments "
          "<font face='Courier'>requests_received</font> for every matching "
          "provider with a single atomic "
          "<font face='Courier'>F()</font> update. This is the denominator of "
          "F5: a provider who ignores requests is measured, not merely absent "
          "from the data. Without it, ignoring every request would look "
          "identical to never having been asked."),

    ("h2", "9.5 Concurrency: the double-accept problem"),

    ("p", "Two providers hit &lsquo;accept&rsquo; on the same broadcast request "
          "at the same millisecond. Both must not get a booking. The fix is in "
          "<font face='Courier'>respond_to_request()</font>:"),

    ("code", [
        "@transaction.atomic",
        "def respond_to_request(*, request_id, provider_id, accept, ...):",
        "    request = (",
        "        ServiceRequest.objects",
        "        .select_for_update()",
        "        .select_related('service', 'location', 'customer')",
        "        .filter(pk=request_id)",
        "        .first()",
        "    )",
    ]),

    ("p", "<font face='Courier'>select_for_update()</font> takes a row-level "
          "write lock in PostgreSQL. The second provider's transaction blocks "
          "at that line until the first commits, then re-reads the row, finds "
          "<font face='Courier'>state == 'accepted'</font>, and gets a clean "
          "<font face='Courier'>request_closed</font> error. No race, no "
          "duplicate booking, no application-level retry logic."),

    ("p", "The same pattern guards the batch jobs. "
          "<font face='Courier'>expire_stale_requests()</font> and "
          "<font face='Courier'>auto_confirm_bookings()</font> both iterate "
          "loosely, then re-lock and re-check state inside a per-row "
          "transaction &mdash; so two cron runs firing simultaneously cannot "
          "double-process the same row. This is exactly the idempotency rule "
          "from section 4.2 in practice."),

    ("h2", "9.6 What happens on completion"),

    ("p", "<font face='Courier'>confirm_completion()</font> is the busiest "
          "moment in the system. In one atomic transaction it:"),

    ("numbers", [
        "locks the booking row,",
        "transitions <font face='Courier'>awaiting_confirm &rarr; completed</font>, "
        "recording the confirmed price,",
        "writes the BookingEvent,",
        "increments <font face='Courier'>jobs_completed</font> atomically,",
        "calls <font face='Courier'>record_completion_payment()</font>, which "
        "creates the Payment and three LedgerEntry rows,",
        "and queues the trust recompute for after the commit.",
    ]),

    ("p", "All of it is one transaction, so a crash halfway cannot leave a "
          "completed booking with no payment record or an incremented counter "
          "with no booking."),

    ("h2", "9.7 Two timers"),

    ("table", {
        "cols": ["Timer", "Window", "Effect"],
        "widths": [0.26, 0.16, 0.58],
        "rows": [
            ["Request expiry", "24 hours",
             "An unanswered open request becomes "
             "<font face='Courier'>expired</font>. The customer is not left "
             "watching a dead request forever."],
            ["Auto-confirm", "72 hours",
             "A booking left in <font face='Courier'>awaiting_confirm</font> is "
             "confirmed by the system at the provider's stated final price, "
             "with <font face='Courier'>auto_confirmed=True</font> and a "
             "<font face='Courier'>system</font> actor on the event."],
        ],
    }),

    ("p", "Auto-confirm exists because a provider should not go unpaid and "
          "un-credited because a customer forgot to tap a button. The flag "
          "records that it was automatic, so the data can distinguish "
          "&lsquo;the customer confirmed&rsquo; from &lsquo;nobody "
          "objected&rsquo; &mdash; which is why "
          "<font face='Courier'>completed &rarr; disputed</font> stays legal."),

    ("pagebreak", None),
)


# ======================================================================
# REVIEWS
# ======================================================================

add(
    ("h1", "10. Reviews and payments"),

    ("h2", "10.1 Why double-blind"),

    ("p", "In a one-sided system the second reviewer sees the first review "
          "before writing theirs. That produces two well-documented distortions: "
          "retaliation (a provider who got 2 stars gives the customer 1 star) "
          "and reciprocity (both sides quietly inflate to keep the peace). Both "
          "destroy the signal the trust engine depends on."),

    ("p", "ServoraBd hides both reviews until either both are submitted or 14 "
          "days pass. The mechanism is a "
          "<font face='Courier'>published_at</font> timestamp that is null "
          "until reveal, plus a <font face='Courier'>reveal_deadline</font>."),

    ("code", [
        "def _maybe_reveal(booking):",
        "    review = Review.objects.filter(booking=booking).first()",
        "    rating = CustomerRating.objects.filter(booking=booking).first()",
        "    if review is None or rating is None:",
        "        return False",
        "    # both present -- publish both, recompute trust",
    ]),

    ("p", "Called after both <font face='Courier'>create_review</font> and "
          "<font face='Courier'>rate_customer</font>, so whichever side "
          "finishes second triggers the reveal. The "
          "<font face='Courier'>reveal_reviews</font> job handles the timeout "
          "case hourly: after 14 days the review publishes even if the other "
          "side never responded, so one silent party cannot suppress feedback "
          "forever."),

    ("p", "Crucially, <b>only published, unhidden reviews feed F6</b>. An "
          "unpublished review is invisible to the trust engine, so a provider "
          "cannot infer their rating from a score change before the reveal."),

    ("h2", "10.2 The other review rules"),

    ("table", {
        "cols": ["Rule", "Value", "Reason"],
        "widths": [0.3, 0.18, 0.52],
        "rows": [
            ["Review window", "30 days",
             "After a month, memory is unreliable and the job is stale."],
            ["Edit window", "24 hours",
             "Correcting a typo or a hasty rating is fair; rewriting history "
             "weeks later is not."],
            ["Edits are logged", "always",
             "<font face='Courier'>ReviewEdit</font> is append-only and stores "
             "the previous rating and comment."],
            ["Provider reply", "one per review",
             "Right of reply, not a comment thread. Only after publication."],
            ["Admin hide", "reason required",
             "Hiding removes it from F6 and recomputes trust immediately."],
        ],
    }),

    ("p", "A review requires a <font face='Courier'>COMPLETED</font> booking "
          "and is one-to-one with it. There is no way to review a provider you "
          "never hired, which is what makes fake-review farming expensive: an "
          "attacker would need a real request, a real acceptance and a real "
          "confirmation for every fake review."),

    ("h2", "10.3 Payments: cash, honestly modelled"),

    ("p", "Phase 1 is cash on completion. There is no payment gateway, and the "
          "model is honest about that &mdash; but it is built so that adding "
          "one is additive: <font face='Courier'>Payment.Method</font> already "
          "has bKash, Nagad and card, and there are "
          "<font face='Courier'>gateway</font>, "
          "<font face='Courier'>gateway_reference</font> and "
          "<font face='Courier'>gateway_payload</font> fields waiting."),

    ("h3", "The two-sided amount check"),

    ("p", "The provider records what they charged; the customer confirms what "
          "they paid. Both numbers are stored:"),

    ("bullets", [
        "If they match &rarr; the payment settles automatically.",
        "If they differ &rarr; status becomes "
        "<font face='Courier'>flagged</font>, "
        "<font face='Courier'>flagged_at</font> is stamped, a warning is "
        "logged, and <b>no ledger entries are written</b> until an admin "
        "resolves it at a decided amount with a mandatory note.",
    ]),

    ("p", "This is the right shape for a cash marketplace. The platform cannot "
          "observe the transaction, so it records both claims and escalates "
          "disagreement rather than silently trusting either party."),

    ("h3", "The three ledger entries"),

    ("p", "A settled 1,000 BDT cash job at 12% commission writes:"),

    ("table", {
        "cols": ["Kind", "Amount", "Meaning"],
        "widths": [0.28, 0.2, 0.52],
        "rows": [
            ["<font face='Courier'>earning</font>", "+1000.00",
             "The job was worth this."],
            ["<font face='Courier'>commission</font>", "&minus;120.00",
             "The platform's 12% cut."],
            ["<font face='Courier'>cash_retained</font>", "&minus;1000.00",
             "The provider already holds the cash."],
        ],
    }),

    ("p", "Balance: &minus;120.00. A <b>negative balance means the provider "
          "owes the platform</b> its commission, which is exactly right for "
          "cash &mdash; the money never passed through the platform, so "
          "commission is a receivable, not a deduction. When the provider pays "
          "it, a <font face='Courier'>settlement</font> entry of +120.00 brings "
          "the balance to zero."),

    ("p", "<font face='Courier'>record_provider_settlement()</font> refuses a "
          "settlement larger than the outstanding payable, so the ledger cannot "
          "be pushed into a fictitious credit."),

    ("h3", "Money correctness"),

    ("bullets", [
        "<b>Decimal, never float.</b> Every amount is a "
        "<font face='Courier'>DecimalField</font>, and "
        "<font face='Courier'>money()</font> quantises to two places with "
        "<font face='Courier'>ROUND_HALF_UP</font> &mdash; banker's rounding "
        "would surprise users.",

        "<b>The commission rate is copied onto the Payment row.</b> If the "
        "platform rate changes from 12% to 15%, historical payments keep the "
        "rate they were settled at. Reading it live from settings would "
        "retroactively rewrite history.",

        "<b>Ledger entries are append-only.</b> A correction is a new "
        "<font face='Courier'>adjustment</font> entry, never an edit. That is "
        "how real accounting works.",

        "<b>Money is a string end to end in the frontend.</b> It is formatted "
        "for display and never added, subtracted or rounded in JavaScript, "
        "where <font face='Courier'>0.1 + 0.2 !== 0.3</font>.",
    ]),

    ("h3", "Two database constraints doing real work"),

    ("code", [
        "# at most one cash payment per booking",
        "UniqueConstraint(fields=['booking'],",
        "                 condition=Q(method='cash'),",
        "                 name='one_cash_payment_per_booking')",
        "",
        "# at most one earning / commission / cash_retained per booking",
        "UniqueConstraint(fields=['booking', 'kind'],",
        "                 condition=Q(kind__in=['earning', 'commission',",
        "                                       'cash_retained']),",
        "                 name='one_accrual_of_each_kind_per_booking')",
    ]),

    ("p", "These are partial unique indexes. Even if a bug called "
          "<font face='Courier'>record_completion_payment</font> twice, the "
          "database refuses the double-accrual. Payouts and adjustments are "
          "deliberately excluded from the second constraint, because a provider "
          "can legitimately be paid or adjusted more than once."),

    ("h3", "Reconciliation"),

    ("p", "<font face='Courier'>reconcile_provider()</font> walks every "
          "completed booking and checks that a payment exists, that the "
          "earning entry equals the settled amount, and that the commission "
          "entry equals the commission. The "
          "<font face='Courier'>reconcile_earnings</font> job runs it nightly. "
          "The README's claim that &lsquo;every provider's ledger reconciles "
          "against their bookings&rsquo; is this function, asserted in the "
          "test suite."),

    ("pagebreak", None),
)


# ======================================================================
# OPERATIONS
# ======================================================================

add(
    ("h1", "11. Operations, scheduled work and security"),

    ("h2", "11.1 The seven scheduled jobs"),

    ("p", "There is no Celery and no Redis. Recurring work is Django "
          "management commands run by cron or Windows Task Scheduler. The "
          "schedule is declared as data in "
          "<font face='Courier'>apps/operations/jobs.py</font>:"),

    ("table", {
        "cols": ["Job", "Cron", "What it does"],
        "widths": [0.28, 0.2, 0.52],
        "rows": [
            ["<font face='Courier'>expire_requests</font>", "*/15 * * * *",
             "Closes requests nobody answered within 24 hours."],
            ["<font face='Courier'>auto_confirm</font>", "5 * * * *",
             "Confirms jobs the customer left unconfirmed for 72 hours."],
            ["<font face='Courier'>reveal_reviews</font>", "10 * * * *",
             "Publishes reviews whose 14-day double-blind window closed."],
            ["<font face='Courier'>recompute_all_trust</font>", "0 3 * * *",
             "Refreshes every score so time decay keeps moving."],
            ["<font face='Courier'>reconcile_earnings</font>", "30 3 * * *",
             "Checks every ledger against its payments."],
            ["<font face='Courier'>purge_otps</font>", "*/10 * * * *",
             "Deletes spent and expired verification codes."],
            ["<font face='Courier'>purge_documents</font>", "0 4 * * *",
             "Deletes verification files past their 90-day retention."],
        ],
    }),

    ("p", "Because the schedule is data rather than a crontab file, "
          "<font face='Courier'>manage.py crontab</font> can print the install "
          "lines, and the health endpoint can compare each job's last run "
          "against its declared interval."),

    ("h3", "Every run is recorded"),

    ("p", "<font face='Courier'>ScheduledCommand</font> is a base class every "
          "job inherits. It creates a <font face='Courier'>JobRun</font> row on "
          "start, marks it succeeded with a row count on completion, or failed "
          "with the exception type and message, then prunes runs older than 30 "
          "days."),

    ("p", "<font face='Courier'>GET /api/v1/admin/jobs/</font> (admin only) "
          "reports each job's last status, last success, whether it is "
          "<b>overdue</b> (no run within twice its interval) and whether it is "
          "<b>stuck</b> (still marked running long after it should have "
          "finished). This is the answer to &lsquo;how do you know cron is "
          "still working?&rsquo; &mdash; a cron job that silently stops is one "
          "of the classic production failure modes, and here it is visible."),

    ("h3", "Why no Celery"),

    ("p", "Phase 1 load does not need it, and a queue is not free: a broker to "
          "run, a worker to supervise, dead-letter handling, and a whole class "
          "of &lsquo;the task ran but the transaction had not committed&rsquo; "
          "bugs. The PRD records the thresholds that would justify adopting "
          "one, and the three service-layer rules from section 4.2 keep the "
          "migration to one line per call site. That is the complete answer: "
          "not &lsquo;we did not need it&rsquo; but &lsquo;here is when we "
          "would, and here is what we did so that day is cheap.&rsquo;"),

    ("h2", "11.2 The rate-limit bypass, and how it was closed"),

    ("p", "This is the best security story in the project. Learn it verbatim."),

    ("p", "DRF identifies a client for throttling by reading "
          "<font face='Courier'>X-Forwarded-For</font>. Behind a proxy that is "
          "necessary &mdash; otherwise every request appears to come from the "
          "proxy. But <font face='Courier'>X-Forwarded-For</font> is a request "
          "header, and <b>anyone can send one</b>. With the default "
          "configuration, an attacker sends a different forged value on every "
          "login attempt and each one looks like a new client. The five-per-15-"
          "minutes login limit becomes unlimited, and so does the OTP limit."),

    ("p", "The fix is <font face='Courier'>NUM_PROXIES</font>, driven by the "
          "<font face='Courier'>TRUSTED_PROXY_COUNT</font> environment "
          "variable. It tells DRF how many proxies sit in front of the "
          "application, so it counts that many entries from the <i>right-hand "
          "end</i> of the header &mdash; the part written by infrastructure you "
          "control &mdash; and ignores everything the client prepended."),

    ("table", {
        "cols": ["Deployment", "TRUSTED_PROXY_COUNT"],
        "widths": [0.52, 0.48],
        "rows": [
            ["Local development, no proxy", "0"],
            ["One Nginx in front of gunicorn", "1"],
            ["Render (one platform router)", "1"],
            ["CDN in front of Nginx", "2"],
        ],
    }),

    ("callout", {
        "title": "Too high is worse than too low",
        "body": "Setting it too low means everyone behind the proxy shares one "
                "bucket &mdash; annoying but safe. Setting it too "
                "<i>high</i> means the limiter starts reading attacker-"
                "controlled entries, and the bypass is back. When unsure, "
                "guess low.",
    }),

    ("p", "Because this cannot be verified from code alone &mdash; it depends "
          "on the deployment topology &mdash; there is a command for it. "
          "<font face='Courier'>manage.py check_proxy_count &lt;url&gt;</font> "
          "sends two requests to a live deployment, one with a forged "
          "<font face='Courier'>X-Forwarded-For: 203.0.113.7</font> and one "
          "without, and reads back the "
          "<font face='Courier'>X-Client-Ident</font> header that "
          "<font face='Courier'>ClientIdentHeaderMiddleware</font> adds when "
          "<font face='Courier'>EXPOSE_CLIENT_IDENT</font> is temporarily "
          "enabled. If the forged address is what the limiter sees, the command "
          "fails with instructions."),

    ("p", "Writing a tool to verify your own security configuration against a "
          "live deployment is unusual in a portfolio project and worth "
          "mentioning without being asked."),

    ("h2", "11.3 The access-control audit test"),

    ("p", "<font face='Courier'>apps/common/tests/test_access_control.py</font> "
          "is the test to show an interviewer if you only get to show one. It "
          "walks Django's URL resolver at runtime, collects every route under "
          "<font face='Courier'>/api/v1/</font>, and asserts that:"),

    ("numbers", [
        "every route not on an explicit 15-entry public allowlist returns "
        "<b>401</b> to an anonymous caller, on both GET and POST;",
        "every route under <font face='Courier'>/api/v1/admin/</font> returns "
        "<b>403</b> to an ordinary logged-in customer;",
        "the allowlist names only routes that actually exist, so a deleted "
        "route cannot linger as a permanent exemption;",
        "at least 60 routes are being checked, so the test cannot silently "
        "pass by finding nothing.",
    ]),

    ("p", "The value is that it is <b>generated from the URL conf, not "
          "hand-written</b>. Add a new endpoint and forget its "
          "<font face='Courier'>permission_classes</font>, and this test fails "
          "before the code merges. Most projects protect endpoints by "
          "convention and code review; this one protects them mechanically."),

    ("h2", "11.4 The rest of the security posture"),

    ("table", {
        "cols": ["Concern", "How it is handled"],
        "widths": [0.26, 0.74],
        "rows": [
            ["SQL injection",
             "The ORM parameterises everything. There is no raw SQL in the "
             "codebase."],
            ["XSS",
             "React escapes by default and there is no "
             "<font face='Courier'>dangerouslySetInnerHTML</font> anywhere. "
             "Uploads are magic-byte checked so an HTML file cannot be stored "
             "as an image."],
            ["CSRF",
             "The API is JWT-in-header, not cookie-authenticated, so it is not "
             "CSRF-reachable. Django admin keeps its CSRF middleware."],
            ["Password storage",
             "Django PBKDF2 with four validators, minimum length 8, plus the "
             "common-password and numeric-only checks."],
            ["Object-level access",
             "Every service filters by owner in the same query that fetches "
             "the row &mdash; "
             "<font face='Courier'>filter(pk=booking_id, customer_id=customer_id)</font> "
             "&mdash; so a wrong owner yields 404, not 403. It does not even "
             "confirm the object exists."],
            ["Suspended users",
             "Blocked at login (the token serializer refuses) and at every "
             "permission class (<font face='Courier'>not user.is_suspended</font>)."],
            ["Production headers",
             "HSTS one year with preload and subdomains, SSL redirect, "
             "nosniff, <font face='Courier'>X-Frame-Options: DENY</font>, "
             "secure and HttpOnly cookies, "
             "<font face='Courier'>Referrer-Policy: same-origin</font>."],
            ["Dependency vulnerabilities",
             "<font face='Courier'>pip-audit</font> and "
             "<font face='Courier'>npm audit</font> run in CI on every push. "
             "The Django 5.2 LTS upgrade cleared 37 known vulnerabilities."],
            ["Deploy checklist",
             "CI runs <font face='Courier'>manage.py check --deploy "
             "--fail-level WARNING</font> against the production settings "
             "module, so a misconfiguration fails the build."],
        ],
    }),

    ("h3", "The 404-not-403 decision"),

    ("p", "When customer A requests customer B's booking, the API returns 404. "
          "Returning 403 would confirm the booking exists, which leaks "
          "information &mdash; an attacker could enumerate valid booking ids by "
          "the difference between 403 and 404. Because ownership is part of the "
          "<font face='Courier'>filter()</font> rather than a check after "
          "fetching, this falls out of the code structure rather than needing "
          "discipline."),

    ("pagebreak", None),
)


# ======================================================================
# FRONTEND
# ======================================================================

add(
    ("h1", "12. The frontend"),

    ("p", "React 18.3, Vite 6, plain JavaScript, TanStack Query for server "
          "state, Zustand for session state, Tailwind CSS 4. Mobile-first: "
          "every screen is designed at 360 px and the end-to-end suite drives "
          "the whole product at that width."),

    ("h2", "12.1 The layer stack"),

    ("table", {
        "cols": ["Layer", "File", "Job"],
        "widths": [0.2, 0.26, 0.54],
        "rows": [
            ["Transport", "<font face='Courier'>api/client.js</font>",
             "fetch wrapper: auth header, token refresh, error normalisation."],
            ["Normalisation", "<font face='Courier'>api/normalize.js</font>",
             "Every API response mapped from snake_case to camelCase."],
            ["Endpoints", "<font face='Courier'>api/endpoints.js</font>",
             "One function per backend route, returning normalised data."],
            ["Server state", "TanStack Query",
             "Caching, refetching, loading and error states."],
            ["Session state", "<font face='Courier'>store/auth.js</font>",
             "Zustand, with the refresh token persisted to localStorage."],
            ["Constants", "<font face='Courier'>constants/domain.js</font>",
             "Frozen booking states, trust tiers, labels and tones."],
            ["Components", "<font face='Courier'>components/</font>",
             "UI primitives, Trust, domain widgets, Layout."],
            ["Pages", "<font face='Courier'>pages/</font>",
             "One file per route; <font face='Courier'>provider/</font> holds "
             "the provider side."],
        ],
    }),

    ("h2", "12.2 The five decisions worth defending"),

    ("h3", "JavaScript, not TypeScript"),

    ("p", "A deliberate choice, with three compensating mechanisms rather than "
          "a shrug: frozen constant objects so a typo in "
          "<font face='Courier'>BOOKING_STATE.AWAITING_CONFIRM</font> throws "
          "instead of rendering nothing; a normaliser layer so a backend field "
          "rename breaks one file and its tests rather than six screens; and "
          "PropTypes on every component that touches money, state or trust. It "
          "is recorded as a decision in PRD &sect;8.6, not an omission."),

    ("h3", "React pinned to 18.3, not 19"),

    ("p", "React 19 silently ignores "
          "<font face='Courier'>propTypes</font> on function components. Since "
          "PropTypes are how this JavaScript codebase catches a wrong-shaped "
          "prop at runtime, upgrading would switch off the type safety without "
          "a single warning. This is a genuinely good answer to &lsquo;why are "
          "you on an old React?&rsquo;"),

    ("h3", "The access token never touches localStorage"),

    ("p", "Only the refresh token and the user object are persisted, via "
          "Zustand's <font face='Courier'>partialize</font>. The access token "
          "lives in memory only. After a page reload there is therefore no "
          "access token, so the first authenticated call refreshes <i>before</i> "
          "it sends rather than going out bare and taking a 401 and a retry."),

    ("h3", "Single-flight refresh"),

    ("p", "This is the subtlest piece of frontend code in the project:"),

    ("code", [
        "let refreshInFlight = null;",
        "",
        "export function refreshSession() {",
        "  if (refreshInFlight) return refreshInFlight;",
        "  refreshInFlight = send('/auth/refresh/', {...})",
        "    .then(...)",
        "    .finally(() => { refreshInFlight = null; });",
        "  return refreshInFlight;",
        "}",
    ]),

    ("p", "Three components mount at once and all three fire a request with an "
          "expired token. Without this, three refresh calls go out. The backend "
          "rotates and blacklists refresh tokens, so the first succeeds and "
          "<b>the other two present a now-blacklisted token and fail</b> "
          "&mdash; logging the user out at random. Holding the in-flight "
          "promise makes all three callers await the same refresh. "
          "<font face='Courier'>client.test.js</font> asserts both this and the "
          "refresh-before-first-call behaviour."),

    ("h3", "Money is a string, everywhere"),

    ("p", "Amounts arrive as strings, are stored as strings and are formatted "
          "for display. JavaScript never adds, subtracts or rounds them, "
          "because IEEE-754 doubles cannot represent 0.1 exactly. Any total the "
          "UI shows is computed by the backend in "
          "<font face='Courier'>Decimal</font>."),

    ("h2", "12.3 Every page, and what it does"),

    ("h3", "Public pages"),

    ("table", {
        "cols": ["Route", "File", "What happens"],
        "widths": [0.24, 0.24, 0.52],
        "rows": [
            ["<font face='Courier'>/</font>", "Home.jsx",
             "Landing page. Its hero is pre-rendered to static HTML at build "
             "time, which is what gets LCP to 1.58 s. React then hydrates with "
             "identical markup, so layout shift stays at zero."],
            ["<font face='Courier'>/services</font>", "Services.jsx",
             "Category grid, then services within a category. Data comes from "
             "<font face='Courier'>useCatalogue</font>, cached by TanStack "
             "Query since the catalogue barely changes."],
            ["<font face='Courier'>/providers</font>", "ProviderSearch.jsx",
             "The filter panel (service, category, location, minimum trust, "
             "tier, verified-only, price band, availability date, sort) and "
             "the ranked result list. Filters live in the URL query string, so "
             "a filtered search is shareable and survives a reload."],
            ["<font face='Courier'>/providers/:id</font>", "ProviderProfile.jsx",
             "Full profile: trust breakdown, services with price flags, "
             "service areas, weekly hours, work photos, published reviews with "
             "provider replies. On a phone the trust breakdown sits directly "
             "under the name &mdash; it is the signature feature and must not "
             "be the last thing on screen."],
            ["<font face='Courier'>/compare</font>", "Compare.jsx",
             "Up to three providers side by side, compared on trust factors "
             "rather than price. The comparison list is a separate Zustand "
             "store so it survives navigation."],
            ["<font face='Courier'>/login</font>, <font face='Courier'>/register</font>",
             "Auth.jsx",
             "Phone or email, password, role choice on registration, then the "
             "OTP step. Errors are read from "
             "<font face='Courier'>ApiError.fieldError(name)</font> and shown "
             "against the right field."],
        ],
    }),

    ("h3", "Customer pages"),

    ("table", {
        "cols": ["Route", "File", "What happens"],
        "widths": [0.26, 0.22, 0.52],
        "rows": [
            ["<font face='Courier'>/request-service</font>", "RequestService.jsx",
             "The six-step wizard: Service, Where, Problem, When, Who, "
             "Confirm. The draft is written to "
             "<font face='Courier'>sessionStorage</font> after every step, so "
             "a mid-way refresh loses nothing. Time is picked as a named slot "
             "(Morning, Midday, Afternoon, Evening) rather than a raw "
             "timestamp, then converted to a Dhaka-local ISO window."],
            ["<font face='Courier'>/my-requests</font>", "Bookings.jsx",
             "Open, accepted, withdrawn and expired requests, with the "
             "responses each received and a withdraw action."],
            ["<font face='Courier'>/my-bookings</font>", "Bookings.jsx",
             "Bookings in every state, filterable. The same "
             "<font face='Courier'>BookingList</font> component serves the "
             "provider side with different props."],
            ["<font face='Courier'>/my-bookings/:id</font>", "Bookings.jsx",
             "One booking with its full event timeline, and the actions legal "
             "from its current state &mdash; confirm, cancel, dispute. The "
             "action set is derived from the state constant, so the UI can "
             "never offer a move the backend would reject."],
            ["<font face='Courier'>/review/:bookingId</font>", "ReviewBooking.jsx",
             "Overall rating plus four optional dimensions (punctuality, "
             "quality, professionalism, price fairness) and a comment. It "
             "states plainly that the review stays hidden until the provider "
             "also submits."],
        ],
    }),

    ("h3", "Provider pages"),

    ("table", {
        "cols": ["Route", "File", "What happens"],
        "widths": [0.28, 0.22, 0.5],
        "rows": [
            ["<font face='Courier'>/provider/dashboard</font>", "Dashboard.jsx",
             "One call to <font face='Courier'>/provider/dashboard/</font> "
             "returns trust, the eligible-request inbox, active bookings and "
             "earnings. Deliberately one aggregated endpoint rather than five "
             "round trips on the page a provider opens most."],
            ["<font face='Courier'>/provider/bookings</font>", "Bookings.jsx",
             "The same list and detail components, with provider actions: "
             "start, complete with final price, cancel with a reason."],
            ["<font face='Courier'>/provider/earnings</font>", "Earnings.jsx",
             "Earnings by day, week or month; the ledger with running balance; "
             "outstanding commission payable."],
            ["<font face='Courier'>/provider/profile</font>", "ProfileSetup.jsx",
             "The largest page. Profile fields, service offerings with prices, "
             "service areas from the location tree, the weekly availability "
             "grid, verification document upload with status, and work photos."],
            ["<font face='Courier'>/provider/trust</font>", "TrustPage.jsx",
             "The provider's own score, all six factors with weights and "
             "contributions, and score history from the snapshots &mdash; so a "
             "provider can see exactly what to improve."],
        ],
    }),

    ("h2", "12.4 Route protection"),

    ("p", "<font face='Courier'>RequireRole</font> in "
          "<font face='Courier'>Layout.jsx</font> wraps every protected route: "
          "unauthenticated users are redirected to login, and users without the "
          "required profile are sent away. This is <b>UX, not security</b> "
          "&mdash; it stops a customer landing on a broken provider screen. The "
          "real enforcement is the backend permission classes, which is why the "
          "access-control audit test exists."),

    ("p", "Every route except the landing page is lazy-loaded with "
          "<font face='Courier'>React.lazy</font>, so a visitor who only looks "
          "at the home page never downloads the provider dashboard's code."),

    ("h2", "12.5 Performance work, and what was measured"),

    ("p", "PRD &sect;12.1 sets one number: landing-page LCP under 2.5 s on 4G. "
          "<font face='Courier'>npm run perf:lcp</font> measures the production "
          "build under Chrome's Slow 4G preset (562 ms latency, 1.44 Mbps) with "
          "a 4&times; CPU slowdown &mdash; the same conditions Lighthouse uses "
          "&mdash; over five cold loads, and reports the median. Before M10 the "
          "landing page measured 2.63 s, just over. It now measures 1.58 s."),

    ("table", {
        "cols": ["Change", "Effect"],
        "widths": [0.4, 0.6],
        "rows": [
            ["Prerendered landing hero",
             "LCP 2.45 s &rarr; 1.6 s. The headline paints as soon as HTML and "
             "CSS arrive, before any JavaScript."],
            ["<font face='Courier'>useRoutes</font> instead of "
             "<font face='Courier'>createBrowserRouter</font>",
             "Main bundle 104 KB &rarr; 85 KB gzipped. The data router pulls in "
             "loaders, actions and fetchers that nothing used."],
            ["Static header shell in <font face='Courier'>index.html</font>",
             "First paint 2.4 s &rarr; 1.4 s on every page. The browser lays "
             "out while the JS is still downloading."],
            ["<font face='Courier'>&lt;main&gt;</font> at least one screen tall",
             "Layout shift 0.21 &rarr; at most 0.10. The footer no longer sits "
             "in view and then gets pushed down."],
            ["<font face='Courier'>app.html</font> preloads public chunks",
             "Saves 175&ndash;290 ms on Slow 4G, costs 30&ndash;80 ms on Fast "
             "4G. Kept, because the people on slow connections are the ones who "
             "give up."],
        ],
    }),

    ("callout", {
        "title": "Say this about the pages that miss the target",
        "body": "Pages other than the landing page stay above 2.5 s on Slow 4G. "
                "Each needs HTML, then the main bundle, then its route chunk, "
                "then its data &mdash; and at 562 ms per request that chain is "
                "about 2.2 s before any work happens. Getting them under the "
                "line needs the data in the first response, which means "
                "server-side rendering. That is a Phase 2 architectural "
                "decision, not a tweak. Being able to say exactly why a target "
                "is missed, and what it would cost to hit it, is far stronger "
                "than claiming everything is fast.",
    }),

    ("h2", "12.6 Accessibility"),

    ("p", "PRD &sect;12.4 asks for WCAG 2.1 AA. "
          "<font face='Courier'>e2e/accessibility.spec.js</font> runs axe-core "
          "against every page at 360 px &mdash; signed out, as a customer and "
          "as a provider &mdash; including the open filter panel, the expanded "
          "trust breakdown and the mobile menu. It finds zero violations."),

    ("p", "The first run did not. Grey "
          "<font face='Courier'>slate-400</font> text measures about 2.6:1 "
          "against white, well under the 4.5:1 minimum. Body text now uses "
          "<font face='Courier'>slate-500</font> or darker, and "
          "<font face='Courier'>slate-400</font> survives only on disabled "
          "controls, which WCAG exempts."),

    ("p", "Automated checks cannot see focus, so there are hand-written tests "
          "too: a skip link is the first tab stop on every page, and a test "
          "asserts it becomes visible when focused, moves focus into the page, "
          "and that the next focused element shows an outline. Knowing the "
          "limits of your automated tooling is itself a good answer."),

    ("h2", "12.7 Testing"),

    ("table", {
        "cols": ["Layer", "Tool", "Covers"],
        "widths": [0.2, 0.2, 0.6],
        "rows": [
            ["Unit", "Vitest",
             "The normaliser, formatting helpers, and "
             "<font face='Courier'>client.js</font> including the "
             "single-flight refresh."],
            ["Component", "Testing Library",
             "Trust badge and breakdown, domain widgets, UI primitives."],
            ["End-to-end", "Playwright",
             "Both golden paths in Chromium at 360 px: the customer journey "
             "(register, verify, search, request, review) and the provider "
             "journey (register, set up, accept, complete, get paid)."],
            ["Accessibility", "axe-core in Playwright",
             "Every page in three auth states."],
        ],
    }),

    ("p", "<font face='Courier'>npm run e2e</font> starts its own backend on "
          "port 8100 and Vite on 5174, runs everything, then deletes the test "
          "users it created via "
          "<font face='Courier'>e2e/cleanup.py</font>. In CI, failures upload "
          "Playwright traces as artifacts and are reported as GitHub "
          "annotations on the failing line."),

    ("pagebreak", None),
)


# ======================================================================
# DEPLOYMENT & CI
# ======================================================================

add(
    ("h1", "13. Deployment and CI"),

    ("h2", "13.1 Two routes, both honest"),

    ("p", "The site is not deployed yet, and the documentation says so. There "
          "are two prepared routes, both checked locally, and each guide marks "
          "which parts remain unverified. Saying that plainly is better than an "
          "unsupportable claim an interviewer can puncture in one question."),

    ("table", {
        "cols": ["Route", "Shape", "Best for"],
        "widths": [0.2, 0.46, 0.34],
        "rows": [
            ["Render", "Driven by <font face='Courier'>render.yaml</font>: "
                       "managed PostgreSQL, a web service for the API, cron "
                       "jobs for the scheduled work, and a static site for the "
                       "React build.",
             "No Linux administration. The simpler route."],
            ["Ubuntu VPS", "Nginx &rarr; gunicorn via a unix socket, systemd "
                           "for supervision, cron for scheduled jobs, "
                           "<font face='Courier'>pg_dump</font> backups with a "
                           "restore check.",
             "Full control, and it demonstrates the ops knowledge."],
        ],
    }),

    ("h2", "13.2 What changes in production settings"),

    ("bullets", [
        "<font face='Courier'>DEBUG=False</font>, real "
        "<font face='Courier'>ALLOWED_HOSTS</font>, SMTP email backend.",
        "<font face='Courier'>OTP_ECHO_TO_LOG=False</font> &mdash; codes never "
        "reach the log.",
        "WhiteNoise inserted directly after "
        "<font face='Courier'>SecurityMiddleware</font>, with the compressed "
        "manifest static storage for hashed, far-future-cacheable filenames.",
        "The full HTTPS header set: SSL redirect, one-year HSTS with preload "
        "and subdomains, <font face='Courier'>SECURE_PROXY_SSL_HEADER</font> so "
        "Django trusts the proxy's protocol, nosniff, "
        "<font face='Courier'>X-Frame-Options: DENY</font>, secure cookies.",
        "Optional S3-compatible object storage, split into two buckets' worth "
        "of configuration: public media with "
        "<font face='Courier'>querystring_auth=False</font>, and private "
        "verification documents with signed URLs expiring in 300 seconds.",
    ]),

    ("p", "That storage split is the same public/private separation as "
          "local disk, expressed for object storage &mdash; the abstraction "
          "held when the backend changed, which is the point of putting it "
          "behind <font face='Courier'>STORAGES</font> in the first place."),

    ("h2", "13.3 CI"),

    ("p", "Four GitHub Actions jobs run on every push and pull request:"),

    ("numbers", [
        "<b>backend</b> &mdash; against real PostgreSQL 18: a "
        "<font face='Courier'>makemigrations --check</font> so a model change "
        "without a migration fails the build; "
        "<font face='Courier'>check --deploy --fail-level WARNING</font> "
        "against the production settings module; then the full suite with "
        "<font face='Courier'>-W error::DeprecationWarning</font>, so a "
        "deprecation becomes a failure now rather than a surprise at the next "
        "Django upgrade.",

        "<b>frontend</b> &mdash; ESLint with zero warnings allowed, Vitest, "
        "and a production build.",

        "<b>e2e</b> &mdash; a real backend with seeded demo data, a real "
        "Chromium, both golden paths and the accessibility scan. Traces upload "
        "on failure.",

        "<b>audit</b> &mdash; <font face='Courier'>pip-audit</font> and "
        "<font face='Courier'>npm audit</font>.",
    ]),

    ("pagebreak", None),
)


# ======================================================================
# INTERVIEW PREPARATION
# ======================================================================

add(
    ("h1", "14. Interview preparation: how to present this"),

    ("h2", "14.1 The 90-second pitch"),

    ("p", "Memorise the shape of this, not the words. It works because it "
          "leads with a problem, not a stack."),

    ("callout", {
        "title": "The pitch",
        "body": "&lsquo;ServoraBd is a local services marketplace &mdash; "
                "electricians, plumbers &mdash; for Dhaka. The booking flow is "
                "a solved problem, so what I actually built it to explore is "
                "the trust model.<br/><br/>"
                "Star ratings are broken in two ways. They cluster: almost "
                "everyone sits between 4.5 and 5.0, so they carry almost no "
                "information. And they only measure jobs that were "
                "<i>completed</i> &mdash; a provider who accepts ten bookings "
                "and abandons eight can hold a perfect score.<br/><br/>"
                "So instead of one number people give you, I compute six from "
                "things the platform observes: verification depth, job volume, "
                "completion rate, cancellation discipline, responsiveness and "
                "review quality. Completion and reviews use Bayesian smoothing "
                "so one good job does not look like a track record. "
                "Cancellations are weighted by notice given &mdash; an hour "
                "before costs four times what two days before costs &mdash; "
                "and decay with a 180-day half-life.<br/><br/>"
                "In my demo data there are two providers rated 4.9 and 4.8. "
                "Their trust scores are 84 and 53, because the second one "
                "abandons 40% of what he accepts. That gap is the whole "
                "project.<br/><br/>"
                "It is Django REST Framework and PostgreSQL with a React "
                "client, 569 backend tests, and search runs in 100 ms at p95 "
                "against ten thousand providers.&rsquo;",
    }),

    ("h2", "14.2 Five things to steer the conversation toward"),

    ("numbers", [
        "<b>The trust algorithm.</b> Bayesian smoothing, logarithmic volume, "
        "damage-weighted decay, penalties outside the weighted sum. Every "
        "choice has a reason and an anti-gaming purpose.",

        "<b>The service layer with its three rules.</b> IDs not instances, "
        "never touch request, idempotent &mdash; and the reason: a Celery "
        "migration becomes one line per call site.",

        "<b>The access-control audit test.</b> A test generated from the URL "
        "conf that fails if any new endpoint forgets its permission class.",

        "<b>The rate-limit bypass and its verification command.</b> A real "
        "vulnerability, understood, fixed, and then made checkable against a "
        "live deployment.",

        "<b>The single-flight token refresh.</b> A subtle frontend bug "
        "&mdash; token rotation plus concurrent requests equals random "
        "logouts &mdash; found, fixed and tested.",
    ]),

    ("h2", "14.3 The weaknesses &mdash; own them before they are found"),

    ("p", "Every one of these will be spotted by a good interviewer. Having a "
          "considered answer turns each from a weakness into evidence of "
          "judgement. The pattern is always the same: acknowledge, explain the "
          "trade-off, state the upgrade path."),

    ("table", {
        "cols": ["They will say", "You say"],
        "widths": [0.32, 0.68],
        "rows": [
            ["&lsquo;It is not deployed.&rsquo;",
             "&lsquo;Correct, and the README says so. Both routes are "
             "prepared &mdash; a Render blueprint and a full Ubuntu guide with "
             "Nginx, gunicorn, systemd, cron and backups &mdash; and each "
             "marks which parts I have not verified live. I would rather say "
             "that than claim production experience I do not have.&rsquo;"],

            ["&lsquo;No Celery. That does not scale.&rsquo;",
             "&lsquo;Right, and it is deliberate. Phase 1 load does not "
             "justify a broker and a worker to supervise. The PRD records the "
             "thresholds that would, and every service takes IDs rather than "
             "instances, never touches request and is idempotent &mdash; so "
             "adopting one is a one-line change per call site, not a "
             "rewrite.&rsquo;"],

            ["&lsquo;No caching layer.&rsquo;",
             "&lsquo;Search is 100 ms at p95 against ten thousand providers, "
             "so the cache would be solving a problem I do not have yet. The "
             "obvious first target is the catalogue, which barely changes; "
             "trust scores are already denormalised onto the provider row, "
             "which is the caching that actually mattered.&rsquo;"],

            ["&lsquo;Why not TypeScript?&rsquo;",
             "&lsquo;A recorded decision, with three things standing in: "
             "frozen constants so a typo throws, a normaliser layer so a "
             "backend rename breaks one file, and PropTypes on everything "
             "touching money, state and trust. On a team I would use "
             "TypeScript; I wanted to prove I could hold the invariants "
             "without it.&rsquo;"],

            ["&lsquo;Distance is not real geospatial.&rsquo;",
             "&lsquo;It is Manhattan distance in degrees. Within one city the "
             "error is negligible, it needs no PostGIS extension, and the sort "
             "stays in the database. PostGIS with a GiST index is the upgrade "
             "if it goes national.&rsquo;"],

            ["&lsquo;Cash only. No payment gateway.&rsquo;",
             "&lsquo;Cash is how the market actually works in Dhaka today, so "
             "modelling it honestly was the right first step. The model "
             "already has bKash, Nagad and card methods and gateway reference "
             "fields; the interesting part is the two-sided amount check that "
             "flags a mismatch for an admin instead of trusting one "
             "side.&rsquo;"],

            ["&lsquo;Trust weights are arbitrary.&rsquo;",
             "&lsquo;They are judgement, not data &mdash; there is no "
             "historical dataset to fit them to. What I did instead is make "
             "them explicit and versioned: every snapshot stores its "
             "algo_version, so when there is real outcome data, weights can be "
             "refitted and old scores stay interpretable. The formula shapes "
             "are the defensible part; the exact numbers are a starting "
             "point.&rsquo;"],

            ["&lsquo;No notifications.&rsquo;",
             "&lsquo;Correct &mdash; FR-8 is unbuilt, and the frontend README "
             "says the UI was left out rather than faked, because there is no "
             "backend to render.&rsquo;"],

            ["&lsquo;Only one region.&rsquo;",
             "&lsquo;The location model is a generic self-referential tree "
             "with three levels; adding Chittagong is seed data, not a schema "
             "change.&rsquo;"],
        ],
    }),

    ("pagebreak", None),

    # ------------------------------------------------------------------
    ("h1", "15. Question bank with model answers"),

    ("h2", "15.1 Architecture"),

    ("h3", "Q: Walk me through your architecture."),

    ("p", "<b>A:</b> Django REST Framework backend, React client, PostgreSQL. "
          "The backend is nine apps by domain, and each app follows the same "
          "six-file split: models for shape and constraints, selectors for "
          "reads, services for writes and business rules, serializers for "
          "validation and shaping, views for HTTP only, permissions for "
          "access. A view parses input, checks permission, calls one service "
          "and returns a response &mdash; if there is an "
          "<font face='Courier'>if</font> about business rules in a view, that "
          "is a bug. The frontend mirrors it: a transport layer, a normaliser "
          "so no component ever reads raw API JSON, an endpoint module, and "
          "then pages."),

    ("h3", "Q: Why separate selectors from services?"),

    ("p", "<b>A:</b> Different concerns. Selectors own read performance "
          "&mdash; all the "
          "<font face='Courier'>select_related</font> and "
          "<font face='Courier'>prefetch_related</font> that stop N+1 queries "
          "&mdash; and never write. Services own correctness and write. "
          "Separating them means I can optimise a query without reading "
          "business logic, and change a business rule without breaking a query "
          "plan. It also makes the write surface small and easy to audit."),

    ("h3", "Q: Why nine apps rather than one?"),

    ("p", "<b>A:</b> They are split on domain boundaries, not layer "
          "boundaries, and the dependencies mostly run one way &mdash; "
          "bookings depends on accounts and catalogue, not the reverse. Where "
          "a cycle would appear, the import is deferred inside the function: "
          "bookings imports the trust engine inside "
          "<font face='Courier'>_recompute_trust</font> rather than at module "
          "level. The payoff is that I can read the payments app without "
          "knowing anything about reviews."),

    ("h2", "15.2 Database"),

    ("h3", "Q: How do you prevent two providers accepting the same request?"),

    ("p", "<b>A:</b> <font face='Courier'>select_for_update()</font> inside "
          "<font face='Courier'>@transaction.atomic</font>. The first "
          "transaction takes a row-level write lock on the request; the second "
          "blocks at that line until the first commits, then re-reads and "
          "finds the state is already <font face='Courier'>accepted</font>, "
          "and returns a clean domain error. It is pessimistic locking, which "
          "is right here because the contention window is milliseconds and "
          "the cost of getting it wrong is two providers turning up."),

    ("h3", "Q: Where are your database constraints, and why not just validate in code?"),

    ("p", "<b>A:</b> Application validation can be bypassed &mdash; a "
          "management command, a shell session, a future bulk import. So the "
          "invariants that must never break live in the database. A check "
          "constraint that a user has a phone or an email. A check constraint "
          "that a non-city location has a parent. Partial unique indexes so "
          "there is at most one cash payment per booking and at most one "
          "earning, commission and cash-retained entry per booking. If a bug "
          "ever called the payment service twice, the database refuses rather "
          "than double-paying."),

    ("h3", "Q: How did you handle N+1 queries?"),

    ("p", "<b>A:</b> In the selectors, and it is measured rather than assumed. "
          "Search uses "
          "<font face='Courier'>select_related('user')</font> for the "
          "one-to-one and a "
          "<font face='Courier'>Prefetch</font> on service areas with their "
          "locations and parents, because the result card shows the area name "
          "and its parent. The benchmark command times it: 100 ms at p95 "
          "against 10,018 providers, against a 400 ms target."),

    ("h3", "Q: Why denormalise the counters onto ProviderProfile?"),

    ("p", "<b>A:</b> Because the trust engine reads them for every provider "
          "every night. Deriving "
          "<font face='Courier'>jobs_completed</font> by counting bookings "
          "would make the nightly recompute a ten-thousand-provider join. "
          "They are maintained with atomic "
          "<font face='Courier'>F()</font> expressions so concurrent updates "
          "cannot lose an increment, and "
          "<font face='Courier'>reconcile_earnings</font> checks the derived "
          "data against the source nightly. The trade-off is accepted "
          "consciously, with a check that catches drift."),

    ("h2", "15.3 Security"),

    ("h3", "Q: Tell me about a security issue you found in your own code."),

    ("p", "<b>A:</b> The best one is the rate-limit bypass. DRF identifies "
          "clients for throttling from "
          "<font face='Courier'>X-Forwarded-For</font>, but that is a request "
          "header anyone can send. With the default configuration an attacker "
          "sends a different forged value per login attempt and every one looks "
          "like a new client, so the five-per-15-minutes limit is effectively "
          "unlimited &mdash; and so is the OTP limit. The fix is "
          "<font face='Courier'>NUM_PROXIES</font>, set from an environment "
          "variable, so DRF counts from the right-hand end of the header and "
          "ignores what the client prepended. Because it depends on the "
          "deployment topology rather than the code, I also wrote a command "
          "that probes a live deployment with a forged header and fails if the "
          "limiter sees it."),

    ("h3", "Q: How do you store national ID documents?"),

    ("p", "<b>A:</b> On a separate storage backend rooted outside anything the "
          "web server serves, and its "
          "<font face='Courier'>url()</font> method raises "
          "<font face='Courier'>NotImplementedError</font> rather than "
          "returning a path. So if anyone ever writes a serializer that tries "
          "to expose it, the code crashes in a test instead of leaking. Admins "
          "view them through an authenticated endpoint that streams the file "
          "with <font face='Courier'>no-store</font>, "
          "<font face='Courier'>nosniff</font>, and a CSP of "
          "<font face='Courier'>default-src 'none'; sandbox</font>. Uploads are "
          "validated by magic bytes, not extension &mdash; that was an M10 "
          "finding; the first version trusted the extension, which let an HTML "
          "file be stored as a .jpg. And files are purged 90 days after review "
          "while the decision record is kept."),

    ("h3", "Q: How do you know every endpoint is protected?"),

    ("p", "<b>A:</b> A test proves it rather than a convention. It walks "
          "Django's URL resolver at runtime, collects every route under "
          "<font face='Courier'>/api/v1/</font>, and asserts that anything not "
          "on a 15-entry public allowlist returns 401 to an anonymous caller "
          "and that every admin route returns 403 to an ordinary customer. It "
          "also asserts the allowlist names only routes that still exist, and "
          "that at least 60 routes were found, so it cannot pass by finding "
          "nothing. Add an endpoint and forget its permission class and CI "
          "fails."),

    ("h3", "Q: Why 404 rather than 403 for someone else's booking?"),

    ("p", "<b>A:</b> A 403 confirms the object exists, which lets an attacker "
          "enumerate valid ids. Ownership is part of the "
          "<font face='Courier'>filter()</font> that fetches the row, so a "
          "wrong owner simply finds nothing. It falls out of the structure "
          "rather than needing anyone to remember it."),

    ("h3", "Q: Explain your OTP implementation."),

    ("p", "<b>A:</b> Six digits from "
          "<font face='Courier'>secrets.randbelow</font>, stored only as a "
          "SHA-256 hash of phone plus code plus "
          "<font face='Courier'>SECRET_KEY</font>. The phone is in the hash so "
          "a code for one number cannot verify another; the secret acts as a "
          "pepper so a database dump cannot be brute-forced offline. "
          "Comparison is <font face='Courier'>secrets.compare_digest</font>, "
          "constant-time, so response timing does not leak how much of the code "
          "was right. Three rate limits: three sends per phone per hour, five "
          "verify attempts per code, and a DRF per-IP throttle &mdash; per-"
          "phone and per-IP are independent axes and you need both. And the "
          "attempt counter is committed in its own transaction before the "
          "exception is raised, because otherwise the rollback would undo the "
          "increment and the attacker would get unlimited guesses."),

    ("h2", "15.4 The trust algorithm"),

    ("h3", "Q: Why Bayesian smoothing? Explain it to a non-technical person."),

    ("p", "<b>A:</b> Without it, a provider who took one job and finished it "
          "scores 100% completion &mdash; a perfect score on one data point. "
          "Smoothing adds ten imaginary jobs at the platform average of 90%, so "
          "a new provider starts near 90 and moves toward their real rate as "
          "evidence accumulates. One of one becomes 90.9 instead of 100; fifty "
          "of fifty becomes 98.3. It is symmetric, which is the fairness "
          "argument: it protects a newcomer from one unlucky job exactly as "
          "much as it stops one lucky job looking like a record. Non-"
          "technically: <i>we do not trust a small sample, in either "
          "direction.</i>"),

    ("h3", "Q: Someone games your system. How?"),

    ("p", "<b>A:</b> Every formula is a defence against a specific attack, so "
          "let me go through them. Create an account and do one perfect job "
          "&mdash; blocked by the Bayesian priors and the New tier below three "
          "jobs. Farm tiny jobs for volume &mdash; F2 is logarithmic and "
          "saturates at 100. Accept everything and deliver selectively &mdash; "
          "F3's denominator is jobs <i>accepted</i>, not completed. Cancel late "
          "but often and hide behind reviews &mdash; F4 weights a no-show six "
          "times a two-day-notice cancellation and the curve is convex. Wait "
          "out a bad incident &mdash; decay is slow, 180 and 365-day "
          "half-lives, and penalties sit outside the weighted sum so they "
          "cannot be diluted. Fake reviews &mdash; a review needs a completed "
          "booking, which needs a real request, acceptance and confirmation. "
          "The genuinely unsolved one is collusion: two accounts booking each "
          "other. That needs graph analysis on the booking network, and it is "
          "honestly Phase 2."),

    ("h3", "Q: Why are penalties applied after the weighted sum?"),

    ("p", "<b>A:</b> Because a weighted average dilutes. If an upheld dispute "
          "were one component of the average, a provider with excellent numbers "
          "elsewhere would reduce it to almost nothing. A flat subtraction "
          "cannot be diluted &mdash; one serious incident costs the same "
          "fifteen points whether you are excellent or mediocre. That ordering "
          "is a deliberate statement about how seriously the platform takes "
          "upheld complaints."),

    ("h3", "Q: How would you validate that the weights are right?"),

    ("p", "<b>A:</b> I would not claim they are. They are judgement, because "
          "there is no historical outcome data to fit them to. What I did "
          "instead is make them explicit, keep them in one dictionary, version "
          "them, and store the version on every snapshot &mdash; so when there "
          "is real data about which providers customers rebook and which "
          "generate complaints, I can fit the weights properly and historical "
          "scores stay interpretable under the version that produced them. The "
          "formula <i>shapes</i> are the defensible part; the exact "
          "coefficients are a starting point I have made easy to change."),

    ("h3", "Q: Why recompute nightly if it is event-driven?"),

    ("p", "<b>A:</b> Because time decay moves when nothing happens. A "
          "cancellation ages past its half-life and a review loses weight "
          "whether or not the provider does anything. Without the nightly "
          "batch, an inactive provider's score would be frozen at whatever it "
          "was on their last job. It streams primary keys with "
          "<font face='Courier'>.values_list('pk', flat=True).iterator()</font> "
          "so memory stays flat, and takes 175 seconds for ten thousand "
          "providers."),

    ("h2", "15.5 Frontend"),

    ("h3", "Q: Where do you store the JWT, and why?"),

    ("p", "<b>A:</b> The access token is in memory only; only the refresh "
          "token is persisted to localStorage. That is a considered trade-off "
          "rather than the textbook answer. HttpOnly cookies would be safer "
          "against XSS, but they bring CSRF back, and the app has no XSS "
          "surface: React escapes by default, there is no "
          "<font face='Courier'>dangerouslySetInnerHTML</font>, and uploads are "
          "magic-byte validated. Keeping the access token out of storage limits "
          "the window if that reasoning ever turns out to be wrong, and the "
          "short 15-minute lifetime limits it further."),

    ("h3", "Q: Tell me about a hard bug you fixed."),

    ("p", "<b>A:</b> Random logouts. The backend rotates refresh tokens and "
          "blacklists the old one after rotation, which is good security. But "
          "when three components mounted at once with an expired access token, "
          "all three fired a refresh. The first succeeded and blacklisted the "
          "token; the other two then presented a blacklisted token and failed, "
          "clearing the session. The fix is single-flight: hold the in-flight "
          "promise in a module-level variable and return it to every concurrent "
          "caller, so they all await the same refresh. It is four lines, and "
          "the test asserts that two concurrent calls produce exactly one "
          "network request."),

    ("h3", "Q: How did you get LCP under 2.5 seconds?"),

    ("p", "<b>A:</b> By measuring first. A script runs the production build "
          "under Chrome's Slow 4G preset with a 4&times; CPU slowdown &mdash; "
          "Lighthouse's mobile conditions &mdash; five cold loads, median "
          "reported. It started at 2.63 s. Prerendering the landing hero to "
          "static HTML at build time took it to about 1.6 s, because the "
          "headline paints as soon as HTML and CSS arrive; React then hydrates "
          "with identical markup, so layout shift stays at zero. Switching from "
          "<font face='Courier'>createBrowserRouter</font> to "
          "<font face='Courier'>useRoutes</font> cut 19 KB gzipped that was "
          "loaders and fetchers nothing used. A static header shell in the HTML "
          "moved first paint on every page. Final number is 1.58 s. I also "
          "tried preloading the current route's chunk from "
          "<font face='Courier'>main.jsx</font> and dropped it &mdash; only "
          "about 40 ms, because the bundle has to be evaluated first."),

    ("h3", "Q: Why not TypeScript, really?"),

    ("p", "<b>A:</b> Partly to prove I could hold the invariants without it. "
          "The three mechanisms are frozen constant objects so a typo in a "
          "state name throws instead of rendering nothing, a normaliser layer "
          "so a backend field rename breaks one file and its tests rather than "
          "six screens, and PropTypes on every component touching money, state "
          "or trust. That is also why React is pinned at 18.3 &mdash; React 19 "
          "ignores propTypes on function components silently. On a team, I "
          "would use TypeScript."),

    ("h2", "15.6 Testing and process"),

    ("h3", "Q: What do your 569 tests actually cover?"),

    ("p", "<b>A:</b> Four layers. Pure-function tests on the trust factors "
          "&mdash; <font face='Courier'>factors.py</font> has no Django "
          "imports, so those run in milliseconds against a dataclass. Service "
          "tests for business rules, including the concurrency paths. API tests "
          "for status codes, permissions and error envelopes. And cross-cutting "
          "audits: the access-control test generated from the URL conf, and the "
          "ledger reconciliation. The two PRD worked examples are asserted "
          "exactly &mdash; 84.19 and 53.48 &mdash; so a change to any weight "
          "fails the suite and tells me the documentation has gone stale."),

    ("h3", "Q: What would you do differently?"),

    ("p", "<b>A:</b> Three things. I would write the access-control audit test "
          "in the first week rather than during hardening, because it would "
          "have caught things earlier and cost nothing. I would deploy at M3 "
          "instead of M10 &mdash; deploying early surfaces configuration "
          "problems while there is little to configure. And I would build the "
          "notification app, because several flows have an obvious hole where a "
          "notification belongs and users currently have to poll the page."),

    ("h3", "Q: What is the next thing you would build?"),

    ("p", "<b>A:</b> Notifications, because it is the largest missing piece "
          "and every other feature is degraded without it. Then a real "
          "deployment, then a payment gateway now that the model is ready for "
          "it. Further out, the interesting problem is collusion detection "
          "&mdash; the one gaming vector the current algorithm does not "
          "address, which needs graph analysis of the booking network rather "
          "than another factor."),

    ("pagebreak", None),

    # ------------------------------------------------------------------
    ("h1", "16. Quick reference"),

    ("h2", "16.1 Numbers to have memorised"),

    ("table", {
        "cols": ["Thing", "Number"],
        "widths": [0.62, 0.38],
        "rows": [
            ["Trust factors", "6"],
            ["Weights", "20 / 15 / 20 / 15 / 10 / 20"],
            ["Completion prior", "k = 10, &mu; = 0.90"],
            ["Review prior", "k = 5, &mu; = 4.2"],
            ["Volume saturation", "100 jobs"],
            ["Cancellation half-life", "180 days"],
            ["Review half-life", "365 days"],
            ["Cancellation weights", "1&times; / 2&times; / 4&times; / 6&times; no-show"],
            ["Cancellation exponent", "1.5"],
            ["Access token / refresh token", "15 minutes / 14 days"],
            ["OTP TTL / sends per hour / attempts", "5 minutes / 3 / 5"],
            ["Login throttle", "5 per 15 minutes"],
            ["Request expiry / auto-confirm", "24 hours / 72 hours"],
            ["Review window / edit window / reveal", "30 days / 24 hours / 14 days"],
            ["Document retention", "90 days after review"],
            ["Commission", "12%"],
            ["Backend tests", "569"],
            ["Search p95 / trust recompute", "100 ms / 175 s"],
            ["Landing LCP, Slow 4G", "1.58 s"],
        ],
    }),

    ("h2", "16.2 Files to be able to open instantly"),

    ("table", {
        "cols": ["If they ask about", "Open"],
        "widths": [0.4, 0.6],
        "rows": [
            ["The trust algorithm",
             "<font face='Courier'>backend/apps/trust/factors.py</font>"],
            ["How trust reaches the database",
             "<font face='Courier'>backend/apps/trust/engine.py</font>"],
            ["The booking lifecycle",
             "<font face='Courier'>backend/apps/bookings/state_machine.py</font>"],
            ["Concurrency",
             "<font face='Courier'>backend/apps/bookings/services.py</font>, "
             "<font face='Courier'>respond_to_request</font>"],
            ["Search performance",
             "<font face='Courier'>backend/apps/providers/search.py</font>"],
            ["Security auditing",
             "<font face='Courier'>backend/apps/common/tests/test_access_control.py</font>"],
            ["The rate-limit fix",
             "<font face='Courier'>backend/apps/operations/management/commands/check_proxy_count.py</font>"],
            ["Private document storage",
             "<font face='Courier'>backend/apps/common/storage.py</font>"],
            ["Upload validation",
             "<font face='Courier'>backend/apps/providers/serializers.py</font>, "
             "<font face='Courier'>VerificationUploadSerializer</font>"],
            ["Money correctness",
             "<font face='Courier'>backend/apps/payments/models.py</font> and "
             "<font face='Courier'>services.py</font>"],
            ["The token refresh bug",
             "<font face='Courier'>frontend/src/api/client.js</font>"],
            ["Error handling",
             "<font face='Courier'>backend/apps/common/exceptions.py</font>"],
        ],
    }),

    ("h2", "16.3 Sentences worth having ready"),

    ("bullets", [
        "&lsquo;The booking flow is a solved problem. What I built this to "
        "explore is the trust model.&rsquo;",

        "&lsquo;Star ratings only measure jobs that were completed. A provider "
        "who abandons eight of ten can hold a perfect score.&rsquo;",

        "&lsquo;4.9 versus 4.8 on stars; 84 versus 53 on trust. That gap is "
        "the project.&rsquo;",

        "&lsquo;Bayesian smoothing means we do not trust a small sample, in "
        "either direction.&rsquo;",

        "&lsquo;Penalties are outside the weighted sum, because an average "
        "dilutes and a subtraction cannot be diluted.&rsquo;",

        "&lsquo;Every service takes IDs, never touches request, and is "
        "idempotent &mdash; so adopting a queue is one line per call "
        "site.&rsquo;",

        "&lsquo;The access-control test is generated from the URL conf, so a "
        "new endpoint without a permission class fails CI.&rsquo;",

        "&lsquo;The private storage backend raises on url() rather than "
        "returning a path, so a leak is a crash in a test.&rsquo;",

        "&lsquo;It is not deployed, and the README says so &mdash; both routes "
        "are prepared and each marks what I have not verified live.&rsquo;",
    ]),

    ("callout", {
        "title": "The habit that makes all of this land",
        "body": "For every answer, give the decision, then the reason, then "
                "the trade-off you accepted. &lsquo;I used "
                "<font face='Courier'>select_for_update</font> &mdash; "
                "pessimistic locking, because the contention window is "
                "milliseconds and two providers arriving at one house is worse "
                "than a few blocked requests.&rsquo; That three-part shape is "
                "what separates someone who followed a tutorial from someone "
                "who made choices.",
    }),
)
