from django.core.management.base import BaseCommand

from apps.reviews import services

class Command(BaseCommand):
    help = "Publish reviews whose double-blind window has closed."

    def handle(self, *args, **options):
        revealed = services.reveal_expired_reviews()
        self.stdout.write(self.style.SUCCESS(
            "Revealed %d review(s)." % revealed
        ))
