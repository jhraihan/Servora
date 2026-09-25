import random
import statistics
import time
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Count
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import ProviderProfile
from apps.catalogue.models import Location, Service
from apps.trust import engine

TARGETS_MS = {
    "provider search": 400,
    "provider detail": 250,
    "trust breakdown": 250,
}
RECOMPUTE_TARGET_MS = 2000


def _percentile(values, pct):
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered)) - 1))
    return ordered[index]


class Command(BaseCommand):
    help = "Measure API latency and query counts against the PRD 12.1 targets."

    def add_arguments(self, parser):
        parser.add_argument("--requests", type=int, default=200)
        parser.add_argument("--seed", type=int, default=11)

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        provider_ids = list(ProviderProfile.objects.values_list("pk", flat=True))
        if len(provider_ids) < 50:
            raise CommandError("Seed data first: manage.py seed_demo --bulk 2000")

        service_ids = list(Service.objects.values_list("pk", flat=True))
        location_ids = list(Location.objects.exclude(level=Location.Level.CITY)
                            .values_list("pk", flat=True))
        orderings = ["", "", "price", "distance"]

        def search_path():
            params = {"service": rng.choice(service_ids),
                      "location": rng.choice(location_ids),
                      "ordering": rng.choice(orderings)}
            if rng.random() < 0.3:
                params["min_trust"] = rng.choice([40, 60, 75])
            if rng.random() < 0.3:
                params["available_on"] = (date.today() + timedelta(
                    days=rng.randint(0, 6))).isoformat()
            query = "&".join("%s=%s" % kv for kv in params.items() if kv[1] != "")
            return "/api/v1/providers/?%s" % query

        scenarios = [
            ("provider search", search_path),
            ("provider detail",
             lambda: "/api/v1/providers/%d/" % rng.choice(provider_ids)),
            ("trust breakdown",
             lambda: "/api/v1/providers/%d/trust/" % rng.choice(provider_ids)),
        ]

        self.stdout.write("%d providers in the database, %d requests per endpoint\n"
                          % (len(provider_ids), options["requests"]))
        self.stdout.write("%-18s %8s %8s %8s %9s %8s  %s"
                          % ("endpoint", "p50 ms", "p95 ms", "max ms",
                             "queries", "target", "result"))

        failures = []
        with override_settings(DEBUG=False, ALLOWED_HOSTS=["*"]):
            for name, make_path in scenarios:
                timings, queries = self._measure(make_path, options["requests"])
                p95 = _percentile(timings, 95)
                ok = p95 < TARGETS_MS[name]
                if not ok:
                    failures.append(name)
                self.stdout.write("%-18s %8.1f %8.1f %8.1f %9s %8d  %s" % (
                    name, statistics.median(timings), p95, max(timings),
                    "%d-%d" % (min(queries), max(queries)),
                    TARGETS_MS[name], "PASS" if ok else "FAIL"))

        richest = (ProviderProfile.objects
                   .annotate(real_bookings=Count("bookings"))
                   .order_by("-real_bookings")
                   .values_list("pk", flat=True).first())
        timings = []
        for _ in range(10):
            started = time.perf_counter()
            engine.recompute(richest)
            timings.append((time.perf_counter() - started) * 1000)
        p95 = _percentile(timings, 95)
        ok = p95 < RECOMPUTE_TARGET_MS
        if not ok:
            failures.append("trust recompute")
        self.stdout.write("%-18s %8.1f %8.1f %8.1f %9s %8d  %s" % (
            "trust recompute", statistics.median(timings), p95, max(timings),
            "-", RECOMPUTE_TARGET_MS, "PASS" if ok else "FAIL"))

        if failures:
            raise CommandError("Missed target: %s" % ", ".join(failures))

    def _measure(self, make_path, count):
        client = Client()
        timings, queries = [], []
        for i in range(count):
            with CaptureQueriesContext(connection) as captured:
                started = time.perf_counter()
                response = client.get(
                    make_path(),
                    REMOTE_ADDR="10.%d.%d.%d" % (i // 65536 % 256,
                                                 i // 256 % 256, i % 256),
                )
                timings.append((time.perf_counter() - started) * 1000)
            queries.append(len(captured))
            if response.status_code != 200:
                raise CommandError("%s returned %s"
                                   % (response.request["PATH_INFO"],
                                      response.status_code))
        return timings, queries
