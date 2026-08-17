from django import forms

from .models import AttributeOption, ProductionPhase, Project, StockItem, Supplier

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
    "target_size": AttributeOption.Group.GROESSE,
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


class ProductionPhaseForm(forms.ModelForm):
    class Meta:
        model = ProductionPhase
        fields = ("name", "sort_order", "is_active")


class AttributeOptionForm(forms.ModelForm):
    class Meta:
        model = AttributeOption
        fields = ("group", "name", "sort_order", "is_active")


class GoodsReceiptForm(CatalogFieldsMixin, forms.ModelForm):
    """Wareneingang erfassen. Stueckzahl ist bei Einzelstuecken kein Modellfeld -
    die View legt entsprechend viele Datensaetze an; bei Mengenartikeln landet
    sie als quantity an einem einzigen Datensatz.
    """

    quantity = forms.IntegerField(label="Stückzahl", min_value=1, initial=1)

    catalog_fields = ("color", "length", "size", "structure", "density", "cap_type")

    # Ohne diese Angaben laesst sich nichts einkaufen; alles Weitere
    # (Verkaufspreis, Beschreibung) kommt spaeter beim Bearbeiten dazu.
    required_fields = (
        "supplier", "product_name", "invoice_no", "purchase_price", "vat_rate",
        "color", "length", "size", "received_at", "stock_mode", "shop_category",
    )

    class Meta:
        model = StockItem
        fields = (
            "stock_mode",
            "shop_category",
            "audience",
            "supplier",
            "product_name",
            "invoice_no",
            "purchase_price",
            "vat_rate",
            "color",
            "length",
            "size",
            "structure",
            "density",
            "cap_type",
            "received_at",
            "sale_price",
            "notes",
        )
        widgets = {
            "received_at": DATE_WIDGET,
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_catalog()
        for name in self.required_fields:
            self.fields[name].required = True
        for name in ("structure", "density", "cap_type", "sale_price", "notes"):
            self.fields[name].required = False
        self.fields["supplier"].empty_label = "Bitte wählen"
        self.fields["shop_category"].choices = [
            ("", "Bitte wählen")
        ] + list(StockItem.SHOP_CATEGORIES)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("shop_category") == "rohling":
            cleaned["audience"] = StockItem.Audience.B2B
        return cleaned


class StockItemForm(CatalogFieldsMixin, forms.ModelForm):
    catalog_fields = ("color", "length", "size", "structure", "density", "cap_type")

    class Meta:
        model = StockItem
        fields = (
            "product_name",
            "stock_mode",
            "quantity",
            "supplier",
            "invoice_no",
            "purchase_price",
            "vat_rate",
            "received_at",
            "color",
            "length",
            "size",
            "structure",
            "density",
            "cap_type",
            "current_phase",
            "status",
            "reserved_for",
            "reserved_until",
            "sold_channel",
            "shop_category",
            "audience",
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

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("shop_category") == "rohling":
            cleaned["audience"] = StockItem.Audience.B2B
        return cleaned


class ProjectForm(CatalogFieldsMixin, forms.ModelForm):
    catalog_fields = (
        "target_color", "target_length", "target_structure",
        "target_cap_type", "target_density", "target_size",
    )

    class Meta:
        model = Project
        fields = (
            "title",
            "stock_item",
            "customer",
            "customer_name",
            "status",
            "due_date",
            "target_color",
            "target_length",
            "target_structure",
            "target_cap_type",
            "target_density",
            "target_size",
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
        self.fields["customer"].empty_label = "Kein Kundenkonto"
        self.fields["stock_item"].queryset = StockItem.objects.exclude(
            status=StockItem.Status.AUSGEMUSTERT
        ).order_by("-created_at")
