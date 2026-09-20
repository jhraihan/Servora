"""
Delete spent and expired OTP rows.

Replaces Redis TTL in Phase 1 (PRD 8.4, FR-9.3). Idempotent: a repeated or
overlapping run simply finds nothing left to delete.
"""

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
