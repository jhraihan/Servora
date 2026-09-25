from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.operations.jobs import SCHEDULE


class Command(BaseCommand):
    help = "Run every scheduled job once, in dependency order."

    def add_arguments(self, parser):
        parser.add_argument("--only", nargs="+", metavar="JOB",
                            help="Run just these jobs, still in schedule order.")

    def handle(self, *args, **options):
        wanted = set(options.get("only") or [job.name for job in SCHEDULE])
        unknown = wanted - {job.name for job in SCHEDULE}
        if unknown:
            raise CommandError("Unknown job(s): %s" % ", ".join(sorted(unknown)))

        failed = []
        for job in SCHEDULE:
            if job.name not in wanted:
                continue
            self.stdout.write("-> %s" % job.name)
            try:
                call_command(job.name, stdout=self.stdout, stderr=self.stderr)
            except Exception as error:
                failed.append(job.name)
                self.stderr.write("   failed: %s" % error)

        if failed:
            raise CommandError("%d job(s) failed: %s"
                               % (len(failed), ", ".join(failed)))
        self.stdout.write(self.style.SUCCESS("All %d job(s) succeeded."
                                             % len(wanted)))
