"""Warenwirtschaft: Bestand (serialisiert + Menge), Fertigungsphasen,
Historie, Bestellungen. Siehe WARENWIRTSCHAFT_PLAN.md.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models


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


class ProductionPhase(models.Model):
    """Katalog der Fertigungsschritte, im Admin pflegbar."""

    name = models.CharField("Phase", max_length=60, unique=True)
    sort_order = models.PositiveSmallIntegerField("Sortierung", default=0)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Fertigungsphase"
        verbose_name_plural = "Fertigungsphasen"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class StockItem(models.Model):
    """Ein physisches Einzelstueck (z. B. eine Peruecke)."""

    class Status(models.TextChoices):
        VERFUEGBAR = "verfuegbar", "Verfügbar"
        RESERVIERT = "reserviert", "Reserviert"
        VERKAUFT = "verkauft", "Verkauft"
        AUSGEMUSTERT = "ausgemustert", "Ausgemustert"

    class Channel(models.TextChoices):
        ONLINE = "online", "Online"
        STUDIO = "studio", "Studio"

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
    received_at = models.DateField("Lieferdatum", null=True, blank=True)

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

    # Dimension 2: handwerkliche Fertigungsphase
    current_phase = models.ForeignKey(
        ProductionPhase, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Aktuelle Fertigungsphase"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bestandsstück"
        verbose_name_plural = "Bestandsstücke"
        ordering = ["inventory_no"]

    def __str__(self):
        return f"{self.inventory_no} · {self.product_name}"

    @property
    def is_available(self):
        return self.status == self.Status.VERFUEGBAR

    @property
    def vat_amount(self):
        """Aus EK-Preis und Satz berechnete Mehrwertsteuer (nur Anzeige)."""
        if self.purchase_price is None:
            return None
        return (self.purchase_price * self.vat_rate / 100).quantize(Decimal("0.01"))

    def log_event(self, kind, from_value, to_value, by=None, note=""):
        """Historien-Eintrag schreiben (wer/wann)."""
        return StockItemEvent.objects.create(
            stock_item=self, kind=kind,
            from_value=from_value or "", to_value=to_value or "",
            changed_by=by, note=note,
        )


class StockItemEvent(models.Model):
    """Lueckenlose Historie je Bestandsstueck (Phase- und Statuswechsel)."""

    class Kind(models.TextChoices):
        EINGANG = "eingang", "Wareneingang"
        PHASE = "phase", "Fertigungsphase"
        STATUS = "status", "Status"

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
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        verbose_name="Kunde"
    )
    created_at = models.DateTimeField(auto_now_add=True)
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


class OrderItem(models.Model):
    """Position einer Bestellung. Einzelstueck ueber stock_item,
    Mengenartikel ueber product + quantity.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("shop.Product", on_delete=models.PROTECT, verbose_name="Produkt")
    stock_item = models.ForeignKey(
        StockItem, null=True, blank=True, on_delete=models.PROTECT,
        verbose_name="Bestandsstück (Einzelstück)"
    )
    quantity = models.PositiveIntegerField("Menge", default=1)
    price = models.DecimalField("Verkaufspreis", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "Bestellposition"
        verbose_name_plural = "Bestellpositionen"

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
