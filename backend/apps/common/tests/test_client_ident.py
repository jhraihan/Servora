import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

FORGED = "203.0.113.7"


@pytest.fixture
def url():
    return reverse("catalogue:category-list")


def test_the_header_is_absent_by_default(client, url, settings):
    assert settings.EXPOSE_CLIENT_IDENT is False
    assert "X-Client-Ident" not in client.get(url)


def test_one_proxy_trusts_the_address_nginx_appended(client, url, settings):
    settings.EXPOSE_CLIENT_IDENT = True
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}

    response = client.get(url, headers={"x-forwarded-for": "%s, 10.0.0.9"
                                                           % FORGED})

    assert response["X-Client-Ident"] == "10.0.0.9"


def test_no_proxy_ignores_the_header_entirely(client, url, settings):
    settings.EXPOSE_CLIENT_IDENT = True
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 0}

    response = client.get(url, headers={"x-forwarded-for": FORGED},
                          REMOTE_ADDR="10.0.0.9")

    assert response["X-Client-Ident"] == "10.0.0.9"


def test_too_many_proxies_lets_a_forged_address_through(client, url, settings):
    settings.EXPOSE_CLIENT_IDENT = True
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 2}

    response = client.get(url, headers={"x-forwarded-for": "%s, 10.0.0.9"
                                                           % FORGED})

    assert response["X-Client-Ident"] == FORGED
