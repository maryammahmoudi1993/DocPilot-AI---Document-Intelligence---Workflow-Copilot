"""Application boot smoke tests.

These would fail today (before the config/apps scaffold exists) with an
import error, not a normal assertion failure — that IS the "expected
reason" for this phase's test-first branch: there is no Django project to
boot yet.
"""

import pytest
from django.core.management import call_command


def test_django_check_passes() -> None:
    """`manage.py check` — Django's own system-check framework — is clean."""
    call_command("check", fail_level="ERROR")


def test_settings_module_is_importable() -> None:
    import django.conf

    assert django.conf.settings.configured
    assert django.conf.settings.USE_TZ is True
    assert django.conf.settings.TIME_ZONE == "UTC"


@pytest.mark.django_db
def test_migrations_are_consistent() -> None:
    """No model changes are missing a migration."""
    from io import StringIO

    out = StringIO()
    call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
