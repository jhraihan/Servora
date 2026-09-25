import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from apps.accounts import services as account_services
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

API_PREFIX = "api/v1/"

PUBLIC = {
    "api/v1/auth/register/",
    "api/v1/auth/otp/send/",
    "api/v1/auth/otp/verify/",
    "api/v1/auth/login/",
    "api/v1/auth/refresh/",
    "api/v1/categories/",
    "api/v1/categories/<slug>/",
    "api/v1/services/",
    "api/v1/locations/",
    "api/v1/locations/tree/",
    "api/v1/providers/",
    "api/v1/providers/<id>/",
    "api/v1/providers/<id>/availability/",
    "api/v1/providers/<id>/trust/",
    "api/v1/providers/<id>/reviews/",
}

CONVERTER = re.compile(r"<(?:(\w+):)?(\w+)>")


def _walk(patterns, prefix=""):
    for entry in patterns:
        route = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, route)
        elif isinstance(entry, URLPattern):
            yield route


def _api_routes():
    return sorted({r for r in _walk(get_resolver().url_patterns)
                   if r.startswith(API_PREFIX)})


def _template(route):
    return CONVERTER.sub(lambda m: "<slug>" if m.group(1) == "slug" else "<id>",
                         route)


def _concrete(route):
    return "/" + CONVERTER.sub(
        lambda m: "sample" if m.group(1) == "slug" else "1", route)


def test_allowlist_names_only_real_routes():
    templates = {_template(r) for r in _api_routes()}
    assert PUBLIC <= templates, PUBLIC - templates


def test_enough_routes_are_being_checked():
    assert len(_api_routes()) >= 60


@pytest.mark.parametrize("route", _api_routes())
def test_private_routes_reject_anonymous_callers(route):
    if _template(route) in PUBLIC:
        pytest.skip("public route")

    client = APIClient()
    for method in ("get", "post"):
        response = getattr(client, method)(_concrete(route), {}, format="json")
        assert response.status_code == 401, (
            "%s %s answered %s to an anonymous caller"
            % (method.upper(), route, response.status_code)
        )


@pytest.fixture
def customer_client(db):
    user = account_services.register_user(
        phone="+8801912345678", password="testpass123",
        role=User.Role.CUSTOMER,
    )
    client = APIClient()
    token = client.post("/api/v1/auth/login/",
                        {"phone": user.phone, "password": "testpass123"},
                        format="json").data["access"]
    client.credentials(HTTP_AUTHORIZATION="Bearer %s" % token)
    return client


def test_admin_routes_refuse_ordinary_users(customer_client):
    admin_routes = [r for r in _api_routes() if r.startswith(API_PREFIX + "admin/")]
    assert len(admin_routes) >= 8

    for route in admin_routes:
        for method in ("get", "post"):
            response = getattr(customer_client, method)(
                _concrete(route), {}, format="json")
            assert response.status_code == 403, (
                "%s %s answered %s to a customer"
                % (method.upper(), route, response.status_code)
            )
