"""Warenwirtschaft: Bestand (serialisiert + Menge), Fertigungsphasen,
Historie, Bestellungen. Siehe WARENWIRTSCHAFT_PLAN.md.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from shop.models import Product as ShopProduct
from shop.models import ProductImage


class Supplier(models.Model):
    name = models.CharField("Name", max_length=120)
    code = models.CharField(
        "Kürzel", max_length=4, unique=True,
        help_text="Zwei bis vier Buchstaben, z. B. EW. Bildet den Anfang der Produktnummer."
    )
    contact = models.CharField("Ansprechpartner", max_length=200, blank=True)
    email = models.EmailField("E-Mail", blank=True)
    notes = models.TextField("Notizen", blank=True)
    # Zaehler je Hersteller fuer die Produktnummer. Eigenes Feld statt Parsen
    # bestehender Nummern, damit die Vergabe unter select_for_update eindeutig ist.
    next_number = models.PositiveIntegerField("Nächste laufende Nummer", default=1)

    class Meta:
        verbose_name = "Lieferant"
        verbose_name_plural = "Lieferanten"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AttributeOption(models.Model):
    """Pflegbarer Wertekatalog fuer die Erfassung (Farbe, Laenge, Schnitt, ...).

    Bewusst getrennt von shop.ConfiguratorOption: dort haengen kundenseitige
    Aufpreise dran, hier sind es reine Erfassungswerte.
    """

    class Group(models.TextChoices):
        FARBE = "farbe", "Farbe"
        LAENGE = "laenge", "Länge"
        SCHNITT = "schnitt", "Schnitt"
        MONTUR = "montur", "Montur"
        DICHTE = "dichte", "Dichte"
        GROESSE = "groesse", "Größe"

    group = models.CharField("Merkmal", max_length=10, choices=Group.choices)
    name = models.CharField("Wert", max_length=80)
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Auswahlwert"
        verbose_name_plural = "Auswahlwerte"
        ordering = ["group", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["group", "name"], name="uniq_attr_group_name")
        ]

    def __str__(self):
        return f"{self.get_group_display()}: {self.name}"


class StockItem(models.Model):
    """Ein physisches Einzelstueck (z. B. eine Peruecke) oder - bei
    stock_mode=menge - ein Posten Mengenware mit Stueckzahl.
    """

    class Status(models.TextChoices):
        VERFUEGBAR = "verfuegbar", "Verfügbar"
        RESERVIERT = "reserviert", "Reserviert"
        VERKAUFT = "verkauft", "Verkauft"
        AUSGEMUSTERT = "ausgemustert", "Ausgemustert"

    class Channel(models.TextChoices):
        ONLINE = "online", "Online"
        STUDIO = "studio", "Studio"

    class StockMode(models.TextChoices):
        EINZELSTUECK = "einzelstueck", "Einzelstück"
        MENGE = "menge", "Mengenartikel"

    class Audience(models.TextChoices):
        B2C = "b2c", "Alle Kunden"
        B2B = "b2b", "Nur B2B"

    # Konfigurierbare Peruecken entstehen nicht aus dem Bestand, sondern bleiben
    # Katalogvorlagen in der Produktverwaltung.
    SHOP_CATEGORIES = [
        (value, label)
        for value, label in ShopProduct.Category.choices
        if value != ShopProduct.Category.KONFIG
    ]

    # Als Decimal, nicht als TextChoices: die Auswahl eines DecimalField wird
    # zu Decimal gecastet und wuerde gegen String-Schluessel nicht validieren.
    VAT_RATES = [
        (Decimal("19.00"), "19 %"),
        (Decimal("7.00"), "7 %"),
        (Decimal("0.00"), "0 %"),
    ]

    # Zuordnung zum Shop-Katalog erst, wenn das Stueck online gestellt wird.
    product = models.ForeignKey(
        "shop.Product", null=True, blank=True, on_delete=models.PROTECT,
        related_name="stock_items", verbose_name="Produkt (Vorlage)"
    )
    inventory_no = models.CharField("Produktnummer", max_length=40, unique=True)
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Hersteller"
    )
    product_name = models.CharField("Produktname", max_length=120, default="")
    invoice_no = models.CharField("Rechnungsnummer", max_length=60, default="")
    purchase_price = models.DecimalField(
        "Einkaufspreis", max_digits=8, decimal_places=2, null=True, blank=True
    )
    vat_rate = models.DecimalField(
        "Mehrwertsteuersatz", max_digits=4, decimal_places=2,
        choices=VAT_RATES, default=Decimal("19.00")
    )
    color = models.CharField("Farbe", max_length=80, default="")
    length = models.CharField("Länge", max_length=60, default="")
    size = models.CharField("Größe", max_length=60, default="")
    structure = models.CharField("Schnitt", max_length=60, blank=True, default="")
    density = models.CharField("Dichte", max_length=60, blank=True, default="")
    cap_type = models.CharField("Montur", max_length=80, blank=True, default="")
    received_at = models.DateField("Lieferdatum", null=True, blank=True)

    # Einzelstueck = ein Datensatz je physischem Stueck; Mengenartikel = ein
    # Datensatz mit Stueckzahl (Pflege, Zubehoer, Top Holder).
    stock_mode = models.CharField(
        "Bestandsart", max_length=12, choices=StockMode.choices,
        default=StockMode.EINZELSTUECK
    )
    quantity = models.PositiveIntegerField("Stückzahl", default=1)

    # Verkaufsdaten fuer die Veroeffentlichung im Shop
    shop_category = models.CharField(
        "Shop-Kategorie", max_length=10, choices=SHOP_CATEGORIES, blank=True, default=""
    )
    audience = models.CharField(
        "Zielgruppe", max_length=3, choices=Audience.choices, default=Audience.B2C
    )
    sale_price = models.DecimalField(
        "Verkaufspreis", max_digits=8, decimal_places=2, null=True, blank=True
    )
    description = models.TextField("Shop-Beschreibung", blank=True, default="")
    notes = models.TextField("Interne Notizen", blank=True, default="")

    # Dimension 1: kaufmaennischer Verfuegbarkeits-Status
    status = models.CharField(
        "Status", max_length=12, choices=Status.choices, default=Status.VERFUEGBAR
    )
    reserved_for = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reserved_items", verbose_name="Reserviert für"
    )
    reserved_until = models.DateTimeField("Reserviert bis", null=True, blank=True)
    sold_at = models.DateTimeField("Verkauft am", null=True, blank=True)
    sold_channel = models.CharField(
        "Verkaufskanal", max_length=10, choices=Channel.choices, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bestandsstück"
        verbose_name_plural = "Bestandsstücke"
        ordering = ["inventory_no"]

    def __str__(self):
        return f"{self.inventory_no} · {self.product_name}"

    def clean(self):
        # Rohlinge sind Handelsware fuer Kollegen, nie fuer Endkunden.
        if self.shop_category == ShopProduct.Category.ROHLING:
            self.audience = self.Audience.B2B

    @property
    def is_available(self):
        return self.status == self.Status.VERFUEGBAR

    @property
    def work_state(self):
        """Arbeitsstand aus den Projekten als (Schluessel, Beschriftung).

        Ersetzt die frueheren Fertigungsphasen: es gibt genau einen Zustand
        je Stueck, und der ergibt sich aus den Projekten statt aus einem
        Feld, das niemand pflegt. Iteriert bewusst in Python, damit ein
        prefetch_related("projects") in Listen greift.
        """
        projekte = list(self.projects.all())
        if not projekte:
            return None
        if any(p.status == Project.Status.OFFEN for p in projekte):
            return ("offen", "In Arbeit")
        if any(p.status == Project.Status.ERLEDIGT for p in projekte):
            return ("erledigt", "Fertig")
        return None

    @property
    def vat_amount(self):
        """Aus EK-Preis und Satz berechnete Mehrwertsteuer (nur Anzeige)."""
        if self.purchase_price is None:
            return None
        return (self.purchase_price * self.vat_rate / 100).quantize(Decimal("0.01"))

    @property
    def cover_image(self):
        """Bild fuer Listen: Verkaufsbild vor Eingangsbild."""
        return (
            self.images.filter(kind=StockItemImage.Kind.SHOP).first()
            or self.images.first()
        )

    @property
    def shop_images(self):
        """Bilder fuer den Shop: Verkaufsbilder, sonst die Eingangsbilder."""
        shop = list(self.images.filter(kind=StockItemImage.Kind.SHOP))
        return shop or list(self.images.filter(kind=StockItemImage.Kind.EINGANG))

    def log_event(self, kind, from_value, to_value, by=None, note=""):
        """Historien-Eintrag schreiben (wer/wann)."""
        return StockItemEvent.objects.create(
            stock_item=self, kind=kind,
            from_value=from_value or "", to_value=to_value or "",
            changed_by=by, note=note,
        )

    @property
    def is_published(self):
        """Online = einem Shop-Produkt zugeordnet. Ob es tatsaechlich kaufbar
        ist, entscheidet der Bestand ueber Product.track_stock.
        """
        return self.product_id is not None

    def sync_to_product(self):
        """Eigenschaften und Galerie ins verknuepfte Shop-Produkt nachziehen.

        Nur die Felder, die der Bestand besser weiss - Name, Kurzlabel, Preis
        und Kategorie bleiben beim Produkt, weil sich mehrere Stuecke ein
        Produkt teilen koennen und die Verkaufstexte dort gepflegt werden.
        """
        produkt = self.product
        if produkt is None:
            return None

        produkt.hair_color = self.color
        produkt.hair_length = self.length
        produkt.hair_size = self.size
        produkt.hair_structure = self.structure
        produkt.hair_density = self.density
        produkt.cap_type = self.cap_type
        if self.audience:
            produkt.audience = self.audience
        if self.description:
            produkt.description = self.description
        if self.stock_mode == self.StockMode.MENGE:
            produkt.stock_mode = ShopProduct.StockMode.MENGE
            produkt.stock_quantity = self.quantity
        produkt.save()

        # Galerie spiegeln: nur Zeilen neu anlegen, die Dateien selbst bleiben
        # im Bestand liegen (image.name ist derselbe Pfad, kein Kopieren).
        # Teilen sich mehrere Stuecke ein Produkt, bleibt die vorhandene
        # Galerie stehen - sonst wuerde das zuletzt gespeicherte Stueck die
        # Fotos der anderen ueberschreiben.
        bilder = self.shop_images
        allein = produkt.stock_items.exclude(pk=self.pk).count() == 0
        if bilder and (allein or not produkt.images.exists()):
            produkt.images.all().delete()
            ProductImage.objects.bulk_create([
                ProductImage(product=produkt, image=b.image.name, sort_order=i)
                for i, b in enumerate(bilder)
            ])
            produkt.image = bilder[0].image.name
            produkt.save(update_fields=["image"])
        return produkt


class StockItemImage(models.Model):
    """Fotos eines Bestandsstuecks. Eingangsbilder dokumentieren den Zustand
    beim Kauf, Verkaufsbilder zeigen das fertig bearbeitete Produkt und wandern
    beim Veroeffentlichen in die Shop-Galerie.
    """

    class Kind(models.TextChoices):
        EINGANG = "eingang", "Eingangsbild"
        SHOP = "shop", "Verkaufsbild"

    stock_item = models.ForeignKey(
        StockItem, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("Bild", upload_to="inventory/%Y/%m/")
    kind = models.CharField(
        "Art", max_length=10, choices=Kind.choices, default=Kind.EINGANG
    )
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bestandsbild"
        verbose_name_plural = "Bestandsbilder"
        ordering = ["kind", "sort_order", "id"]

    def __str__(self):
        return f"{self.get_kind_display()} zu {self.stock_item.inventory_no}"


class StockItemEvent(models.Model):
    """Lueckenlose Historie je Bestandsstueck (Phase- und Statuswechsel)."""

    class Kind(models.TextChoices):
        EINGANG = "eingang", "Wareneingang"
        PHASE = "phase", "Fertigungsphase"
        STATUS = "status", "Status"
        PROJEKT = "projekt", "Projekt"

    stock_item = models.ForeignKey(
        StockItem, on_delete=models.CASCADE, related_name="events"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    from_value = models.CharField("von", max_length=60, blank=True)
    to_value = models.CharField("auf", max_length=60, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField("Notiz", blank=True)

    class Meta:
        verbose_name = "Historien-Eintrag"
        verbose_name_plural = "Historie"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.stock_item.inventory_no}: {self.from_value} -> {self.to_value}"


class Project(models.Model):
    """Der nach der Kundenberatung festgelegte Plan fuer ein Produkt.

    Das Bestandsstueck ist optional: ein Projekt kann schon stehen, bevor die
    passende Ware da ist, und spaeter zugeordnet werden.
    """

    class Status(models.TextChoices):
        OFFEN = "offen", "Offen"
        ERLEDIGT = "erledigt", "Erledigt"
        STORNIERT = "storniert", "Storniert"

    title = models.CharField("Bezeichnung", max_length=120)
    stock_item = models.ForeignKey(
        StockItem, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="projects", verbose_name="Bestandsstück"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="projects", verbose_name="Kunde (Konto)"
    )
    customer_name = models.CharField("Kundenname", max_length=120, blank=True, default="")

    target_color = models.CharField("Farbe", max_length=80, blank=True, default="")
    target_length = models.CharField("Länge", max_length=60, blank=True, default="")
    target_structure = models.CharField("Schnitt", max_length=60, blank=True, default="")
    target_cap_type = models.CharField("Montur", max_length=80, blank=True, default="")
    target_density = models.CharField("Dichte", max_length=60, blank=True, default="")
    target_size = models.CharField("Größe", max_length=60, blank=True, default="")

    notes = models.TextField("Kommentare", blank=True, default="")
    due_date = models.DateField("Fertig bis", null=True, blank=True)
    status = models.CharField(
        "Status", max_length=10, choices=Status.choices, default=Status.OFFEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Planfeld am Projekt -> Eigenschaftsfeld am Bestandsstueck
    PLAN_FIELDS = (
        ("target_color", "color"),
        ("target_length", "length"),
        ("target_structure", "structure"),
        ("target_cap_type", "cap_type"),
        ("target_density", "density"),
        ("target_size", "size"),
    )

    class Meta:
        verbose_name = "Projekt"
        verbose_name_plural = "Projekte"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def customer_display(self):
        if self.customer:
            name = f"{self.customer.first_name} {self.customer.last_name}".strip()
            return name or self.customer.email
        return self.customer_name or "–"

    @property
    def plan_rows(self):
        """(Label, Wert)-Paare des Plans - nur befuellte Felder."""
        rows = []
        for name, _ in self.PLAN_FIELDS:
            value = getattr(self, name)
            if value:
                rows.append((self._meta.get_field(name).verbose_name, value))
        return rows

    def apply_plan(self, by=None):
        """Plandaten auf das Bestandsstueck uebernehmen."""
        if self.stock_item is None:
            return False
        stueck = self.stock_item
        geaendert = []
        for plan_field, item_field in self.PLAN_FIELDS:
            value = getattr(self, plan_field)
            if value and getattr(stueck, item_field) != value:
                setattr(stueck, item_field, value)
                geaendert.append(item_field)
        if not geaendert:
            return False
        stueck.save(update_fields=geaendert + ["updated_at"])
        stueck.log_event(
            StockItemEvent.Kind.PROJEKT, "", self.title, by=by,
            note="Plandaten aus dem Projekt übernommen.",
        )
        return True


class Order(models.Model):
    """Aufgenommene Bestellung. Zahlung/Rechnung liegen im Fremdsystem;
    nach Aufnahme werden die Daten dorthin uebergeben (siehe Plan Abschnitt 6).
    """

    class Status(models.TextChoices):
        AUFGENOMMEN = "aufgenommen", "Aufgenommen"
        UEBERGEBEN = "uebergeben", "An Fremdsystem übergeben"
        STORNIERT = "storniert", "Storniert"

    class ExportStatus(models.TextChoices):
        PENDING = "pending", "Offen"
        SENT = "sent", "Gesendet"
        FAILED = "failed", "Fehlgeschlagen"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Kunde (Konto)"
    )
    # Laufkundschaft im Studio hat kein Konto - dann werden diese Felder gefuellt.
    customer_name = models.CharField("Name", max_length=120, blank=True)
    customer_street = models.CharField("Straße und Hausnummer", max_length=120, blank=True)
    customer_zip = models.CharField("PLZ", max_length=10, blank=True)
    customer_city = models.CharField("Ort", max_length=80, blank=True)
    customer_email = models.EmailField("E-Mail", blank=True)

    channel = models.CharField(
        "Verkaufskanal", max_length=10, choices=StockItem.Channel.choices,
        default=StockItem.Channel.STUDIO
    )
    note = models.TextField("Notiz für die Rechnung", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sold_on = models.DateField("Verkaufsdatum", null=True, blank=True)
    status = models.CharField(
        "Status", max_length=12, choices=Status.choices, default=Status.AUFGENOMMEN
    )
    total = models.DecimalField("Summe", max_digits=10, decimal_places=2, default=0)

    # Uebergabe ans Fremdsystem
    export_status = models.CharField(
        "Übergabe", max_length=10, choices=ExportStatus.choices,
        default=ExportStatus.PENDING
    )
    export_ref = models.CharField("Referenz Fremdsystem", max_length=100, blank=True)

    class Meta:
        verbose_name = "Bestellung"
        verbose_name_plural = "Bestellungen"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bestellung #{self.pk}"

    @property
    def customer_display(self):
        """Name der Kundin, egal ob Konto oder Freitext."""
        if self.user:
            voll = f"{self.user.first_name} {self.user.last_name}".strip()
            return self.user.company_name or voll or self.user.email
        return self.customer_name

    @property
    def billing_lines(self):
        """Rechnungsanschrift als Zeilenliste - eine Quelle für Mail und Anzeige."""
        if self.user:
            zeilen = [
                self.customer_display,
                self.user.street,
                f"{self.user.zip_code} {self.user.city}".strip(),
                self.user.email,
                self.user.phone,
            ]
            if self.user.vat_id:
                zeilen.append(f"USt-IdNr.: {self.user.vat_id}")
        else:
            zeilen = [
                self.customer_name,
                self.customer_street,
                f"{self.customer_zip} {self.customer_city}".strip(),
                self.customer_email,
            ]
        return [z for z in zeilen if z]


class OrderItem(models.Model):
    """Position einer Bestellung. Einzelstueck ueber stock_item,
    Mengenartikel ueber product + quantity.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # Optional: ein noch nicht online gestelltes Stueck hat kein Shop-Produkt.
    product = models.ForeignKey(
        "shop.Product", null=True, blank=True, on_delete=models.PROTECT,
        verbose_name="Produkt"
    )
    stock_item = models.ForeignKey(
        StockItem, null=True, blank=True, on_delete=models.PROTECT,
        verbose_name="Bestandsstück (Einzelstück)"
    )
    # Momentaufnahme: spaetere Umbenennungen duerfen alte Rechnungen nicht aendern.
    description = models.CharField("Bezeichnung", max_length=160, default="")
    quantity = models.PositiveIntegerField("Menge", default=1)
    price = models.DecimalField("Verkaufspreis", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "Bestellposition"
        verbose_name_plural = "Bestellpositionen"

    def __str__(self):
        return f"{self.quantity}x {self.description}"
