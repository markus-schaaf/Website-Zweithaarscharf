"""Doppelte erste Miniatur auf der Produktseite bereinigen.

inventory.StockItem.sync_to_product() hat das erste Verkaufsbild sowohl als
Product.image als auch als ProductImage angelegt. Die Produktseite zeigt das
Hauptbild und danach die Galerie - das erste Foto erschien dadurch zweimal.
Die Ursache ist behoben; hier fallen die bereits angelegten Doppel weg.
"""

from django.db import migrations
from django.db.models import F


def doppelte_entfernen(apps, schema_editor):
    ProductImage = apps.get_model("shop", "ProductImage")
    ProductImage.objects.filter(image=F("product__image")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0011_product_track_stock"),
    ]

    operations = [
        migrations.RunPython(doppelte_entfernen, migrations.RunPython.noop),
    ]
