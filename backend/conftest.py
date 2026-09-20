"""
Pytest fixtures applied to every test.

Throttle state lives in Django's cache, which is process-wide and is NOT
reset between tests. Without clearing it, the login throttle trips partway
through a run and every later test sees 429 -- a false failure that hides
real ones.
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()
