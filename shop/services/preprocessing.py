"""Bildvorverarbeitung für die 3D-Generierung:
Haare freistellen (rembg) und auf einen neutralen Dummy-Kopf setzen (Pillow).
"""

import io

from django.contrib.staticfiles import finders
from PIL import Image

DUMMY_HEAD_STATIC_PATH = "images/3d/dummy-head.png"

# Freisteller-Breite relativ zur Dummy-Kopf-Breite (Perücke ragt seitlich über den Kopf)
DEFAULT_HAIR_WIDTH_RATIO = 0.85
# Oberkante des Freistellers relativ zur Bildhöhe (Haaransatz sitzt oberhalb der Stirn)
DEFAULT_ANCHOR_Y_RATIO = 0.12
# Kantenlänge des Ergebnisbilds (Base64-Data-URI-Limit der Provider-APIs)
MAX_COMPOSITE_SIZE = 1024


def remove_background(image_bytes):
    """Entfernt den Hintergrund, gibt RGBA-PIL-Image mit Transparenz zurück."""
    # rembg lädt onnxruntime + ML-Modell: teurer Import, nur bei Bedarf
    from rembg import remove

    cutout = remove(Image.open(io.BytesIO(image_bytes)))
    return cutout.convert("RGBA")


def composite_on_dummy_head(cutout, offset_x=0.0, offset_y=0.0, scale=1.0):
    """Setzt den Freisteller auf das Dummy-Kopf-Bild, gibt PNG-Bytes zurück.

    offset_x/offset_y verschieben in Anteilen der Kopfbild-Breite/-Höhe,
    scale multipliziert die Standardgröße (1.0 = Heuristik unverändert).
    """
    head_path = finders.find(DUMMY_HEAD_STATIC_PATH)
    if not head_path:
        raise FileNotFoundError(
            f"Dummy-Kopf-Bild fehlt: static/{DUMMY_HEAD_STATIC_PATH}"
        )
    head = Image.open(head_path).convert("RGBA")

    bbox = cutout.getbbox()
    if not bbox:
        raise ValueError("Freisteller ist leer (rembg hat nichts erkannt).")
    hair = cutout.crop(bbox)

    target_width = int(head.width * DEFAULT_HAIR_WIDTH_RATIO * scale)
    target_height = int(hair.height * target_width / hair.width)
    hair = hair.resize((max(target_width, 1), max(target_height, 1)), Image.LANCZOS)

    paste_x = int((head.width - hair.width) / 2 + offset_x * head.width)
    paste_y = int(head.height * DEFAULT_ANCHOR_Y_RATIO + offset_y * head.height)

    composite = head.copy()
    composite.alpha_composite(hair, (paste_x, paste_y))

    composite.thumbnail((MAX_COMPOSITE_SIZE, MAX_COMPOSITE_SIZE), Image.LANCZOS)
    # Weißer Hintergrund statt Alpha: Provider erwarten ein normales Produktfoto
    flattened = Image.new("RGB", composite.size, (255, 255, 255))
    flattened.paste(composite, mask=composite.getchannel("A"))

    buffer = io.BytesIO()
    flattened.save(buffer, format="PNG")
    return buffer.getvalue()


def prepare_source_image(image_bytes, offset_x=0.0, offset_y=0.0, scale=1.0):
    """Komplette Vorverarbeitung eines Quellfotos: freistellen + auf Dummy-Kopf setzen."""
    cutout = remove_background(image_bytes)
    return composite_on_dummy_head(cutout, offset_x, offset_y, scale)
