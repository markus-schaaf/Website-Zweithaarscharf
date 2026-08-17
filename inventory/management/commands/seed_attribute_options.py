"""Legt Start-Auswahlwerte fuer die Erfassung an. Platzhalter - in der
Warenwirtschaft frei anpassbar.
Aufruf:  python manage.py seed_attribute_options
"""

from django.core.management.base import BaseCommand

from inventory.models import AttributeOption

G = AttributeOption.Group

DEFAULTS = {
    G.FARBE: [
        "Naturblond", "Hellblond", "Aschblond", "Karamell",
        "Naturbraun", "Hellbraun", "Dunkelbraun", "Kastanienbraun",
        "Rotbraun", "Kupfer", "Mahagoni",
        "Grau meliert", "Silbergrau", "Schwarz",
    ],
    G.LAENGE: [
        "20 cm", "25 cm", "30 cm", "35 cm", "40 cm", "45 cm", "50 cm", "60 cm",
    ],
    G.SCHNITT: [
        "Glatt", "Glatt gestuft", "Bob", "Kurzhaarschnitt",
        "Gewellt", "Lockig",
    ],
    G.MONTUR: [
        "Tresse", "Tressenmontur mit Monofilament-Scheitel", "Monofilament",
        "Filmansatz", "Vollmontur handgeknüpft", "Integrationsmontur",
    ],
    G.DICHTE: ["Leicht", "Mittel", "Voll", "Extra voll"],
    G.GROESSE: [
        "52-54 cm", "54-56 cm", "56-58 cm", "Oberkopf/Scheitel",
    ],
}


class Command(BaseCommand):
    help = "Legt Standard-Auswahlwerte an (nur falls noch nicht vorhanden)."

    def handle(self, *args, **options):
        created = total = 0
        for group, values in DEFAULTS.items():
            for i, name in enumerate(values, start=1):
                _, was_created = AttributeOption.objects.get_or_create(
                    group=group, name=name, defaults={"sort_order": i}
                )
                created += int(was_created)
                total += 1
        self.stdout.write(self.style.SUCCESS(
            f"{created} neue Auswahlwert(e) angelegt, {total - created} bereits vorhanden."
        ))
