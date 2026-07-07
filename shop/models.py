from decimal import Decimal

from django.conf import settings
from django.db import models

MAX_QTY = 99


class ProductQuerySet(models.QuerySet):
    def visible_for(self, user):
        """Aktive Produkte, die dieser Besucher sehen darf (user darf anonym sein).

        B2B-Produkte sehen nur B2B-Kunden sowie All Power/Admin (Pruefrecht);
        alle anderen (inkl. anonym) sehen nur die B2C-Produkte.
        """
        qs = self.filter(is_active=True)
        if user.is_authenticated and user.can_see_b2b_products:
            return qs
        return qs.filter(audience=Product.Audience.B2C)


class Product(models.Model):
    class Category(models.TextChoices):
        KONFIG = "konfig", "Echthaarperücken konfigurierbar"
        BESTAND = "bestand", "Echthaarperücken im Bestand"
        PFLEGE = "pflege", "Pflegeprodukte"
        ROHLING = "rohling", "Rohlinge (B2B)"

    class Audience(models.TextChoices):
        B2C = "b2c", "Alle Kunden"
        B2B = "b2b", "Nur B2B"

    class Badge(models.TextChoices):
        NEW = "new", "Neu"
        POPULAR = "popular", "Beliebt"

    name = models.CharField("Name", max_length=120)
    label = models.CharField("Kurzlabel", max_length=60)
    slug = models.SlugField(max_length=80, unique=True)
    category = models.CharField("Kategorie", max_length=10, choices=Category.choices)
    audience = models.CharField(
        "Zielgruppe", max_length=3, choices=Audience.choices, default=Audience.B2C
    )
    price = models.DecimalField("Preis (ab)", max_digits=8, decimal_places=2)
    badge = models.CharField("Badge", max_length=10, choices=Badge.choices, blank=True, default="")
    description = models.TextField("Beschreibung", blank=True)
    image = models.ImageField("Produktbild", upload_to="products/", blank=True)

    # Produktattribute fuer die Detailseite (optional, je nach Kategorie relevant)
    hair_length = models.CharField("Haarlänge", max_length=60, blank=True, default="")
    hair_color = models.CharField("Haarfarbe", max_length=80, blank=True, default="")
    hair_structure = models.CharField("Haarstruktur", max_length=60, blank=True, default="")
    cap_type = models.CharField("Monturart", max_length=80, blank=True, default="")
    hair_origin = models.CharField("Haarherkunft", max_length=80, blank=True, default="")
    care_notes = models.TextField("Pflegehinweise", blank=True, default="")
    content_amount = models.CharField("Inhalt / Menge", max_length=40, blank=True, default="")
    usage_notes = models.TextField("Anwendung", blank=True, default="")

    is_active = models.BooleanField("Aktiv", default=True)
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "Produkt"
        verbose_name_plural = "Produkte"
        ordering = ["category", "sort_order", "id"]

    def __str__(self):
        return self.name

    @property
    def price_display(self):
        """Ganze Euro mit deutschem Tausenderpunkt, z. B. '1.190'."""
        return f"{int(self.price):,}".replace(",", ".")

    @property
    def is_configurable(self):
        """Konfigurierbare Perücken: nur Rohpreis, Kauf nur nach Beratungstermin."""
        return self.category == self.Category.KONFIG

    @property
    def is_orderable(self):
        return not self.is_configurable

    # Illustrations-Fallback je Kategorie, solange kein echtes Foto hochgeladen ist
    PLACEHOLDER_IMAGES = {
        Category.KONFIG: "images/wigs/wig-curly-volume.svg",
        Category.BESTAND: "images/wigs/wig-classic.svg",
        Category.ROHLING: "images/wigs/wig-long-layers.svg",
    }

    @property
    def placeholder_image(self):
        """Statischer Pfad einer Illustration, wenn kein Produktbild existiert (sonst None)."""
        return self.PLACEHOLDER_IMAGES.get(self.category)

    @property
    def public_3d_asset(self):
        """Neuestes fertiges und freigegebenes 3D-Modell (sonst None)."""
        return self.assets_3d.filter(
            status=Product3DAsset.Status.DONE, is_public=True
        ).first()

    @property
    def detail_attributes(self):
        """(Label, Wert)-Paare fuer die Detailseite — nur befuellte Felder."""
        if self.category == self.Category.PFLEGE:
            field_names = ("content_amount", "usage_notes")
        else:
            field_names = (
                "hair_length",
                "hair_color",
                "hair_structure",
                "cap_type",
                "hair_origin",
                "care_notes",
            )
        rows = []
        for field_name in field_names:
            value = getattr(self, field_name)
            if value:
                rows.append((self._meta.get_field(field_name).verbose_name, value))
        return rows


