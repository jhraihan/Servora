import os

wsgi_app = "config.wsgi:application"

if os.environ.get("PORT"):
    bind = "0.0.0.0:%s" % os.environ["PORT"]
    forwarded_allow_ips = "*"
else:
    bind = "unix:/run/shebalocal/gunicorn.sock"
    umask = 0o007

workers = int(os.environ.get("WEB_CONCURRENCY", 3))
worker_class = "sync"
timeout = 30
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = "info"
