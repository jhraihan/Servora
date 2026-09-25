import logging

from django.core.management.base import BaseCommand

from .jobs import get_job
from .models import JobRun

logger = logging.getLogger(__name__)


class ScheduledCommand(BaseCommand):
    job_name = None

    def run_job(self, *args, **options):
        raise NotImplementedError

    def handle(self, *args, **options):
        get_job(self.job_name)
        run = JobRun.start(self.job_name)
        try:
            rows, message = self.run_job(*args, **options)
        except Exception as error:
            run.fail(error)
            logger.error("Scheduled job %s failed: %s", self.job_name, error)
            raise

        run.succeed(rows, message)
        JobRun.prune(self.job_name)
        self.stdout.write(self.style.SUCCESS(message))
