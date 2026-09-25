from django.core.management.base import CommandError

from apps.accounts.models import ProviderProfile
from apps.operations.scheduling import ScheduledCommand
from apps.payments import services


class Command(ScheduledCommand):
    help = "Check that every provider's ledger reconciles with their bookings."
    job_name = "reconcile_earnings"

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=int,
                            help="Reconcile a single provider.")
        parser.add_argument("--fix", action="store_true",
                            help="Record payments for completed bookings "
                                 "that have none, then re-check.")

    def run_job(self, *args, **options):
        provider_id = options.get("provider")

        if options["fix"]:
            created = services.backfill_missing_payments(provider_id)
            self.stdout.write("Backfilled %d payment(s)." % created)

        providers = ProviderProfile.objects.all()
        if provider_id is not None:
            providers = providers.filter(pk=provider_id)

        checked = 0
        failures = 0
        for pk in providers.values_list("pk", flat=True):
            checked += 1
            for problem in services.reconcile_provider(pk):
                failures += 1
                self.stderr.write("provider %s: %s" % (pk, problem))

        if failures:
            raise CommandError(
                "%d discrepancy(ies) across %d provider(s)."
                % (failures, checked)
            )
        return checked, (
            "Reconciled %d provider(s): no discrepancies." % checked
        )
