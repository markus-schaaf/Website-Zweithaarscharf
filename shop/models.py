import re
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify

MAX_QTY = 99


class ProductQuerySet(models.QuerySet):
    def with_stock(self):
        """Zaehlt die verfuegbaren Bestandsstuecke je Produkt.

        Der Bezug laeuft ueber das related_name "stock_items" als String, damit
        shop nicht inventory importieren muss (inventory referenziert bereits
        shop.Product - sonst gaebe es einen Zirkelimport).
        """
        return self.annotate(
            verfuegbar_count=models.Count(
                "stock_items",
                filter=models.Q(stock_items__status="verfuegbar"),
                distinct=True,
            )
        )

    def visible_for(self, user):
        """Aktive Produkte, die dieser Besucher sehen darf (user darf anonym sein).

        Die Zielgruppe ist dreiwertig: "alle" sieht jeder, "b2b" nur B2B-Kunden,
        "b2c" nur Endkunden. All Power/Admin sehen alles (Pruefrecht).
        """
        qs = self.filter(is_active=True)
        if user.is_authenticated:
            if user.can_manage_products:
                return qs
            if user.can_see_b2b_products:
                return qs.filter(
                    audience__in=(Product.Audience.B2B, Product.Audience.ALLE)
                )
        return qs.filter(audience__in=(Product.Audience.B2C, Product.Audience.ALLE))


