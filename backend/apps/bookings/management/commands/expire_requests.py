from django.core.management.base import BaseCommand

from apps.bookings import services

class Command(BaseCommand):
    help = "Close service requests that went unanswered past their expiry."

    def handle(self, *args, **options):
        expired = services.expire_stale_requests()
        self.stdout.write(self.style.SUCCESS(
            "Expired %d request(s)." % expired
        ))
