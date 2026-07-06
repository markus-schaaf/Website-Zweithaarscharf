from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import Product
from zweithaarschaaf.demo_products import (
    DAMEN_PRODUCTS,
    HERREN_PRODUCTS,
    PFLEGE_PRODUCTS,
    ROHLING_PRODUCTS,
)


class Command(BaseCommand):
    help = (
        "Schreibt die Demo-Produkte aus demo_products.py idempotent in die "
        "Datenbank (bestehende Produkte werden nicht überschrieben)."
    )

    def handle(self, *args, **options):
        created_count = 0
        for category, products in (
            (Product.Category.DAMEN, DAMEN_PRODUCTS),
            (Product.Category.HERREN, HERREN_PRODUCTS),
            (Product.Category.PFLEGE, PFLEGE_PRODUCTS),
            (Product.Category.ROHLING, ROHLING_PRODUCTS),
        ):
            for index, entry in enumerate(products):
                slug = slugify(f"{category}-{entry['label']}")
                product, created = Product.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name": entry["display_name"],
                        "label": entry["label"],
                        "category": category,
                        "audience": entry.get("audience", Product.Audience.B2C),
                        "price": Decimal(entry["price"].replace(".", "")),
                        "badge": entry["badge"] or "",
                        "description": entry["desc"],
                        "sort_order": index,
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                status = "angelegt" if created else "bereits vorhanden"
                self.stdout.write(f"{slug}: {status}")
        self.stdout.write(
            f"Fertig: {created_count} neu angelegt, "
            f"{Product.objects.count()} Produkte insgesamt."
        )
