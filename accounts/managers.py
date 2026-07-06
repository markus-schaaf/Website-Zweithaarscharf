from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager fuer das E-Mail-basierte User-Model (ohne username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("E-Mail-Adresse ist erforderlich")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", self.model.Role.B2C)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = self.model.Role.ADMIN
        return self._create_user(email, password, **extra_fields)
