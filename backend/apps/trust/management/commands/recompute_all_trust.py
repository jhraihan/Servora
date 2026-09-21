from django.core.management.base import BaseCommand

from apps.trust import engine
from apps.trust.models import TrustSnapshot

class Command(BaseCommand):
    help = "Recompute trust scores for all active providers."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true",
                            help="Include inactive providers.")

    def handle(self, *args, **options):
        count = engine.recompute_all(
            trigger=TrustSnapshot.Trigger.NIGHTLY_BATCH,
            only_active=not options["all"],
        )
        self.stdout.write(self.style.SUCCESS(
            "Recomputed trust for %d provider(s)." % count
        ))
