import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.operations import demo
from apps.trust import engine


class Command(BaseCommand):
    help = "Fill a development database with a realistic demo marketplace."

    def add_arguments(self, parser):
        parser.add_argument("--per-archetype", type=int, default=3,
                            help="Providers created for each of the six archetypes.")
        parser.add_argument("--bulk", type=int, default=0,
                            help="Also create this many lightweight providers "
                                 "for load testing.")
        parser.add_argument("--reset", action="store_true",
                            help="Delete all demo data first.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_demo creates accounts with a published password and "
                "refuses to run when DEBUG is off."
            )

        if options["reset"]:
            removed = demo.reset_demo()
            self.stdout.write("Removed %d demo user(s)." % removed)

        self.stdout.write("Seeding the demo marketplace...")
        started = time.perf_counter()
        created = demo.seed_marketplace(
            providers_per_archetype=options["per_archetype"],
            log=self.stdout.write,
        )
        self.stdout.write("Created %d provider(s) in %.1fs."
                          % (created, time.perf_counter() - started))

        if options["bulk"]:
            started = time.perf_counter()
            demo.seed_bulk(options["bulk"], log=self.stdout.write)
            self.stdout.write("Bulk insert took %.1fs."
                              % (time.perf_counter() - started))
            started = time.perf_counter()
            count = engine.recompute_all()
            self.stdout.write("Scored %d provider(s) in %.1fs."
                              % (count, time.perf_counter() - started))

        self.stdout.write(self.style.SUCCESS(
            "Log in with any demo phone, password %s. Customer: %s. "
            "Veteran provider: %s. Flaky provider: %s."
            % (demo.DEMO_PASSWORD, demo.demo_phone(demo.CUSTOMER_OFFSET),
               demo.demo_phone(1), demo.demo_phone(3))
        ))