class Product(models.Model):
    class Category(models.TextChoices):
        ECHTHAAR_PERUECKE = "echthaar_peruecke", "Echthaarperücke"
        ECHTHAAR_TOPPER = "echthaar_topper", "Echthaartopper"
        KUNSTHAAR_PERUECKE = "kunsthaar_peruecke", "Kunsthaarperücke"
        KUNSTHAAR_TOPPER = "kunsthaar_topper", "Kunsthaartopper"
        ZUBEHOER = "zubehoer", "Perücken Zubehör"
        PFLEGE = "pflege", "Pflegeprodukte (Hair Care)"
        KONFIG = "konfig", "Maßanfertigung"

    # Haarware: hat Haarattribute, ist Einzelstueck und kann in ein Projekt.
    # Eine Quelle fuer Shop-Filter, Erfassungsformular und Warenwirtschaft.
    HAARWAREN = (
        Category.ECHTHAAR_PERUECKE,
        Category.ECHTHAAR_TOPPER,
        Category.KUNSTHAAR_PERUECKE,
        Category.KUNSTHAAR_TOPPER,
    )

    class Audience(models.TextChoices):
        ALLE = "alle", "Alle Kunden"
        B2C = "b2c", "Nur B2C"
        B2B = "b2b", "Nur B2B"

    class Badge(models.TextChoices):
        NEW = "new", "Neu"
        POPULAR = "popular", "Beliebt"

    name = models.CharField("Name", max_length=120)
    label = models.CharField("Kurzlabel", max_length=60)
    slug = models.SlugField(max_length=80, unique=True)
    category = models.CharField("Kategorie", max_length=20, choices=Category.choices)
    audience = models.CharField(
        "Zielgruppe", max_length=5, choices=Audience.choices, default=Audience.ALLE
    )
    price = models.DecimalField("Preis (ab)", max_digits=8, decimal_places=2)
    badge = models.CharField("Badge", max_length=10, choices=Badge.choices, blank=True, default="")
    description = models.TextField("Beschreibung", blank=True)
    image = models.ImageField("Produktbild", upload_to="products/", blank=True)

    # Bestandsart: Einzelstueck (serialisiert ueber inventory.StockItem)
    # oder Mengenartikel (Zaehlfeld stock_quantity).
    class StockMode(models.TextChoices):
        EINZELSTUECK = "einzelstueck", "Einzelstück"
        MENGE = "menge", "Mengenartikel"

    stock_mode = models.CharField(
        "Bestandsart", max_length=12, choices=StockMode.choices,
        default=StockMode.EINZELSTUECK
    )
    stock_quantity = models.PositiveIntegerField(
        "Bestand (nur Mengenartikel)", default=0
    )
    # Opt-in: nur bestandsgefuehrte Produkte richten sich nach dem Lager. Ohne
    # diesen Schalter waeren beim Deploy alle Produkte ohne Bestandsstuecke
    # schlagartig ausverkauft.
    track_stock = models.BooleanField(
        "Bestandsgeführt", default=False,
        help_text="Verfügbarkeit im Shop aus dem Warenbestand ableiten."
    )

    # Produktattribute fuer die Detailseite (optional, je nach Kategorie relevant)
    hair_length = models.CharField("Länge", max_length=60, blank=True, default="")
    hair_size = models.CharField("Größe", max_length=60, blank=True, default="")
    hair_color = models.CharField("Farbe", max_length=80, blank=True, default="")
    hair_structure = models.CharField("Schnitt", max_length=60, blank=True, default="")
    hair_density = models.CharField("Dichte", max_length=60, blank=True, default="")
    cap_type = models.CharField("Montur", max_length=80, blank=True, default="")
    hair_origin = models.CharField("Haarherkunft", max_length=80, blank=True, default="")
    care_notes = models.TextField("Pflegehinweise", blank=True, default="")
    content_amount = models.CharField("Inhalt / Menge", max_length=40, blank=True, default="")
    usage_notes = models.TextField("Anwendung", blank=True, default="")

    # Bestellware: Ware, die wir anbieten, ohne sie am Lager zu haben. Beide
    # Felder werden aus inventory.CatalogItem nachgezogen und sind sonst leer.
    # Bewusst als fertiger Text statt als Bezug, damit shop weiterhin nichts
    # aus inventory importieren muss (siehe Kommentar bei with_stock).
    delivery_days = models.PositiveSmallIntegerField(
        "Lieferzeit (Werktage)", null=True, blank=True
    )
    available_variants = models.TextField(
        "Auch erhältlich in", blank=True, default=""
    )

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

    def ensure_slug(self):
        """Slug beim Anlegen erzeugen (Schema wie seed_products),
        Kollisionen bekommen ein -2/-3-Suffix.
        """
        if self.slug:
            return self.slug
        base = slugify(f"{self.category}-{self.label}")[:70]
        slug, i = base, 2
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        self.slug = slug
        return self.slug

    @property
    def price_display(self):
        """Ganze Euro mit deutschem Tausenderpunkt, z. B. '1.190'."""
        return f"{int(self.price):,}".replace(",", ".")

    @property
    def price_int(self):
        """Ganzzahliger Preis fuer data-price (clientseitige Sortierung)."""
        return int(self.price)

    # --- Normalisierte Filtergruppen (aus Freitextfeldern abgeleitet) ---
    # Reihenfolge in COLOR_KEYWORDS ist relevant: braun vor rot, damit
    # Mischtoene wie "Rotbraun" als braun gruppiert werden.
    COLOR_KEYWORDS = (
        ("grau", "grau"),
        ("silber", "grau"),
        ("schwarz", "schwarz"),
        ("blond", "blond"),
        ("champagner", "blond"),
        ("braun", "braun"),
        ("kastanien", "braun"),
        ("espresso", "braun"),
        ("karamell", "braun"),
        ("asch", "braun"),
        ("kupfer", "rot"),
        ("mahagoni", "rot"),
        ("rosegold", "rot"),
        ("roségold", "rot"),
        ("rot", "rot"),
    )

    # Montur-Filtergruppen: Reihenfolge = Priorität (Sondermerkmal vor Tresse).
    MONTUR_KEYWORDS = (
        ("vollmontur", "vollmontur"),
        ("monofilament", "monofilament"),
        ("film", "film"),
        ("integration", "integration"),
        ("tresse", "tresse"),
    )

    @property
    def structure_group(self):
        s = self.hair_structure.lower()
        if "lockig" in s:
            return "lockig"
        if "gewellt" in s:
            return "gewellt"
        if "glatt" in s:
            return "glatt"
        return ""

    @property
    def color_group(self):
        c = self.hair_color.lower()
        for keyword, group in self.COLOR_KEYWORDS:
            if keyword in c:
                return group
        return ""

    @property
    def length_group(self):
        match = re.search(r"(\d+)", self.hair_length)
        if not match:
            return ""
        cm = int(match.group(1))
        if cm <= 25:
            return "kurz"
        if cm <= 45:
            return "mittel"
        return "lang"

    @property
    def size_group(self):
        # Nur plausible Kopfumfänge gruppieren; Tressenlängen o. Ä. ignorieren.
        match = re.search(r"(\d+)", self.hair_size)
        if not match:
            return ""
        cm = int(match.group(1))
        if cm < 48 or cm > 64:
            return ""
        if cm < 54:
            return "klein"
        if cm < 56:
            return "mittel"
        return "gross"

    @property
    def density_group(self):
        d = self.hair_density.lower()
        for value in ("leicht", "mittel", "voll"):
            if value in d:
                return value
        return ""

    @property
    def montur_group(self):
        c = self.cap_type.lower()
        for keyword, group in self.MONTUR_KEYWORDS:
            if keyword in c:
                return group
        return ""

    @property
    def is_configurable(self):
        """Konfigurierbare Perücken: nur Rohpreis, Kauf nur nach Beratungstermin."""
        return self.category == self.Category.KONFIG

    @property
    def available_count(self):
        """Verfuegbare Menge. Nutzt die Annotation aus with_stock(), falls
        vorhanden, sonst eine eigene Abfrage (Detailseite, Einzelobjekte).
        """
        if self.stock_mode == self.StockMode.MENGE:
            return self.stock_quantity
        annotiert = getattr(self, "verfuegbar_count", None)
        if annotiert is not None:
            return annotiert
        return self.stock_items.filter(status="verfuegbar").count()

    @property
    def is_sold_out(self):
        return self.track_stock and self.available_count == 0

    @property
    def is_orderable(self):
        return not self.is_configurable and not self.is_sold_out

    @property
    def ist_bestellware(self):
        """Wird auf Bestellung beim Lieferanten geordert, liegt nicht im Lager."""
        return self.delivery_days is not None

    @property
    def stock_label(self):
        """Kurzlabel fuer den Warenkorb-Chip: woher das Stueck kommt."""
        if self.ist_bestellware:
            return "Bestellware"
        if self.stock_mode == self.StockMode.EINZELSTUECK:
            return "Einzelstück"
        return ""

    # Illustrations-Fallback je Kategorie, solange kein echtes Foto hochgeladen ist
    PLACEHOLDER_IMAGES = {
        Category.KONFIG: "images/wigs/wig-curly-volume.svg",
        Category.ECHTHAAR_PERUECKE: "images/wigs/wig-classic.svg",
        Category.KUNSTHAAR_PERUECKE: "images/wigs/wig-long-layers.svg",
        Category.ECHTHAAR_TOPPER: "images/wigs/wig-classic.svg",
        Category.KUNSTHAAR_TOPPER: "images/wigs/wig-long-layers.svg",
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
        if self.category not in self.HAARWAREN:
            field_names = ("content_amount", "usage_notes")
        else:
            field_names = (
                "hair_length",
                "hair_size",
                "hair_structure",
                "hair_color",
                "hair_density",
                "cap_type",
            )
        rows = []
        for field_name in field_names:
            value = getattr(self, field_name)
            if value:
                rows.append((self._meta.get_field(field_name).verbose_name, value))
        return rows


class ProductImage(models.Model):
    """Zusätzliches Galeriebild eines Produkts (Hauptbild bleibt Product.image)."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("Bild", upload_to="products/")
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)

    class Meta:
        verbose_name = "Produktbild"
        verbose_name_plural = "Produktbilder"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Bild für {self.product}"


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
