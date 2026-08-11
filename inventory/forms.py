from django import forms

from .models import ProductionPhase, StockItem, Supplier

# <input type="date"> bzw. datetime-local akzeptieren nur ISO. Ohne festes
# format rendert Django den deutschen Wert, den der Browser verwirft - das Feld
# waere beim Bearbeiten leer und der Wert ginge beim Speichern verloren.
DATE_WIDGET = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
DATETIME_WIDGET = forms.DateTimeInput(
    attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
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


class GoodsReceiptForm(forms.ModelForm):
    """Wareneingang erfassen. Stueckzahl ist kein Modellfeld - jedes StockItem
    ist genau ein Stueck; die View legt entsprechend viele Datensaetze an.
    """

    quantity = forms.IntegerField(label="Stückzahl", min_value=1, initial=1)

    class Meta:
        model = StockItem
        fields = (
            "supplier",
            "product_name",
            "invoice_no",
            "purchase_price",
            "vat_rate",
            "color",
            "length",
            "size",
            "received_at",
        )
        widgets = {
            "received_at": DATE_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.Meta.fields:
            self.fields[name].required = True
        self.fields["supplier"].empty_label = "Bitte wählen"


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


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = (
            "supplier",
            "product_name",
            "invoice_no",
            "purchase_price",
            "vat_rate",
            "color",
            "length",
            "size",
            "received_at",
            "product",
            "status",
            "current_phase",
            "reserved_for",
            "reserved_until",
            "sold_channel",
        )
        widgets = {
            "received_at": DATE_WIDGET,
            "reserved_until": DATETIME_WIDGET,
        }
