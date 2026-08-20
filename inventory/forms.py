from django import forms
from django.utils import timezone

from .models import AttributeOption, CatalogItem, Project, StockItem, Supplier

# <input type="date"> bzw. datetime-local akzeptieren nur ISO. Ohne festes
# format rendert Django den deutschen Wert, den der Browser verwirft - das Feld
# waere beim Bearbeiten leer und der Wert ginge beim Speichern verloren.
DATE_WIDGET = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
DATETIME_WIDGET = forms.DateTimeInput(
    attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
)

# Formularfeld -> Katalog-Merkmal
CATALOG_MAP = {
    "color": AttributeOption.Group.FARBE,
    "length": AttributeOption.Group.LAENGE,
    "structure": AttributeOption.Group.SCHNITT,
    "cap_type": AttributeOption.Group.MONTUR,
    "density": AttributeOption.Group.DICHTE,
    "size": AttributeOption.Group.GROESSE,
    "target_color": AttributeOption.Group.FARBE,
    "target_length": AttributeOption.Group.LAENGE,
    "target_structure": AttributeOption.Group.SCHNITT,
    "target_cap_type": AttributeOption.Group.MONTUR,
    "target_density": AttributeOption.Group.DICHTE,
}


def catalog_choices(group, current=""):
    """Auswahl aus dem Wertekatalog. Ein bereits gespeicherter Wert, der nicht
    (mehr) im Katalog steht, wird angehaengt - sonst ginge er beim Speichern
    verloren.
    """
    values = list(
        AttributeOption.objects.filter(group=group, is_active=True)
        .values_list("name", flat=True)
    )
    if current and current not in values:
        values.append(current)
    return [("", "Bitte wählen")] + [(v, v) for v in values]


