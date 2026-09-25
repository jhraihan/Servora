from apps.bookings import services
from apps.operations.scheduling import ScheduledCommand


class Command(ScheduledCommand):
    help = "Auto-confirm bookings the customer never confirmed."
    job_name = "auto_confirm"

    def run_job(self, *args, **options):
        confirmed = services.auto_confirm_bookings()
        return confirmed, "Auto-confirmed %d booking(s)." % confirmed
