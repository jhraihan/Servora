from apps.bookings import services
from apps.operations.scheduling import ScheduledCommand


class Command(ScheduledCommand):
    help = "Close service requests that went unanswered past their expiry."
    job_name = "expire_requests"

    def run_job(self, *args, **options):
        expired = services.expire_stale_requests()
        return expired, "Expired %d request(s)." % expired
