from django.core.management.base import BaseCommand

from apps.accounts import services

class Command(BaseCommand):
    help = "Purge OTP codes older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours", type=int, default=24,
            help="Delete codes created more than this many hours ago.",
        )

    def handle(self, *args, **options):
        deleted = services.purge_expired_otps(
            older_than_hours=options["hours"]
        )
        self.stdout.write(self.style.SUCCESS(
            "Purged %d OTP row(s)." % deleted
        ))
