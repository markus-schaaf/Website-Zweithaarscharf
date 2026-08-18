"""Meldet Bilddatensaetze, deren Datei fehlt oder nicht lesbar ist.

Aufruf:  python manage.py pruefe_bilder
         python manage.py pruefe_bilder --aufraeumen

Hintergrund: Vor der HEIC-Umstellung wurden iPhone-Fotos unveraendert
gespeichert. Die Datensaetze sind in Ordnung, die Dateien aber in keinem
Browser darstellbar. Dieser Befehl zeigt, was neu hochgeladen werden muss.

Mit --aufraeumen werden Datensaetze ohne Datei entfernt, damit der Shop statt
eines kaputten Bildes wieder die Illustration zeigt.
"""

from django.core.management.base import BaseCommand
from PIL import Image, UnidentifiedImageError

from inventory.models import StockItemImage
from shop.models import Product, ProductImage

FEHLT = "Datei fehlt auf der Platte"


class Command(BaseCommand):
    help = "Prüft alle hinterlegten Bilddateien auf Existenz und Lesbarkeit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--aufraeumen",
            action="store_true",
            help="Datensätze ohne Datei löschen (Hauptbilder werden geleert).",
        )

    def handle(self, *args, **options):
        aufraeumen = options["aufraeumen"]
        gesamt = kaputt = entfernt = 0

        for modell, bezeichnung in (
            (StockItemImage, "Bestand"),
            (ProductImage, "Shop-Galerie"),
        ):
            for bild in list(modell.objects.select_related().iterator()):
                gesamt += 1
                problem = self._pruefe(bild.image)
                if not problem:
                    continue
                kaputt += 1
                self.stdout.write(self.style.WARNING(
                    f"{bezeichnung} #{bild.pk}: {bild.image.name} - {problem}"
                ))
                if aufraeumen and problem == FEHLT:
                    bild.delete()
                    entfernt += 1

        # Hauptbilder haengen nicht an ProductImage, muessen also einzeln ran
        for produkt in Product.objects.exclude(image=""):
            gesamt += 1
            problem = self._pruefe(produkt.image)
            if not problem:
                continue
            kaputt += 1
            self.stdout.write(self.style.WARNING(
                f"Shop-Hauptbild #{produkt.pk}: {produkt.image.name} - {problem}"
            ))
            if aufraeumen and problem == FEHLT:
                produkt.image = ""
                produkt.save(update_fields=["image"])
                entfernt += 1

        if entfernt:
            self.stdout.write(self.style.SUCCESS(
                f"\n{entfernt} verwaiste Einträge entfernt. Diese Fotos bitte neu "
                "hochladen."
            ))
        elif kaputt:
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
                return FEHLT
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
