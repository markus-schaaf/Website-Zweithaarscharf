from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

PASSWORD = "Test1234!"

DUMMY_USERS = [
    ("b2c@test.de", "Clara", "Consumer", User.Role.B2C, {}),
    (
        "b2b@test.de",
        "Bianca",
        "Business",
        User.Role.B2B,
        {
            "company_name": "Friseur Meisterbetrieb Muster GmbH",
            "vat_id": "DE123456789",
            "phone": "02676 1234-0",
            "street": "Musterstraße 12",
            "zip_code": "56766",
            "city": "Ulmen",
        },
    ),
    ("allpower@test.de", "Alina", "Power", User.Role.ALL_POWER, {}),
    ("admin@test.de", "Adrian", "Admin", User.Role.ADMIN, {}),
]


class Command(BaseCommand):
    help = (
        "Legt Dummy-Accounts zum Testen an (idempotent). "
        f"Passwort für alle: {PASSWORD} — "
        "b2c@test.de (B2C), b2b@test.de (B2B), "
        "allpower@test.de (All Power), admin@test.de (Admin)."
    )

    def handle(self, *args, **options):
        # Legacy: user@test.de in-place umbenennen (Warenkorb bleibt erhalten)
        legacy = User.objects.filter(email="user@test.de").first()
        if legacy:
            if User.objects.filter(email="b2c@test.de").exists():
                self.stdout.write(
                    "user@test.de existiert weiterhin — bitte manuell prüfen"
                )
            else:
                legacy.email = "b2c@test.de"
                legacy.first_name = "Clara"
                legacy.last_name = "Consumer"
                legacy.save()
                self.stdout.write(
                    "user@test.de -> b2c@test.de umbenannt (Warenkorb bleibt erhalten)"
                )

        for email, first_name, last_name, role, extra in DUMMY_USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": role,
                    **extra,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
            status = "angelegt" if created else "bereits vorhanden"
            self.stdout.write(f"{email} ({user.get_role_display()}): {status}")
