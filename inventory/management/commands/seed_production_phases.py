"""Legt Start-Fertigungsphasen an. Platzhalter - im Admin frei anpassbar.
Aufruf:  python manage.py seed_production_phases
"""

from django.core.management.base import BaseCommand

from inventory.models import ProductionPhase

DEFAULTS = [
    "Rohling",
    "Knüpfen",
    "Schnitt",
    "Färben",
    "Finish",
    "Qualitätskontrolle",
]


class Command(BaseCommand):
    help = "Legt Standard-Fertigungsphasen an (nur falls noch nicht vorhanden)."

    def handle(self, *args, **options):
        created = 0
        for i, name in enumerate(DEFAULTS, start=1):
            _, was_created = ProductionPhase.objects.get_or_create(
                name=name, defaults={"sort_order": i}
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"{created} neue Phase(n) angelegt, {len(DEFAULTS) - created} bereits vorhanden."
        ))
