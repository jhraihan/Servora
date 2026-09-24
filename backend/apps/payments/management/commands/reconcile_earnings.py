from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import ProviderProfile
from apps.payments import services


class Command(BaseCommand):
    help = "Check that every provider's ledger reconciles with their bookings."

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=int,
                            help="Reconcile a single provider.")
        parser.add_argument("--fix", action="store_true",
                            help="Record payments for completed bookings "
                                 "that have none, then re-check.")

    def handle(self, *args, **options):
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
            problems = services.reconcile_provider(pk)
            for problem in problems:
                failures += 1
                self.stderr.write("provider %s: %s" % (pk, problem))

        if failures:
            raise CommandError(
                "%d discrepancy(ies) across %d provider(s)."
                % (failures, checked)
            )
        self.stdout.write(self.style.SUCCESS(
            "Reconciled %d provider(s): no discrepancies." % checked
        ))
