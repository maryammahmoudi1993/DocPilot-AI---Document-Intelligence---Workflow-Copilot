"""Required-environment-variable validation for the production settings
module. `local.py` and `test.py` intentionally have safe fallbacks (see
their module docstrings); `production.py` must not.
"""

import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


def _reimport_production_settings():
    for module_name in ("config.settings.production", "config.settings.base"):
        sys.modules.pop(module_name, None)
    import importlib

    return importlib.import_module("config.settings.production")


def test_production_requires_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("INTEGRATION_SECRET_KEY", "xjnqLuaWBy-MYTPeJUKpEGiIB1W1VbeMBsyYaPfswhc=")

    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        _reimport_production_settings()


def test_production_requires_allowed_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "a-real-secret-key")
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("INTEGRATION_SECRET_KEY", "xjnqLuaWBy-MYTPeJUKpEGiIB1W1VbeMBsyYaPfswhc=")

    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        _reimport_production_settings()


def test_production_requires_integration_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "a-real-secret-key")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")
    monkeypatch.delenv("INTEGRATION_SECRET_KEY", raising=False)

    with pytest.raises(ImproperlyConfigured, match="INTEGRATION_SECRET_KEY"):
        _reimport_production_settings()


def test_production_boots_when_required_vars_are_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "a-real-secret-key")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("INTEGRATION_SECRET_KEY", "xjnqLuaWBy-MYTPeJUKpEGiIB1W1VbeMBsyYaPfswhc=")

    settings_module = _reimport_production_settings()

    assert settings_module.DEBUG is False
    assert settings_module.ALLOWED_HOSTS == ["example.com"]


def test_production_sets_the_hardened_security_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "a-real-secret-key")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("INTEGRATION_SECRET_KEY", "xjnqLuaWBy-MYTPeJUKpEGiIB1W1VbeMBsyYaPfswhc=")

    settings_module = _reimport_production_settings()

    # Clickjacking: deny framing entirely (this app is never embedded).
    assert settings_module.X_FRAME_OPTIONS == "DENY"
    # Referrer-Policy: never leak the current URL (which can contain a
    # document/workspace id) to a cross-origin destination.
    assert settings_module.SECURE_REFERRER_POLICY == "same-origin"
    # MIME-sniffing protection and the cookie/HSTS hardening already
    # covered by test_production_boots_when_required_vars_are_set's
    # sibling assertions above (kept together here since they're all
    # "does production actually turn security on" checks).
    assert settings_module.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings_module.SESSION_COOKIE_SECURE is True
    assert settings_module.CSRF_COOKIE_SECURE is True
