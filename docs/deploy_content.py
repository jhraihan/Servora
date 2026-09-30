# -*- coding: utf-8 -*-
"""
Content source for the ServoraBd Render deployment steps.

Same (kind, payload) format as guide_content.py, rendered by build_deploy.py.
"""

TITLE = "ServoraBd"
SUBTITLE = "Local Service Marketplace"
DOC_TYPE = "Render Deployment Steps"
VERSION = "1.0"
STATUS = "Free tier / temporary database"
DATE = "30 September 2026"
AUTHOR = "Jahid H. R."

PITCH = "Free plan, temporary database. Eight steps."

DOC = []


def add(*items):
    DOC.extend(items)


add(
    ("h1", "Deploy to Render"),

    ("h2", "1. Push to GitHub"),

    ("code", [
        "git add .",
        "git commit -m \"Add free-tier Render blueprint\"",
        "git push origin main",
    ]),

    ("h2", "2. Create the services"),

    ("numbers", [
        "<font face='Courier'>dashboard.render.com</font> &gt; <b>New</b> &gt; "
        "<b>Blueprint</b>",
        "Pick your repository.",
        "Set <b>Blueprint file</b> to "
        "<font face='Courier'>render-free.yaml</font> &mdash; not "
        "<font face='Courier'>render.yaml</font>, which is paid.",
        "<b>Apply</b>. Expect 3 free services and no price. Wait for the "
        "build.",
    ]),

    ("h2", "3. Check the API"),

    ("p", "Open <font face='Courier'>https://servorabd-api.onrender.com"
          "/healthz/</font> &mdash; expect "
          "<font face='Courier'>{\"status\": \"ok\", \"database\": \"ok\"}</font>. "
          "First load takes ~50s while the service wakes."),

    ("h2", "4. Seed the data"),

    ("p", "Copy the <b>External Database URL</b> from "
          "<b>servorabd-db</b>, then from "
          "<font face='Courier'>backend/</font>:"),

    ("code", [
        "$env:DATABASE_URL = \"<External Database URL>\"",
        "$env:DJANGO_SETTINGS_MODULE = \"config.settings.prod\"",
        "$env:SECRET_KEY = \"one-off\"",
        "python manage.py seed_catalogue",
        "python manage.py createsuperuser",
    ]),

    ("h2", "5. Fix the rewrites if renamed"),

    ("p", "If Render named your API anything other than "
          "<font face='Courier'>servorabd-api</font>, edit the four "
          "<font face='Courier'>destination</font> lines in "
          "<font face='Courier'>render-free.yaml</font> to the real hostname, "
          "then push. Otherwise the site loads but no data arrives."),

    ("h2", "6. Add SMTP if people must log in"),

    ("p", "Login codes are e-mailed. Without these four keys the site works "
          "but <b>nobody can register or log in</b>. Set them on "
          "<b>servorabd-api &gt; Environment</b> (Gmail needs an app "
          "password, not your normal one):"),

    ("table", {
        "cols": ["Key", "Value"],
        "widths": [0.34, 0.66],
        "rows": [
            ["<font face='Courier'>EMAIL_HOST</font>",
             "<font face='Courier'>smtp.gmail.com</font>"],
            ["<font face='Courier'>EMAIL_HOST_USER</font>",
             "your Gmail address"],
            ["<font face='Courier'>EMAIL_HOST_PASSWORD</font>",
             "16-char app password, no spaces"],
            ["<font face='Courier'>DEFAULT_FROM_EMAIL</font>",
             "same Gmail address"],
        ],
    }),

    ("h2", "7. Verify the site"),

    ("p", "At <font face='Courier'>https://servorabd-web.onrender.com</font>: "
          "the landing page loads, <font face='Courier'>/providers</font> "
          "loads with data, and <font face='Courier'>/admin/</font> shows a "
          "<b>styled</b> Django login."),

    ("h2", "8. Set a 30-day reminder"),

    ("p", "The free database is <b>deleted after 30 days</b> and cannot be "
          "upgraded in place. Before then, dump it and move to "
          "<font face='Courier'>render.yaml</font>:"),

    ("code", [
        "pg_dump --format=custom --no-owner \\",
        "        --dbname=\"<External Database URL>\" --file=servorabd.dump",
    ]),

    ("h2", "If something breaks"),

    ("table", {
        "cols": ["Symptom", "Cause"],
        "widths": [0.40, 0.60],
        "rows": [
            ["First visit takes ~50s", "Free service waking. Expected."],
            ["Lists are empty",
             "<font face='Courier'>seed_catalogue</font> not run (step 4)."],
            ["No login code arrives", "No SMTP (step 6)."],
            ["Site loads, no data",
             "Rewrite hostname wrong (step 5)."],
            ["Deep link 404s",
             "Missing <font face='Courier'>/*</font> rewrite to "
             "<font face='Courier'>app.html</font>."],
            ["<font face='Courier'>/admin/</font> unstyled",
             "<font face='Courier'>collectstatic</font> failed; check build "
             "log."],
            ["<font face='Courier'>Bad Request (400)</font>",
             "Set <font face='Courier'>ALLOWED_HOSTS</font> to your API "
             "hostname."],
            ["DB errors after ~a month",
             "Free database expired (step 8)."],
            ["Uploads vanish on deploy",
             "No persistent disk on free. Expected."],
        ],
    }),

    ("h2", "Not running on free"),

    ("p", "Cron services need a paid plan, so the seven scheduled jobs never "
          "fire: bookings will not auto-expire and reviews will not "
          "auto-reveal. Run one by hand with the step 4 variables set:"),

    ("code", [
        "python manage.py run_scheduled_jobs --only reveal_reviews",
    ]),
)
