import pytest

from apps.accounts.models import User


@pytest.mark.django_db
def test_create_user_normalizes_email_and_sets_username_default():
    user = User.objects.create_user(email="Person@Example.com", password="s3cret-pass")

    assert user.email == "Person@example.com"
    assert user.username == "Person@example.com"
    assert user.check_password("s3cret-pass")
    assert not user.is_staff
    assert not user.is_superuser


@pytest.mark.django_db
def test_create_superuser_sets_staff_and_superuser_flags():
    user = User.objects.create_superuser(email="root@example.com", password="s3cret-pass")

    assert user.is_staff
    assert user.is_superuser


def test_create_user_requires_an_email():
    with pytest.raises(ValueError, match="email"):
        User.objects.create_user(email="", password="s3cret-pass")


@pytest.mark.django_db
def test_user_str_is_its_email():
    user = User.objects.create_user(email="person@example.com", password="s3cret-pass")

    assert str(user) == "person@example.com"


@pytest.mark.django_db
def test_username_defaults_to_email_even_when_bypassing_the_manager():
    """get_or_create()/factory_boy/admin all construct User() directly,
    skipping UserManager.create_user() — save() must still default
    username, or the second such user collides on its unique constraint
    (this was a real bug: both the demo-data seed command and the test
    factory hit it before this was fixed)."""
    first = User.objects.get_or_create(email="a@example.com")[0]
    second = User.objects.get_or_create(email="b@example.com")[0]

    assert first.username == "a@example.com"
    assert second.username == "b@example.com"