class Product3DAsset(models.Model):
    """Generiertes 3D-Modell (GLB) eines Produkts inkl. Quellbildern und Status.

    Quellbilder als vier Einzelfelder statt eigenem Bild-Model: das
    Provider-Limit ist fix 1-4 Bilder, so bleiben Form und Views trivial.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Wartet"
        PROCESSING = "processing", "In Bearbeitung"
        DONE = "done", "Fertig"
        FAILED = "failed", "Fehlgeschlagen"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="assets_3d"
    )
    source_image_1 = models.ImageField("Quellbild 1", upload_to="products/3d/sources/")
    source_image_2 = models.ImageField(
        "Quellbild 2", upload_to="products/3d/sources/", blank=True
    )
    source_image_3 = models.ImageField(
        "Quellbild 3", upload_to="products/3d/sources/", blank=True
    )
    source_image_4 = models.ImageField(
        "Quellbild 4", upload_to="products/3d/sources/", blank=True
    )
    status = models.CharField(
        "Status", max_length=12, choices=Status.choices, default=Status.PENDING
    )
    model_file = models.FileField(
        "3D-Modell (GLB)", upload_to="products/3d/models/", blank=True
    )
    preview_thumbnail = models.ImageField(
        "Vorschaubild", upload_to="products/3d/thumbs/", blank=True
    )
    error_message = models.TextField("Fehlermeldung", blank=True, default="")
    is_public = models.BooleanField("Für Kunden sichtbar", default=False)
    provider = models.CharField("3D-Dienst", max_length=30, blank=True, default="")
    provider_job_id = models.CharField(max_length=100, blank=True, default="")

    # Feinjustierung des Compositings auf den Dummy-Kopf
    # (Anteile der Kopfbild-Breite/-Höhe bzw. Skalierungsfaktor)
    comp_offset_x = models.FloatField("Versatz X", default=0.0)
    comp_offset_y = models.FloatField("Versatz Y", default=0.0)
    comp_scale = models.FloatField("Skalierung", default=1.0)

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "3D-Modell"
        verbose_name_plural = "3D-Modelle"
        ordering = ["-created_at"]

    def __str__(self):
        return f"3D-Modell für {self.product} ({self.get_status_display()})"

    @property
    def source_images(self):
        return [
            f
            for f in (
                self.source_image_1,
                self.source_image_2,
                self.source_image_3,
                self.source_image_4,
            )
            if f
        ]


class ConfiguratorGroup(models.Model):
    """Merkmal des Perücken-Konfigurators, z. B. 'Haarlänge'."""

    name = models.CharField("Name", max_length=60, unique=True)
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Konfigurator-Gruppe"
        verbose_name_plural = "Konfigurator-Gruppen"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class ConfiguratorOption(models.Model):
    """Auswahl innerhalb einer Gruppe, z. B. '50 cm' mit Aufpreis."""

    group = models.ForeignKey(
        ConfiguratorGroup, on_delete=models.CASCADE, related_name="options"
    )
    name = models.CharField("Bezeichnung", max_length=80)
    surcharge = models.DecimalField(
        "Aufpreis", max_digits=8, decimal_places=2, default=Decimal("0")
    )
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Konfigurator-Option"
        verbose_name_plural = "Konfigurator-Optionen"
        ordering = ["group", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["group", "name"], name="uniq_group_option")
        ]

    def __str__(self):
        return f"{self.group.name}: {self.name}"


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Warenkorb"
        verbose_name_plural = "Warenkörbe"

    def __str__(self):
        return f"Warenkorb von {self.user}"

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Menge", default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Warenkorb-Position"
        verbose_name_plural = "Warenkorb-Positionen"
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="uniq_cart_product")
        ]
        ordering = ["added_at", "id"]

    def __str__(self):
        return f"{self.quantity}x {self.product}"

    @property
    def line_total(self):
        return self.product.price * self.quantity
