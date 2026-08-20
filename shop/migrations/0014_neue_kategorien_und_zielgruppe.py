"""Kategorien beschreiben ab jetzt nur noch die Warenart.

bestand/rohling gehen in echthaar_peruecke auf, topholder in zubehoer. Die
Zielgruppe wird dreiwertig: der alte Wert b2c hiess "Alle Kunden" und wird
deshalb zu alle; b2b bleibt b2b.
"""

from django.db import migrations

KATEGORIEN = {
    "bestand": "echthaar_peruecke",
    "rohling": "echthaar_peruecke",
    "topholder": "zubehoer",
}

NEUE_KATEGORIEN = (
    "echthaar_peruecke", "echthaar_topper",
    "kunsthaar_peruecke", "kunsthaar_topper",
)


def _slug_umschreiben(Product, product, alt, neu):
    """Slug-Prefix mitziehen - seed_products baut den Slug aus der Kategorie,
    ohne Rewrite entstuenden beim naechsten Seed Duplikate (siehe 0004).
    """
    if not product.slug.startswith(alt + "-"):
        return
    base = (neu + "-" + product.slug[len(alt) + 1:])[:80]
    slug, i = base, 2
    while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
        slug = f"{base[:70]}-{i}"
        i += 1
    product.slug = slug


def vorwaerts(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    # Zuerst die Zielgruppe: sonst waeren die Rohlinge nach dem Umzug der
    # Kategorie nicht mehr als B2B-Ware erkennbar.
    Product.objects.filter(audience="b2c").update(audience="alle")
    for alt, neu in KATEGORIEN.items():
        for product in Product.objects.filter(category=alt):
            product.category = neu
            _slug_umschreiben(Product, product, alt, neu)
            product.save(update_fields=["category", "slug"])


def rueckwaerts(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    for product in Product.objects.filter(category__in=NEUE_KATEGORIEN):
        alt = product.category
        product.category = "bestand"
        _slug_umschreiben(Product, product, alt, "bestand")
        product.save(update_fields=["category", "slug"])
    Product.objects.filter(audience="alle").update(audience="b2c")


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0013_alter_product_audience_alter_product_category"),
    ]

    operations = [
        migrations.RunPython(vorwaerts, rueckwaerts),
    ]
