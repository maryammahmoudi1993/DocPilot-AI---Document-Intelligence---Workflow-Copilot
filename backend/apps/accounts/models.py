from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager["User"]):
    """Email-based user manager — this project logs in by email, not a
    separate username (see User.USERNAME_FIELD)."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields) -> "User":
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user: User = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model, introduced before any migration has ever been
    applied to a real database in this project — see
    docs/adr/0002-custom-user-model.md for why now is the safe time to do
    this rather than migrating an existing users table later.
    """

    email = models.EmailField("email address", unique=True)
    # Convenience pointer only — never an authorization source. Every
    # workspace-scoped endpoint re-validates real WorkspaceMembership
    # rows on every request (see apps/workspaces/permissions.py); this
    # field just tells the frontend which workspace to preselect.
    active_workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    # django-stubs types AbstractUser.objects as the *default*
    # UserManager; overriding it with our own is the standard custom-user
    # pattern, but the stub can't express "this subclass replaces it" —
    # see django-stubs' own docs on custom user managers.
    objects = UserManager()  # type: ignore[assignment,misc]

    def save(self, *args, **kwargs) -> None:
        # `username` is unique but unused (email is USERNAME_FIELD).
        # UserManager.create_user() defaults it to the email, but that
        # manager method isn't the only way a User row gets created —
        # get_or_create(), factory_boy, fixtures, and the Django admin's
        # "add user" form all construct the model directly. Defaulting it
        # here too means every creation path is safe, not just the one
        # someone remembered to route through create_user().
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email
