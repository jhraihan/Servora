from apps.accounts import services
from apps.operations.scheduling import ScheduledCommand


class Command(ScheduledCommand):
    help = "Purge OTP codes older than the retention window."
    job_name = "purge_otps"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours", type=int, default=24,
            help="Delete codes created more than this many hours ago.",
        )

    def run_job(self, *args, **options):
        deleted = services.purge_expired_otps(older_than_hours=options["hours"])
        return deleted, "Purged %d OTP row(s)." % deleted
