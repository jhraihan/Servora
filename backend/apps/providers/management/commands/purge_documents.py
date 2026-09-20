from django.core.management.base import BaseCommand

from apps.providers import services

class Command(BaseCommand):
    help = "Delete verification document files past their retention window."

    def handle(self, *args, **options):
        purged = services.purge_reviewed_documents()
        self.stdout.write(self.style.SUCCESS(
            "Purged %d verification document file(s)." % purged
        ))
