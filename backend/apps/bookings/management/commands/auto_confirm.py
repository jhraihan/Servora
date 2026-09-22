from django.core.management.base import BaseCommand

from apps.bookings import services

class Command(BaseCommand):
    help = "Auto-confirm bookings the customer never confirmed."

    def handle(self, *args, **options):
        confirmed = services.auto_confirm_bookings()
        self.stdout.write(self.style.SUCCESS(
            "Auto-confirmed %d booking(s)." % confirmed
        ))
