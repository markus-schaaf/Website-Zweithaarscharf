"""Gegenstueck zu shop.0014 fuer die Bestandsstuecke."""

from django.db import migrations

KATEGORIEN = {
    "bestand": "echthaar_peruecke",
    "rohling": "echthaar_peruecke",
    "topholder": "zubehoer",
}


def vorwaerts(apps, schema_editor):
    StockItem = apps.get_model("inventory", "StockItem")
    StockItem.objects.filter(audience="b2c").update(audience="alle")
    for alt, neu in KATEGORIEN.items():
        StockItem.objects.filter(shop_category=alt).update(shop_category=neu)


def rueckwaerts(apps, schema_editor):
    StockItem = apps.get_model("inventory", "StockItem")
    StockItem.objects.filter(
        shop_category__in=(
            "echthaar_peruecke", "echthaar_topper",
            "kunsthaar_peruecke", "kunsthaar_topper",
        )
    ).update(shop_category="bestand")
    StockItem.objects.filter(audience="alle").update(audience="b2c")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0010_alter_stockitem_audience_and_more"),
        ("shop", "0014_neue_kategorien_und_zielgruppe"),
    ]

    operations = [
        migrations.RunPython(vorwaerts, rueckwaerts),
    ]
