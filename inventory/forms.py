from django import forms

from .models import ProductionPhase, StockItem, Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ("name", "contact", "email", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ProductionPhaseForm(forms.ModelForm):
    class Meta:
        model = ProductionPhase
        fields = ("name", "sort_order", "is_active")


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = (
            "product",
            "inventory_no",
            "supplier",
            "purchase_price",
            "received_at",
            "status",
            "current_phase",
            "reserved_for",
            "reserved_until",
            "sold_channel",
        )
        widgets = {
            "received_at": forms.DateInput(attrs={"type": "date"}),
            "reserved_until": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
