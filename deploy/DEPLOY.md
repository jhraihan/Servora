# Deploying ShebaLocal

This runbook takes a fresh Ubuntu server to a running ShebaLocal at `https://shebalocal.example.com`.
Replace that domain everywhere with yours.

> **Status:** everything in `deploy/` was written and checked on a development machine, but
> **has not yet been run on a real server.** The parts that were verified are listed under
> [What has and has not been verified](#what-has-and-has-not-been-verified). Expect to fix small
> things the first time through, and do the first deployment on a server with no real users.

## What runs where

```
Browser ──HTTPS──> Nginx ─┬─ /                 dist/index.html (landing page, hero prerendered)
                          ├─ /assets/*          hashed JS and CSS, cached for a year
                          ├─ every other page   dist/app.html (the React app)
                          ├─ /api/*, /admin/*   ──unix socket──> gunicorn (3 workers) ──> Django ──> PostgreSQL
                          ├─ /static/*          Django admin CSS and JS
                          └─ /media/*.jpg|png|webp   public photos only
cron ──> deploy/scripts/manage.sh <job>   (the 7 scheduled jobs, backups, a weekly restore check)
```

Verification documents live in `backend/private_media/`. Nginx has no route to that directory,
and it must never be given one.

| Path on the server | What it is | Owner, mode |
| --- | --- | --- |
| `/srv/shebalocal` | this repository | `sheba` |
| `/var/lib/sheba` | the `sheba` user's home (npm and pip caches) | `sheba` |
| `/srv/shebalocal/backend/.env` | production settings and secrets | `sheba`, `600` |
| `/srv/shebalocal/backend/media` | public photos | `sheba:www-data`, `2770` |
| `/srv/shebalocal/backend/private_media` | ID documents | `sheba`, `700` |
| `/run/shebalocal/gunicorn.sock` | app socket, created by systemd | `sheba:www-data` |
| `/var/log/shebalocal` | cron and backup logs | `sheba` |
| `/var/backups/shebalocal` | nightly database and media backups | `sheba`, `700` |

## 1. Server and packages

Use **Ubuntu 24.04 LTS** with at least 2 GB of RAM. It ships Python 3.12, the same version the
project is developed and tested on. Point your domain's DNS `A` record at the server first, because
the certificate step needs it.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx python3.12-venv certbot rsync

sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install -y postgresql-18

curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
```

PostgreSQL 18 comes from the official PostgreSQL apt repository, because Ubuntu's own repository
has an older version. Node is only needed to build the frontend.

## 2. User and directories

```bash
sudo adduser --system --group --home /var/lib/sheba --shell /bin/bash sheba
sudo mkdir -p /srv/shebalocal /var/log/shebalocal /var/backups/shebalocal
sudo chown sheba:sheba /srv/shebalocal /var/log/shebalocal /var/backups/shebalocal
sudo chmod 700 /var/backups/shebalocal
```

## 3. Database

The app connects as its own role, which owns the database and nothing else. It can create
databases only so the weekly restore check can build and drop a scratch copy.

```bash
sudo -u postgres createuser --createdb --pwprompt sheba
sudo -u postgres createdb --owner sheba shebalocal
```

**Do not install any PostgreSQL extensions.** The app does not use any. An extension that only a
superuser can create (such as `earthdistance`) would end up in every backup, and restoring that
backup would then need a superuser. The restore check in step 9 exists to catch exactly that.

## 4. Code and Python environment

```bash
sudo -u sheba git clone https://github.com/jhraihan/Servora.git /srv/shebalocal
cd /srv/shebalocal/backend
sudo -u sheba python3.12 -m venv venv
sudo -u sheba venv/bin/pip install -r requirements.txt

sudo -u sheba mkdir -p media private_media
sudo chown sheba:www-data media && sudo chmod 2770 media
sudo chmod 700 private_media
```

## 5. Settings

```bash
sudo -u sheba cp /srv/shebalocal/deploy/env.production.example /srv/shebalocal/backend/.env
sudo chmod 600 /srv/shebalocal/backend/.env
sudo -u sheba nano /srv/shebalocal/backend/.env
```

Fill in every `<...>` value:

- `SECRET_KEY`: generate a new one on the server. Never reuse the development key.
- `DATABASE_URL`: the password you gave the `sheba` role in step 3.
- `TRUSTED_PROXY_COUNT=1` is correct only while Nginx is the **only** proxy in front of the app.
  Nginx overwrites `X-Forwarded-For` with the real client address, and the login, OTP and search
  rate limits trust that value. If you ever put a CDN or load balancer in front of Nginx, this
  number and the Nginx `X-Forwarded-For` line must change together, or clients can dodge rate
  limits by sending a fake header.

**Always run Django commands through `deploy/scripts/manage.sh`.** A plain
`python manage.py ...` falls back to the development settings, which switch `DEBUG` on against
the production database. The wrapper pins `config.settings.prod`.

```bash
cd /srv/shebalocal
sudo -u sheba deploy/scripts/manage.sh check --deploy --fail-level WARNING
sudo -u sheba deploy/scripts/manage.sh migrate
sudo -u sheba deploy/scripts/manage.sh collectstatic --no-input
sudo -u sheba deploy/scripts/manage.sh seed_catalogue
sudo -u sheba deploy/scripts/manage.sh createsuperuser
```

`seed_demo` refuses to run with `DEBUG` off. That is deliberate, because it creates accounts with
a published password.

## 6. Frontend build

```bash
cd /srv/shebalocal/frontend
sudo -u sheba npm ci
sudo -u sheba npm run build
```

The build writes two pages. `dist/index.html` has the landing page's hero already rendered, so
the headline appears before any JavaScript runs. `dist/app.html` serves every other route. The
Nginx config depends on both files.

## 7. App server

```bash
sudo cp /srv/shebalocal/deploy/systemd/shebalocal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now shebalocal
sudo systemctl status shebalocal
curl --unix-socket /run/shebalocal/gunicorn.sock -H "Host: shebalocal.example.com" \
     -H "X-Forwarded-Proto: https" http://localhost/api/v1/categories/
```

The `curl` should print the category list as JSON. Logs: `journalctl -u shebalocal -f`.

## 8. Nginx and HTTPS

The certificate has to exist before our config will load, so issue it first through Ubuntu's
default site, which already serves `/var/www/html`:

```bash
sudo certbot certonly --webroot -w /var/www/html -d shebalocal.example.com \
     --deploy-hook "systemctl reload nginx"
```

Then install the ShebaLocal config and remove the default site:

```bash
sudo cp /srv/shebalocal/deploy/nginx/snippets/*.conf /etc/nginx/snippets/
sudo cp /srv/shebalocal/deploy/nginx/shebalocal.conf /etc/nginx/sites-available/
sudo sed -i 's/shebalocal.example.com/YOUR.DOMAIN/g' /etc/nginx/sites-available/shebalocal.conf
sudo ln -s /etc/nginx/sites-available/shebalocal.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot renew --dry-run
```

Our config keeps serving `/.well-known/acme-challenge/` from `/var/www/html` over plain HTTP, so
renewals keep working without further changes.

The `Strict-Transport-Security` header includes `preload`. If you submit the domain to the
browser preload list, browsers will refuse plain HTTP for it, and every subdomain, for a long
time. Only submit once HTTPS is solid.

## 9. Scheduled jobs and backups

The job schedule lives in code (`apps/operations/jobs.py`). Generate the crontab from it rather
than typing it, then add the backup and a weekly restore check:

```bash
cd /srv/shebalocal
{ sudo -u sheba deploy/scripts/manage.sh crontab
  echo "0 2 * * *   /srv/shebalocal/deploy/scripts/backup.sh >> /var/log/shebalocal/backup.log 2>&1"
  echo "30 5 * * 0  /srv/shebalocal/deploy/scripts/restore-check.sh >> /var/log/shebalocal/backup.log 2>&1"
} | sudo crontab -u sheba -
sudo crontab -u sheba -l
```

Run both scripts once by hand before trusting them:

```bash
sudo -u sheba deploy/scripts/backup.sh
sudo -u sheba deploy/scripts/restore-check.sh
```

`backup.sh` writes a verified `pg_dump` and a tarball of `media` and `private_media` to
`/var/backups/shebalocal` and deletes anything older than 30 days. `restore-check.sh` restores the
newest dump into a scratch database, prints row counts, and drops it. Both connect as the `sheba`
role over the local socket, so they need no password.

**Backups must leave the server.** Set `BACKUP_REMOTE` (any `rsync` destination, such as
`backup@otherhost:/srv/backups/shebalocal/`) at the top of the crontab and set up an SSH key for
it. The tarball contains customers' ID documents, so the destination must be private, and
ideally encrypted.

Job health is visible to admin users at `GET /api/v1/admin/job-runs/`. After the first hour,
every job should report a recent success.

## 10. Check the live site

- `https://YOUR.DOMAIN/` shows the landing page, and the headline appears before the page is interactive.
- `curl -sI https://YOUR.DOMAIN/ | grep -i -E "strict-transport|content-security|x-frame"` prints all three headers.
- `https://YOUR.DOMAIN/providers` loads (served by `app.html`).
- `https://YOUR.DOMAIN/admin/` shows the Django login, styled, which proves `/static/` works.
- `curl -s -o /dev/null -w "%{http_code}" https://YOUR.DOMAIN/.env` prints `404`.
- Log in, register a provider and upload a verification document. The file lands in
  `private_media/`, and there is no URL that serves it.

## Updating

```bash
cd /srv/shebalocal
sudo -u sheba deploy/scripts/backup.sh
sudo -u sheba git pull
sudo -u sheba backend/venv/bin/pip install -r backend/requirements.txt
sudo -u sheba deploy/scripts/manage.sh migrate
sudo -u sheba deploy/scripts/manage.sh collectstatic --no-input
(cd frontend && sudo -u sheba npm ci && sudo -u sheba npm run build)
sudo systemctl reload shebalocal
```

`reload` restarts gunicorn's workers one at a time, so requests are not dropped. If the job
schedule changed, regenerate the crontab as in step 9.

To roll back, check out the previous commit and repeat the steps above. If a migration changed
data, restore the backup taken at the start instead of migrating backwards.

## What has and has not been verified

Checked on the development machine:

- `manage.py check --deploy --fail-level WARNING` passes on the production settings, using the
  variables in `env.production.example`.
- `backup.sh` produced a dump and a media tarball from the real development database, and a
  restore of that dump as the non-superuser app role brought back every table (30 users,
  231 bookings, 585 ledger entries). The first attempt failed on the `earthdistance` extension,
  which is why step 3 says not to install extensions.
- The Content-Security-Policy in `nginx/snippets/shebalocal-headers.conf` was applied to the
  production build in a browser, across ten pages, a login and the trust breakdown, with no
  violations and no console errors.
- The landing-versus-app routing was exercised with `vite preview`, which mirrors the Nginx rules.
- The pinned `gunicorn` has no known vulnerabilities, and the gunicorn config parses.

Not verified, because it needs a Linux server:

- `nginx -t` on the config, and the certificate issuance and renewal flow.
- gunicorn starting under the systemd unit, especially with its hardening options
  (`ProtectSystem=strict` and so on). If the service fails to start, check `journalctl -u shebalocal`.
- The cron entries running under a real `cron`.
