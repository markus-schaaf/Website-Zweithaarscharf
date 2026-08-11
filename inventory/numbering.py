"""Vergabe der eigenen Produktnummer, Format: EW-BLO-50-0001
(Hersteller-Kuerzel, Farbe auf 3 Zeichen, Laenge in cm, laufende Nummer).
"""

import re
import unicodedata

from django.db import transaction

from .models import Supplier

UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _color_part(color):
    plain = unicodedata.normalize("NFKD", color.lower().translate(UMLAUTE))
    letters = re.sub(r"[^a-z]", "", plain).upper()
    return letters[:3].ljust(3, "X")


def _length_part(length):
    match = re.search(r"(\d+)", length or "")
    return match.group(1) if match else "XX"


def build_inventory_no(supplier, color, length, counter):
    return (
        f"{supplier.code.upper()}-{_color_part(color)}-"
        f"{_length_part(length)}-{counter:04d}"
    )


def reserve_numbers(supplier, count):
    """Sperrt den Lieferanten und reserviert count laufende Nummern."""
    with transaction.atomic():
        locked = Supplier.objects.select_for_update().get(pk=supplier.pk)
        start = locked.next_number
        locked.next_number = start + count
        locked.save(update_fields=["next_number"])
    return list(range(start, start + count))
