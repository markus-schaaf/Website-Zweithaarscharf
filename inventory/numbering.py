"""Vergabe der eigenen Produktnummer.

Haarware: EW-BLO-50-0001 (Hersteller-Kuerzel, Farbe auf 3 Zeichen, Laenge in
cm, laufende Nummer). Zubehoer und Pflegeprodukte haben weder Farbe noch
Laenge, dort steht der Produktname an dieser Stelle: EW-SHA-0001.
"""

import re
import unicodedata

from django.db import transaction

from .models import Supplier

UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _letter_part(text):
    plain = unicodedata.normalize("NFKD", (text or "").lower().translate(UMLAUTE))
    letters = re.sub(r"[^a-z]", "", plain).upper()
    return letters[:3].ljust(3, "X")


def _length_part(length):
    match = re.search(r"(\d+)", length or "")
    return match.group(1) if match else "XX"


def build_inventory_no(supplier, color, length, counter, product_name=""):
    code = supplier.code.upper()
    if not color and not length:
        return f"{code}-{_letter_part(product_name)}-{counter:04d}"
    return f"{code}-{_letter_part(color)}-{_length_part(length)}-{counter:04d}"


def reserve_numbers(supplier, count):
    """Sperrt den Lieferanten und reserviert count laufende Nummern."""
    with transaction.atomic():
        locked = Supplier.objects.select_for_update().get(pk=supplier.pk)
        start = locked.next_number
        locked.next_number = start + count
        locked.save(update_fields=["next_number"])
    return list(range(start, start + count))
