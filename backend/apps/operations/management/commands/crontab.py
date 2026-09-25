from django.core.management.base import BaseCommand

from apps.operations.jobs import SCHEDULE


class Command(BaseCommand):
    help = "Print crontab entries for every scheduled job."

    def add_arguments(self, parser):
        parser.add_argument("--root", default="/srv/shebalocal/backend",
                            help="Backend directory on the server.")
        parser.add_argument("--python", default=None,
                            help="Python interpreter. Defaults to ROOT/venv/bin/python.")
        parser.add_argument("--settings-module", default="config.settings.prod")
        parser.add_argument("--log", default="/var/log/shebalocal/cron.log")

    def handle(self, *args, **options):
        root = options["root"].rstrip("/")
        python = options["python"] or "%s/venv/bin/python" % root

        lines = [
            "SHELL=/bin/bash",
            "DJANGO_SETTINGS_MODULE=%s" % options["settings_module"],
            "",
        ]
        width = max(len(job.cron) for job in SCHEDULE)
        for job in SCHEDULE:
            lines.append(
                "%s  cd %s && %s manage.py %s >> %s 2>&1"
                % (job.cron.ljust(width), root, python, job.name, options["log"])
            )
        self.stdout.write("\n".join(lines))
