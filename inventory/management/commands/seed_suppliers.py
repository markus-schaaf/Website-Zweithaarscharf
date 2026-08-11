"""Legt die Stamm-Hersteller an. Aufruf:  python manage.py seed_suppliers"""

from django.core.management.base import BaseCommand

from inventory.models import Supplier

DEFAULTS = [
    ("EW", "EllenWille"),
    ("DH", "DeuingHair"),
    ("GS", "Glückssträhnen"),
    ("CH", "China"),
    ("BM", "Bergmann"),
]


class Command(BaseCommand):
    help = "Legt die Standard-Hersteller an (nur falls noch nicht vorhanden)."

    def handle(self, *args, **options):
        created = 0
        for code, name in DEFAULTS:
            _, was_created = Supplier.objects.get_or_create(
                code=code, defaults={"name": name}
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"{created} neue(r) Hersteller angelegt, "
            f"{len(DEFAULTS) - created} bereits vorhanden."
        ))
