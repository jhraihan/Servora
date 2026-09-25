from apps.operations.scheduling import ScheduledCommand
from apps.trust import engine
from apps.trust.models import TrustSnapshot


class Command(ScheduledCommand):
    help = "Recompute trust scores for all active providers."
    job_name = "recompute_all_trust"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true",
                            help="Include inactive providers.")

    def run_job(self, *args, **options):
        count = engine.recompute_all(
            trigger=TrustSnapshot.Trigger.NIGHTLY_BATCH,
            only_active=not options["all"],
        )
        return count, "Recomputed trust for %d provider(s)." % count
