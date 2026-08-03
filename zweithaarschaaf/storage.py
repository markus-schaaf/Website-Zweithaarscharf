"""Statisch-Dateien-Storage fuer die Produktion.

Wie WhiteNoise CompressedManifestStaticFilesStorage (inkl. Cache-Busting ueber
gehashte Dateinamen), aber fehlende *referenzierte* Dateien - z. B. nicht
mitgelieferte Theme-Fonts oder Sourcemaps - lassen collectstatic nicht mehr
abbrechen. Sie werden uebersprungen; die betroffene Referenz bleibt unveraendert
(im Zweifel liefert der Browser dafuer ein harmloses 404).
"""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    # Zur Laufzeit: fehlt ein Eintrag im Manifest, den Originalnamen nutzen
    # statt einen Fehler zu werfen.
    manifest_strict = False

    def post_process(self, paths, dry_run=False, **options):
        for name, hashed_name, processed in super().post_process(paths, dry_run, **options):
            if isinstance(processed, Exception):
                # Fehlende Referenz nur ueberspringen, Build nicht abbrechen.
                processed = False
            yield name, hashed_name, processed
