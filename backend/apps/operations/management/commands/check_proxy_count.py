import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError

PROBE = "203.0.113.7"


class Command(BaseCommand):
    help = ("Check that TRUSTED_PROXY_COUNT matches the deployment, by asking "
            "the live site whether a forged X-Forwarded-For reaches the "
            "rate limiter.")

    def add_arguments(self, parser):
        parser.add_argument("url", help="A throttled endpoint, e.g. "
                                        "https://example.com/api/v1/providers/")

    def handle(self, *args, **options):
        seen = self._probe(options["url"], PROBE)
        baseline = self._probe(options["url"], None)

        self.stdout.write("Rate limiting sees %r with a forged header, %r "
                          "without one." % (seen, baseline))

        if seen is None or baseline is None:
            raise CommandError(
                "The endpoint did not report a client address. Add the "
                "debug header support described in deploy/RENDER.md, or "
                "check the address in the access log instead."
            )

        if seen == PROBE:
            raise CommandError(
                "A forged X-Forwarded-For header reached the rate limiter. "
                "TRUSTED_PROXY_COUNT is too high: anyone can dodge the login "
                "and OTP limits by sending a fake header. Lower it by one "
                "and deploy again."
            )

        self.stdout.write(self.style.SUCCESS(
            "Forged headers are ignored; TRUSTED_PROXY_COUNT is not too high."
        ))

    def _probe(self, url, forged):
        request = urllib.request.Request(url)
        if forged:
            request.add_header("X-Forwarded-For", forged)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.headers.get("X-Client-Ident")
        except urllib.error.HTTPError as error:
            return error.headers.get("X-Client-Ident")
        except urllib.error.URLError as error:
            raise CommandError("Could not reach %s: %s" % (url, error.reason))
