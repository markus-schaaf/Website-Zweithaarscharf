from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        B2C = "B2C", "B2C-Kunde"
        B2B = "B2B", "B2B-Kunde"
        ALL_POWER = "ALL_POWER", "All Power"
        ADMIN = "ADMIN", "Administrator"

    username = None
    email = models.EmailField("E-Mail-Adresse", unique=True)
    role = models.CharField(
        "Rolle", max_length=10, choices=Role.choices, default=Role.B2C
    )

    # Firmendaten (nur fuer B2B-Konten gefuellt)
    company_name = models.CharField("Firmenname", max_length=120, blank=True)
    vat_id = models.CharField("USt-IdNr.", max_length=20, blank=True)
    phone = models.CharField("Telefon", max_length=40, blank=True)
    street = models.CharField("Straße und Hausnummer", max_length=120, blank=True)
    zip_code = models.CharField("PLZ", max_length=10, blank=True)
    city = models.CharField("Ort", max_length=80, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Benutzer"
        verbose_name_plural = "Benutzer"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Die Rolle ist die einzige Quelle fuer den /admin/-Zugang:
        # manuelle is_staff/is_superuser-Aenderungen werden ueberschrieben.
        is_admin = self.role == self.Role.ADMIN
        self.is_staff = is_admin
        self.is_superuser = is_admin
        super().save(*args, **kwargs)

    @property
    def can_view_users(self):
        return self.role in (self.Role.ALL_POWER, self.Role.ADMIN)

    @property
    def can_manage_users(self):
        return self.role == self.Role.ADMIN

    @property
    def can_manage_products(self):
        return self.role in (self.Role.ALL_POWER, self.Role.ADMIN)

    @property
    def can_see_b2b_products(self):
        # Verwaltungsrollen sehen B2B-Produkte, um die Listings pruefen zu koennen
        return self.role in (self.Role.B2B, self.Role.ALL_POWER, self.Role.ADMIN)
