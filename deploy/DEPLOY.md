# Deploying ServoraBd

This runbook takes a fresh Ubuntu server to a running ServoraBd at `https://servorabd.example.com`.
Replace that domain everywhere with yours.

For a managed platform instead, where you administer no server at all, see
[`RENDER.md`](RENDER.md). It is the easier route.

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
| `/srv/servorabd` | this repository | `servora` |
| `/var/lib/servora` | the `servora` user's home (npm and pip caches) | `servora` |
| `/srv/servorabd/backend/.env` | production settings and secrets | `servora`, `600` |
| `/srv/servorabd/backend/media` | public photos | `servora:www-data`, `2770` |
| `/srv/servorabd/backend/private_media` | ID documents | `servora`, `700` |
| `/run/servorabd/gunicorn.sock` | app socket, created by systemd | `servora:www-data` |
| `/var/log/servorabd` | cron and backup logs | `servora` |
| `/var/backups/servorabd` | nightly database and media backups | `servora`, `700` |

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
sudo adduser --system --group --home /var/lib/servora --shell /bin/bash servora
sudo mkdir -p /srv/servorabd /var/log/servorabd /var/backups/servorabd
sudo chown servora:servora /srv/servorabd /var/log/servorabd /var/backups/servorabd
sudo chmod 700 /var/backups/servorabd
```

## 3. Database

The app connects as its own role, which owns the database and nothing else. It can create
databases only so the weekly restore check can build and drop a scratch copy.

```bash
sudo -u postgres createuser --createdb --pwprompt servora
sudo -u postgres createdb --owner servora servorabd
```

**Do not install any PostgreSQL extensions.** The app does not use any. An extension that only a
superuser can create (such as `earthdistance`) would end up in every backup, and restoring that
backup would then need a superuser. The restore check in step 9 exists to catch exactly that.

## 4. Code and Python environment

```bash
sudo -u servora git clone https://github.com/jhraihan/Servora.git /srv/servorabd
cd /srv/servorabd/backend
sudo -u servora python3.12 -m venv venv
sudo -u servora venv/bin/pip install -r requirements.txt

sudo -u servora mkdir -p media private_media
sudo chown servora:www-data media && sudo chmod 2770 media
sudo chmod 700 private_media
```

## 5. Settings

```bash
sudo -u servora cp /srv/servorabd/deploy/env.production.example /srv/servorabd/backend/.env
sudo chmod 600 /srv/servorabd/backend/.env
sudo -u servora nano /srv/servorabd/backend/.env
```

Fill in every `<...>` value:

- `SECRET_KEY`: generate a new one on the server. Never reuse the development key.
- `DATABASE_URL`: the password you gave the `servora` role in step 3.
- `TRUSTED_PROXY_COUNT=1` is correct only while Nginx is the **only** proxy in front of the app.
  Nginx overwrites `X-Forwarded-For` with the real client address, and the login, OTP and search
  rate limits trust that value. If you ever put a CDN or load balancer in front of Nginx, this
  number and the Nginx `X-Forwarded-For` line must change together, or clients can dodge rate
  limits by sending a fake header.

**Always run Django commands through `deploy/scripts/manage.sh`.** A plain
`python manage.py ...` falls back to the development settings, which switch `DEBUG` on against
the production database. The wrapper pins `config.settings.prod`.

```bash
cd /srv/servorabd
sudo -u servora deploy/scripts/manage.sh check --deploy --fail-level WARNING
sudo -u servora deploy/scripts/manage.sh migrate
sudo -u servora deploy/scripts/manage.sh collectstatic --no-input
sudo -u servora deploy/scripts/manage.sh seed_catalogue
sudo -u servora deploy/scripts/manage.sh createsuperuser
```

`seed_demo` refuses to run with `DEBUG` off. That is deliberate, because it creates accounts with
a published password.

## 6. Frontend build

```bash
cd /srv/servorabd/frontend
sudo -u servora npm ci
sudo -u servora npm run build
```

The build writes two pages. `dist/index.html` has the landing page's hero already rendered, so
the headline appears before any JavaScript runs. `dist/app.html` serves every other route. The
Nginx config depends on both files.

## 7. App server

```bash
sudo cp /srv/servorabd/deploy/systemd/servorabd.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now servorabd
sudo systemctl status servorabd
curl --unix-socket /run/servorabd/gunicorn.sock -H "Host: servorabd.example.com" \
     -H "X-Forwarded-Proto: https" http://localhost/api/v1/categories/
```

The `curl` should print the category list as JSON. Logs: `journalctl -u servorabd -f`.

## 8. Nginx and HTTPS

The certificate has to exist before our config will load, so issue it first through Ubuntu's
default site, which already serves `/var/www/html`:

```bash
sudo certbot certonly --webroot -w /var/www/html -d servorabd.example.com \
     --deploy-hook "systemctl reload nginx"
```

Then install the ServoraBd config and remove the default site:

```bash
sudo cp /srv/servorabd/deploy/nginx/snippets/*.conf /etc/nginx/snippets/
sudo cp /srv/servorabd/deploy/nginx/servorabd.conf /etc/nginx/sites-available/
sudo sed -i 's/servorabd.example.com/YOUR.DOMAIN/g' /etc/nginx/sites-available/servorabd.conf
sudo ln -s /etc/nginx/sites-available/servorabd.conf /etc/nginx/sites-enabled/
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
cd /srv/servorabd
{ sudo -u servora deploy/scripts/manage.sh crontab
  echo "0 2 * * *   /srv/servorabd/deploy/scripts/backup.sh >> /var/log/servorabd/backup.log 2>&1"
  echo "30 5 * * 0  /srv/servorabd/deploy/scripts/restore-check.sh >> /var/log/servorabd/backup.log 2>&1"
} | sudo crontab -u servora -
sudo crontab -u servora -l
```

Run both scripts once by hand before trusting them:

```bash
sudo -u servora deploy/scripts/backup.sh
sudo -u servora deploy/scripts/restore-check.sh
```

`backup.sh` writes a verified `pg_dump` and a tarball of `media` and `private_media` to
`/var/backups/servorabd` and deletes anything older than 30 days. `restore-check.sh` restores the
newest dump into a scratch database, prints row counts, and drops it. Both connect as the `servora`
role over the local socket, so they need no password.

**Backups must leave the server.** Set `BACKUP_REMOTE` (any `rsync` destination, such as
`backup@otherhost:/srv/backups/servorabd/`) at the top of the crontab and set up an SSH key for
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
cd /srv/servorabd
sudo -u servora deploy/scripts/backup.sh
sudo -u servora git pull
sudo -u servora backend/venv/bin/pip install -r backend/requirements.txt
sudo -u servora deploy/scripts/manage.sh migrate
sudo -u servora deploy/scripts/manage.sh collectstatic --no-input
(cd frontend && sudo -u servora npm ci && sudo -u servora npm run build)
sudo systemctl reload servorabd
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
- The Content-Security-Policy in `nginx/snippets/servorabd-headers.conf` was applied to the
  production build in a browser, across ten pages, a login and the trust breakdown, with no
  violations and no console errors.
- The landing-versus-app routing was exercised with `vite preview`, which mirrors the Nginx rules.
- The pinned `gunicorn` has no known vulnerabilities, and the gunicorn config parses.

Not verified, because it needs a Linux server:

- `nginx -t` on the config, and the certificate issuance and renewal flow.
- gunicorn starting under the systemd unit, especially with its hardening options
  (`ProtectSystem=strict` and so on). If the service fails to start, check `journalctl -u servorabd`.
- The cron entries running under a real `cron`.