class CatalogFieldsMixin:
    """Macht aus den Freitextfeldern in CATALOG_MAP Auswahlfelder."""

    catalog_fields = ()

    @property
    def haar_kategorien(self):
        """Kategorien mit Haarangaben, als Liste fuers data-Attribut.

        Das Formular blendet die Eigenschaften danach ein und aus; massgeblich
        bleibt die Pruefung in clean().
        """
        return ",".join(StockItem.PROJEKTFAEHIGE_KATEGORIEN)

    def _apply_catalog(self):
        for name in self.catalog_fields:
            field = self.fields[name]
            current = self.get_initial_for_field(field, name) or ""
            self.fields[name] = forms.ChoiceField(
                label=field.label,
                choices=catalog_choices(CATALOG_MAP[name], str(current)),
                required=field.required,
                initial=current,
            )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("name", "code", "contact", "email", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class AttributeOptionForm(forms.ModelForm):
    class Meta:
        model = AttributeOption
        fields = ("group", "name", "sort_order", "is_active")


class GoodsReceiptForm(CatalogFieldsMixin, forms.ModelForm):
    """Wareneingang erfassen.

    Die Anzahl bedeutet je nach Kategorie zweierlei: bei Peruecken und Rohlingen
    entstehen so viele Datensaetze mit eigener Produktnummer, bei Mengenware ein
    einziger Datensatz mit dieser Anzahl. Die Bestandsart wird deshalb nicht
    mehr gefragt, sondern aus der Kategorie abgeleitet.
    """

    quantity = forms.IntegerField(label="Anzahl", min_value=1, initial=1)

    catalog_fields = ("color", "length", "size", "structure", "density", "cap_type")

    # Ohne diese Angaben laesst sich nichts einkaufen; alles Weitere
    # (Verkaufspreis, Zielgruppe) kommt beim Bearbeiten und beim Onlinestellen
    # dazu.
    required_fields = (
        "supplier", "product_name", "invoice_no", "purchase_price",
        "received_at", "shop_category",
    )
    # Nur bei Haarware Pflicht - an Zubehoer und Pflegeprodukten gibt es weder
    # Farbe noch Laenge noch Kopfumfang.
    required_haar_fields = ("color", "length", "size")

    class Meta:
        model = StockItem
        fields = (
            "shop_category",
            "supplier",
            "product_name",
            "supplier_article_no",
            "invoice_no",
            "purchase_price",
            "color",
            "length",
            "size",
            "structure",
            "density",
            "cap_type",
            "received_at",
            "sale_price",
            "description",
            "notes",
        )
        widgets = {
            "received_at": DATE_WIDGET,
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_catalog()
        for name in self.required_fields:
            self.fields[name].required = True
        # Die Haarfelder sind ChoiceFields aus dem Katalog: waeren sie hier
        # schon Pflicht, scheiterte die Validierung vor clean() - und damit
        # bevor die Kategorie bekannt ist.
        for name in self.catalog_fields + ("sale_price", "description", "notes"):
            self.fields[name].required = False
        self.fields["supplier"].empty_label = "Bitte wählen"
        self.fields["shop_category"].choices = [
            ("", "Bitte wählen")
        ] + list(StockItem.SHOP_CATEGORIES)
        # Ware wird fast immer am Eingangstag erfasst. Ein leeres Datumsfeld
        # sieht auf dem iPhone zudem aus wie ein Fehler.
        self.fields["received_at"].initial = timezone.localdate()

    def clean(self):
        daten = super().clean()
        kategorie = daten.get("shop_category")
        if kategorie in StockItem.PROJEKTFAEHIGE_KATEGORIEN:
            for name in self.required_haar_fields:
                if not daten.get(name):
                    self.add_error(name, "Dieses Feld ist erforderlich.")
        return daten


class StockItemPublishForm(forms.Form):
    """Bestandsstueck online stellen: bestehendes Shop-Produkt waehlen oder
    ein neues anlegen, vorbelegt aus den Wareneingangsdaten.
    """

    product = forms.ModelChoiceField(
        queryset=None, required=False, label="Bestehendes Shop-Produkt",
        empty_label="Neues Produkt anlegen",
    )
    name = forms.CharField(label="Produktname", max_length=120, required=False)
    label = forms.CharField(label="Kurzlabel", max_length=60, required=False)
    category = forms.ChoiceField(label="Kategorie", required=False)
    price = forms.DecimalField(
        label="Verkaufspreis (€)", max_digits=8, decimal_places=2, required=False
    )
    # Erst hier gefragt: beim Einkauf steht oft noch nicht fest, ob ein Stueck
    # an Endkunden oder an Kollegen geht. Bewusst ohne Vorauswahl.
    audience = forms.ChoiceField(
        label="Zielgruppe", choices=(), required=True,
        help_text="Wer das Produkt im Shop sehen darf.",
    )

    def __init__(self, *args, **kwargs):
        # Import hier, nicht auf Modulebene: shop importiert inventory nicht,
        # aber die Kette bleibt so in jedem Fall zirkelfrei.
        from shop.models import Product

        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.order_by("name")
        self.fields["category"].choices = [("", "---------")] + [
            (wert, bezeichnung) for wert, bezeichnung in Product.Category.choices
            if wert != Product.Category.KONFIG
        ]
        self.fields["audience"].choices = [
            ("", "Bitte wählen")
        ] + list(StockItem.Audience.choices)

    def clean(self):
        daten = super().clean()
        if daten.get("product"):
            return daten
        # Neues Produkt: die Angaben, die der Wareneingang nicht liefert
        for feld, text in (
            ("name", "Produktname"), ("label", "Kurzlabel"),
            ("category", "Kategorie"), ("price", "Verkaufspreis"),
        ):
            if not daten.get(feld):
                self.add_error(feld, f"{text} wird für ein neues Produkt benötigt.")
        return daten


class StockItemSellForm(forms.Form):
    """Verkauf buchen. Kundin entweder ueber ein Konto oder als Freitext."""

    user = forms.ModelChoiceField(
        queryset=None, required=False, label="Kundenkonto",
        empty_label="Ohne Konto (Angaben unten)",
    )
    customer_name = forms.CharField(label="Name", max_length=120, required=False)
    customer_street = forms.CharField(
        label="Straße und Hausnummer", max_length=120, required=False
    )
    customer_zip = forms.CharField(label="PLZ", max_length=10, required=False)
    customer_city = forms.CharField(label="Ort", max_length=80, required=False)
    customer_email = forms.EmailField(label="E-Mail", required=False)

    price = forms.DecimalField(
        label="Verkaufspreis (€)", max_digits=8, decimal_places=2
    )
    sold_on = forms.DateField(label="Verkaufsdatum", widget=DATE_WIDGET)
    channel = forms.ChoiceField(label="Verkaufskanal", choices=())
    note = forms.CharField(
        label="Notiz für die Rechnung", required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        from accounts.models import User

        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(
            role__in=(User.Role.B2C, User.Role.B2B)
        ).order_by("last_name", "email")
        self.fields["channel"].choices = StockItem.Channel.choices

    def clean(self):
        daten = super().clean()
        if daten.get("user"):
            return daten
        if not daten.get("customer_name"):
            self.add_error(
                "customer_name",
                "Ohne Kundenkonto wird der Name für die Rechnung benötigt.",
            )
        return daten


class StockItemForm(CatalogFieldsMixin, forms.ModelForm):
    catalog_fields = ("color", "length", "size", "structure", "density", "cap_type")

    class Meta:
        model = StockItem
        fields = (
            "product_name",
            "quantity",
            "supplier",
            "supplier_article_no",
            "invoice_no",
            "purchase_price",
            "received_at",
            "color",
            "length",
            "size",
            "structure",
            "density",
            "cap_type",
            "status",
            "reserved_for",
            "reserved_until",
            "sold_channel",
            "shop_category",
            "sale_price",
            "description",
            "notes",
        )
        widgets = {
            "received_at": DATE_WIDGET,
            "reserved_until": DATETIME_WIDGET,
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_catalog()
        for name in ("structure", "density", "cap_type"):
            self.fields[name].required = False
        self.fields["shop_category"].choices = [
            ("", "Bitte wählen")
        ] + list(StockItem.SHOP_CATEGORIES)
        # Beschriftung je nach Ware: bei Peruecken zaehlt der Datensatz genau
        # ein Stueck, bei Mengenware steht hier der Lagerbestand.
        if self.instance.pk and self.instance.ist_einzelstueck:
            self.fields["quantity"].help_text = (
                "Einzelstück – dieser Datensatz ist genau ein Stück."
            )
            self.fields["quantity"].disabled = True
        else:
            self.fields["quantity"].help_text = "Wie viele davon im Lager liegen."


class CatalogItemForm(CatalogFieldsMixin, forms.ModelForm):
    """Bestellartikel pflegen: Ware, die wir anbieten, ohne sie am Lager zu
    haben. Lieferant und dessen Artikelnummer sind Pflicht - ohne sie laesst
    sich nichts nachbestellen.
    """

    catalog_fields = ("color", "length", "size", "structure", "density", "cap_type")

    # Nur bei Haarware Pflicht, wie im Wareneingang. Geprueft in clean(),
    # weil die Kategorie erst dort feststeht.
    required_haar_fields = ("color", "length", "size")

    class Meta:
        model = CatalogItem
        fields = (
            "shop_category",
            "supplier",
            "supplier_article_no",
            "product_name",
            "color",
            "length",
            "size",
            "structure",
            "density",
            "cap_type",
            "available_colors",
            "available_sizes",
            "list_price",
            "sale_price",
            "delivery_days",
            "availability",
            "is_active",
            "description",
            "notes",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "available_colors": forms.CheckboxSelectMultiple,
            "available_sizes": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_catalog()
        for name in self.catalog_fields + ("list_price", "description", "notes"):
            self.fields[name].required = False
        self.fields["supplier"].empty_label = "Bitte wählen"
        self.fields["shop_category"].choices = [
            ("", "Bitte wählen")
        ] + list(StockItem.SHOP_CATEGORIES)
        # Die Palette kommt aus demselben Wertekatalog wie die Einzelangaben.
        # label_from_instance: __str__ setzt "Farbe: " davor, was in einer
        # Liste mit der Ueberschrift "Farben" nur stoert.
        for name, gruppe in (
            ("available_colors", AttributeOption.Group.FARBE),
            ("available_sizes", AttributeOption.Group.GROESSE),
        ):
            feld = self.fields[name]
            feld.queryset = AttributeOption.objects.filter(
                group=gruppe, is_active=True
            )
            feld.label_from_instance = lambda option: option.name

    def clean(self):
        daten = super().clean()
        if daten.get("shop_category") in StockItem.PROJEKTFAEHIGE_KATEGORIEN:
            for name in self.required_haar_fields:
                if not daten.get(name):
                    self.add_error(name, "Dieses Feld ist erforderlich.")
        return daten


class ProjectForm(CatalogFieldsMixin, forms.ModelForm):
    # Die Groesse fehlt hier bewusst: sie kommt fest aus dem Bestandsstueck
    # (dort beim Wareneingang erfasst) und ist im Projekt nicht waehlbar.
    catalog_fields = (
        "target_color", "target_length", "target_structure",
        "target_cap_type", "target_density",
    )

    class Meta:
        model = Project
        fields = (
            "title",
            "stock_item",
            "catalog_item",
            "customer",
            "customer_name",
            "status",
            "due_date",
            "target_color",
            "target_length",
            "target_structure",
            "target_cap_type",
            "target_density",
            "notes",
        )
        widgets = {
            "due_date": DATE_WIDGET,
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_catalog()
        self.fields["stock_item"].empty_label = "Noch kein Bestandsstück"
        self.fields["catalog_item"].empty_label = "Kein Bestellartikel"
        self.fields["customer"].empty_label = "Kein Kundenkonto"
        # Nur handwerklich bearbeitbare Ware: an Zubehoer oder Pflegeprodukten
        # gibt es nichts zu planen.
        self.fields["stock_item"].queryset = (
            StockItem.objects
            .filter(shop_category__in=StockItem.PROJEKTFAEHIGE_KATEGORIEN)
            .exclude(status=StockItem.Status.AUSGEMUSTERT)
            .order_by("-created_at")
        )
        self.fields["catalog_item"].queryset = (
            CatalogItem.objects
            .filter(
                shop_category__in=StockItem.PROJEKTFAEHIGE_KATEGORIEN,
                is_active=True,
            )
            .order_by("product_name")
        )
