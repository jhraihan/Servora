from apps.operations.scheduling import ScheduledCommand
from apps.reviews import services


class Command(ScheduledCommand):
    help = "Publish reviews whose double-blind window has closed."
    job_name = "reveal_reviews"

    def run_job(self, *args, **options):
        revealed = services.reveal_expired_reviews()
        return revealed, "Revealed %d review(s)." % revealed
