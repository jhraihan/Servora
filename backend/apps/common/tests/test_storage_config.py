import importlib
from urllib.parse import parse_qs, urlparse

import pytest

PROD_ENV = {
    "SECRET_KEY": "test-key-for-settings-import-only",
    "DEBUG": "False",
    "ALLOWED_HOSTS": "shebalocal.example.com",
    "DATABASE_URL": "postgres://u:p@127.0.0.1:5432/db",
    "EMAIL_HOST": "smtp.example.com",
    "EMAIL_HOST_USER": "u",
    "EMAIL_HOST_PASSWORD": "p",
    "DEFAULT_FROM_EMAIL": "no-reply@example.com",
    "TRUSTED_PROXY_COUNT": "1",
    "USE_OBJECT_STORAGE": "True",
    "S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_BUCKET_NAME": "shebalocal",
}


def _load(monkeypatch, **overrides):
    for key, value in {**PROD_ENV, **overrides}.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(importlib.import_module("config.settings.prod"))


@pytest.fixture
def prod_settings(monkeypatch):
    return _load(monkeypatch)


def test_documents_and_photos_use_separate_prefixes(prod_settings):
    private = prod_settings.STORAGES["private"]["OPTIONS"]
    default = prod_settings.STORAGES["default"]["OPTIONS"]

    assert private["location"] == "private"
    assert default["location"] == "media"
    assert private["location"] != default["location"]


def test_document_links_expire_and_are_signed(prod_settings):
    private = prod_settings.STORAGES["private"]["OPTIONS"]

    assert private["querystring_auth"] is True
    assert private["querystring_expire"] <= 600
    assert private["custom_domain"] is False


def test_public_photos_are_served_without_signing(prod_settings):
    default = prod_settings.STORAGES["default"]["OPTIONS"]

    assert default["querystring_auth"] is False


def test_uploads_never_overwrite_each_other(prod_settings):
    for alias in ("default", "private"):
        assert prod_settings.STORAGES[alias]["OPTIONS"]["file_overwrite"] is False


def test_static_files_are_served_by_whitenoise(prod_settings):
    assert "whitenoise" in prod_settings.STORAGES["staticfiles"]["BACKEND"]
    security = prod_settings.MIDDLEWARE.index(
        "django.middleware.security.SecurityMiddleware")
    assert prod_settings.MIDDLEWARE[security + 1] == (
        "whitenoise.middleware.WhiteNoiseMiddleware")


def test_local_disk_is_the_default_without_the_flag(monkeypatch):
    settings = _load(monkeypatch, USE_OBJECT_STORAGE="False")

    assert settings.STORAGES["private"]["BACKEND"] == (
        "apps.common.storage.PrivateMediaStorage")


def _storage(prod_settings, alias):
    from django.utils.module_loading import import_string

    config = prod_settings.STORAGES[alias]
    return import_string(config["BACKEND"])(**config["OPTIONS"])


def test_a_document_url_is_signed_and_expires(prod_settings):
    url = _storage(prod_settings, "private").url("verification/9/nid.jpg")
    query = parse_qs(urlparse(url).query)

    assert urlparse(url).path.endswith("/private/verification/9/nid.jpg")
    assert "X-Amz-Signature" in query
    assert int(query["X-Amz-Expires"][0]) <= 600


def test_a_work_photo_url_carries_no_credentials(prod_settings):
    url = _storage(prod_settings, "default").url("work_photos/9/p.jpg")

    assert urlparse(url).path.endswith("/media/work_photos/9/p.jpg")
    assert "X-Amz-Signature" not in parse_qs(urlparse(url).query)
