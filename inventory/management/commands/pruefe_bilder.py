"""Meldet Bilddatensaetze, deren Datei fehlt oder nicht lesbar ist.

Aufruf:  python manage.py pruefe_bilder

Hintergrund: Vor der HEIC-Umstellung wurden iPhone-Fotos unveraendert
gespeichert. Die Datensaetze sind in Ordnung, die Dateien aber in keinem
Browser darstellbar. Dieser Befehl zeigt, was neu hochgeladen werden muss.
"""

from django.core.management.base import BaseCommand
from PIL import Image, UnidentifiedImageError

from inventory.models import StockItemImage
from shop.models import ProductImage


class Command(BaseCommand):
    help = "Prüft alle hinterlegten Bilddateien auf Existenz und Lesbarkeit."

    def handle(self, *args, **options):
        gesamt = kaputt = 0
        for modell, bezeichnung in (
            (StockItemImage, "Bestand"),
            (ProductImage, "Shop-Galerie"),
        ):
            for bild in modell.objects.select_related().iterator():
                gesamt += 1
                problem = self._pruefe(bild.image)
                if problem:
                    kaputt += 1
                    self.stdout.write(self.style.WARNING(
                        f"{bezeichnung} #{bild.pk}: {bild.image.name} - {problem}"
                    ))

        if kaputt:
            self.stdout.write(self.style.ERROR(
                f"\n{kaputt} von {gesamt} Bildern sind nicht darstellbar. "
                "Diese Fotos bitte neu hochladen."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Alle {gesamt} Bilder sind vorhanden und lesbar."
            ))

    @staticmethod
    def _pruefe(feld):
        if not feld:
            return "kein Dateiname hinterlegt"
        try:
            if not feld.storage.exists(feld.name):
                return "Datei fehlt auf der Platte"
        except (NotImplementedError, ValueError):
            return "Speicherort nicht pruefbar"
        try:
            with feld.open("rb") as datei:
                Image.open(datei).verify()
        except UnidentifiedImageError:
            return "kein lesbares Bildformat (vermutlich HEIC von vor der Umstellung)"
        except OSError as fehler:
            return f"nicht lesbar ({fehler})"
        return None
