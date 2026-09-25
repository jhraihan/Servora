wsgi_app = "config.wsgi:application"
bind = "unix:/run/shebalocal/gunicorn.sock"
umask = 0o007

workers = 3
worker_class = "sync"
timeout = 30
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = "info"
