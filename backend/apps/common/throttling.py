"""
Custom throttles.

DRF's rate syntax only accepts a bare period ("5/min", "5/hour") -- it cannot
express "5 per 15 minutes", which is what PRD 12.2 specifies for login. The
throttle below adds an explicit duration instead of trying to encode the
window in the rate string.
"""

from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """5 login attempts per 15 minutes per IP (PRD 12.2)."""

    scope = "login"
    rate = "5/15min"          # documentation only; parsed below

    num_requests = 5
    duration = 15 * 60

    def get_rate(self):
        # Bypass DRF's parser, which cannot read the multiplier.
        return self.rate

    def parse_rate(self, rate):
        return self.num_requests, self.duration

    def get_cache_key(self, request, view):
        # Throttle by IP: the identifier being attacked is whatever the
        # attacker types, so keying on it would let them rotate freely.
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
