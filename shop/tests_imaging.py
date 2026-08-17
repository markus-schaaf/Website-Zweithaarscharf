"""Bildnormalisierung: iPhone-Fotos (HEIC), Drehung, Groesse, Fehlerfall."""

import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .services.imaging import MAX_KANTE, normalize_upload, normalize_uploads


def _upload(name, groesse=(40, 30), format="JPEG", farbe="red", exif=None):
    puffer = io.BytesIO()
    bild = Image.new("RGB", groesse, farbe)
    if exif is not None:
        bild.save(puffer, format=format, exif=exif)
    else:
        bild.save(puffer, format=format)
    return SimpleUploadedFile(name, puffer.getvalue(), content_type="image/*")


class NormalizeUploadTest(TestCase):
    def test_heic_wird_zu_jpeg(self):
        """Der eigentliche Fehlerfall: iPhone-Kamera liefert HEIC."""
        datei = _upload("IMG_4711.heic", format="HEIF")
        ergebnis = normalize_upload(datei)
        self.assertEqual(ergebnis.name, "IMG_4711.jpg")
        self.assertEqual(Image.open(ergebnis).format, "JPEG")

    def test_png_mit_transparenz_wird_zu_jpeg(self):
        puffer = io.BytesIO()
        Image.new("RGBA", (20, 20), (255, 0, 0, 0)).save(puffer, format="PNG")
        datei = SimpleUploadedFile("logo.png", puffer.getvalue())
        ergebnis = normalize_upload(datei)
        bild = Image.open(ergebnis)
        self.assertEqual(bild.format, "JPEG")
        self.assertEqual(bild.mode, "RGB")

    def test_jpeg_bleibt_jpeg(self):
        ergebnis = normalize_upload(_upload("foto.jpg"))
        self.assertEqual(ergebnis.name, "foto.jpg")
        self.assertEqual(Image.open(ergebnis).format, "JPEG")

    def test_grosse_aufnahme_wird_verkleinert(self):
        """48-Megapixel-Fotos muessen nicht in Originalgroesse in den Shop."""
        ergebnis = normalize_upload(_upload("gross.jpg", groesse=(5000, 3000)))
        bild = Image.open(ergebnis)
        self.assertEqual(max(bild.size), MAX_KANTE)
        self.assertEqual(bild.size[0] / bild.size[1], 5000 / 3000)

    def test_kleine_aufnahme_bleibt_unveraendert(self):
        ergebnis = normalize_upload(_upload("klein.jpg", groesse=(300, 200)))
        self.assertEqual(Image.open(ergebnis).size, (300, 200))

    def test_exif_drehung_wird_eingerechnet(self):
        """Hochkantfotos vom iPhone tragen die Drehung nur im EXIF."""
        exif = Image.Exif()
        exif[274] = 6  # Orientation: 90 Grad im Uhrzeigersinn drehen
        datei = _upload("hochkant.jpg", groesse=(40, 20), exif=exif.tobytes())
        ergebnis = normalize_upload(datei)
        # Nach dem Anwenden der Drehung sind Breite und Hoehe getauscht
        self.assertEqual(Image.open(ergebnis).size, (20, 40))

    def test_pfad_im_dateinamen_wird_entfernt(self):
        ergebnis = normalize_upload(_upload("C:/Bilder/urlaub.jpg"))
        self.assertEqual(ergebnis.name, "urlaub.jpg")

    def test_keine_bilddatei_meldet_verstaendlich(self):
        datei = SimpleUploadedFile("notiz.txt", b"kein Bild")
        with self.assertRaises(ValidationError) as ctx:
            normalize_upload(datei)
        self.assertIn("notiz.txt", ctx.exception.messages[0])

    def test_mehrere_dateien_sammeln_alle_fehler(self):
        dateien = [
            _upload("gut.jpg"),
            SimpleUploadedFile("kaputt1.jpg", b"nein"),
            SimpleUploadedFile("kaputt2.jpg", b"auch nicht"),
        ]
        with self.assertRaises(ValidationError) as ctx:
            normalize_uploads(dateien)
        self.assertEqual(len(ctx.exception.messages), 2)

    def test_mehrere_gute_dateien(self):
        ergebnis = normalize_uploads([_upload("a.heic", format="HEIF"), _upload("b.png", format="PNG")])
        self.assertEqual([f.name for f in ergebnis], ["a.jpg", "b.jpg"])
