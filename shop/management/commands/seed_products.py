from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import ConfiguratorGroup, ConfiguratorOption, Product
from zweithaarschaaf.demo_products import (
    B2B_PRODUCTS,
    CONFIGURATOR_GROUPS,
    ECHTHAAR_PERUECKE_PRODUCTS,
    ECHTHAAR_TOPPER_PRODUCTS,
    KONFIG_PRODUCTS,
    KUNSTHAAR_PERUECKE_PRODUCTS,
    KUNSTHAAR_TOPPER_PRODUCTS,
    PFLEGE_PRODUCTS,
    TOPHOLDER_PRODUCTS,
    ZUBEHOER_PRODUCTS,
)

ATTRIBUTE_FIELDS = (
    "hair_length",
    "hair_size",
    "hair_color",
    "hair_structure",
    "hair_density",
    "cap_type",
    "content_amount",
    "usage_notes",
)


class Command(BaseCommand):
    help = (
        "Schreibt die Demo-Produkte und den Konfigurator-Katalog aus "
        "demo_products.py idempotent in die Datenbank (bestehende "
        "Einträge werden nicht überschrieben)."
    )

    def handle(self, *args, **options):
        created_count = 0
        for category, products in (
            (Product.Category.KONFIG, KONFIG_PRODUCTS),
            (Product.Category.ECHTHAAR_PERUECKE, ECHTHAAR_PERUECKE_PRODUCTS),
            (Product.Category.ECHTHAAR_PERUECKE, B2B_PRODUCTS),
            (Product.Category.ECHTHAAR_TOPPER, ECHTHAAR_TOPPER_PRODUCTS),
            (Product.Category.KUNSTHAAR_PERUECKE, KUNSTHAAR_PERUECKE_PRODUCTS),
            (Product.Category.KUNSTHAAR_TOPPER, KUNSTHAAR_TOPPER_PRODUCTS),
            (Product.Category.ZUBEHOER, ZUBEHOER_PRODUCTS),
            (Product.Category.ZUBEHOER, TOPHOLDER_PRODUCTS),
            (Product.Category.PFLEGE, PFLEGE_PRODUCTS),
        ):
            for index, entry in enumerate(products):
                slug = slugify(f"{category}-{entry['label']}")
                defaults = {
                    "name": entry["display_name"],
                    "label": entry["label"],
                    "category": category,
                    "audience": entry.get("audience", Product.Audience.ALLE),
                    "price": Decimal(entry["price"].replace(".", "")),
                    "badge": entry["badge"] or "",
                    "description": entry["desc"],
                    "sort_order": index,
                    "is_active": True,
                }
                for field in ATTRIBUTE_FIELDS:
                    defaults[field] = entry.get(field, "")
                # Demodaten: bestehende Zeilen werden aktualisiert (Werte auffrischen).
                _, created = Product.objects.update_or_create(
                    slug=slug, defaults=defaults
                )
                if created:
                    created_count += 1
                status = "angelegt" if created else "aktualisiert"
                self.stdout.write(f"{slug}: {status}")

        option_count = 0
        for group_index, group_entry in enumerate(CONFIGURATOR_GROUPS):
            group, _ = ConfiguratorGroup.objects.get_or_create(
                name=group_entry["name"], defaults={"sort_order": group_index}
            )
            for option_index, (name, surcharge) in enumerate(group_entry["options"]):
                _, created = ConfiguratorOption.objects.get_or_create(
                    group=group,
                    name=name,
                    defaults={
                        "surcharge": Decimal(surcharge),
                        "sort_order": option_index,
                    },
                )
                if created:
                    option_count += 1

        self.stdout.write(
            f"Fertig: {created_count} Produkte neu angelegt "
            f"({Product.objects.count()} insgesamt), "
            f"{option_count} Konfigurator-Optionen neu angelegt "
            f"({ConfiguratorOption.objects.count()} insgesamt)."
        )
