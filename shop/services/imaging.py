"""Hochgeladene Fotos in ein anzeigbares Format bringen.

Hintergrund: Die Pflege laeuft ueber iPhones. Deren Standardformat ist HEIC,
das weder Chrome/Firefox/Edge noch Pillow von Haus aus darstellen koennen -
solche Dateien landeten frueher unveraendert im Medienordner und waren danach
unsichtbar. Deshalb wird jedes Bild beim Hochladen einmal durch Pillow
geschickt und als JPEG abgelegt.

Nebenbei erledigt das drei weitere iPhone-Eigenheiten:
- EXIF-Drehung wird eingerechnet (Hochkantfotos lagen sonst quer)
- 48-Megapixel-Aufnahmen werden auf eine vernuenftige Kantenlaenge gebracht
- Transparenz wird auf Weiss gelegt, weil JPEG keinen Alphakanal kann
"""

import io
import os

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

# HEIC/HEIF-Unterstuetzung in Pillow nachruesten (iPhone-Standardformat).
# Der Aufruf ist idempotent und muss vor dem ersten Image.open() passieren.
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover - nur wenn die Abhaengigkeit fehlt
    pass

# Laengste Kante des gespeicherten Bilds. 2200 px reichen fuer die
# Produktdetailseite und fuer Zoom, sparen aber gegenueber 48 MP das Vielfache
# an Speicher und Ladezeit.
MAX_KANTE = 2200
JPEG_QUALITAET = 85


def normalize_upload(datei, max_kante=MAX_KANTE, qualitaet=JPEG_QUALITAET):
    """Beliebiges Foto als JPEG-ContentFile zurueckgeben.

    Wirft ValidationError mit einer verstaendlichen Meldung, wenn die Datei
    kein lesbares Bild ist - der Aufrufer zeigt sie im Formular an.
    """
    try:
        datei.seek(0)
        bild = Image.open(datei)
        bild.load()
    except UnidentifiedImageError:
        raise ValidationError(
            f"„{datei.name}“ ist kein lesbares Bild und wurde nicht übernommen."
        )
    except OSError as fehler:
        raise ValidationError(
            f"„{datei.name}“ konnte nicht gelesen werden ({fehler})."
        )

    # Hochkantaufnahmen tragen die Drehung nur in den EXIF-Daten
    bild = ImageOps.exif_transpose(bild)

    if bild.mode in ("RGBA", "LA", "P"):
        bild = bild.convert("RGBA")
        hintergrund = Image.new("RGB", bild.size, (255, 255, 255))
        hintergrund.paste(bild, mask=bild.split()[-1])
        bild = hintergrund
    elif bild.mode != "RGB":
        bild = bild.convert("RGB")

    if max(bild.size) > max_kante:
        bild.thumbnail((max_kante, max_kante), Image.LANCZOS)

    puffer = io.BytesIO()
    bild.save(puffer, format="JPEG", quality=qualitaet, optimize=True, progressive=True)
    return ContentFile(puffer.getvalue(), name=_jpeg_name(datei.name))


def normalize_uploads(dateien):
    """Mehrere Uploads umwandeln. Sammelt alle Fehler in einer ValidationError,
    damit die Nutzerin nicht Datei fuer Datei durchprobieren muss.
    """
    fertig, fehler = [], []
    for datei in dateien:
        try:
            fertig.append(normalize_upload(datei))
        except ValidationError as problem:
            fehler.extend(problem.messages)
    if fehler:
        raise ValidationError(fehler)
    return fertig


def _jpeg_name(name):
    stamm = os.path.splitext(os.path.basename(name or "foto"))[0]
    return f"{stamm or 'foto'}.jpg"
