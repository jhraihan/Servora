from apps.operations.scheduling import ScheduledCommand
from apps.providers import services


class Command(ScheduledCommand):
    help = "Delete verification document files past their retention window."
    job_name = "purge_documents"

    def run_job(self, *args, **options):
        purged = services.purge_reviewed_documents()
        return purged, "Purged %d verification document file(s)." % purged
