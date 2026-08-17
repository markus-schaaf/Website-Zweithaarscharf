from django import forms

from .models import ConfiguratorGroup, ConfiguratorOption, Product, Product3DAsset
from .services.imaging import normalize_upload


class NormalizedImageMixin:
    """Wandelt frisch hochgeladene Bildfelder nach JPEG um.

    Ohne das landen HEIC-Dateien der iPhone-Kamera unveraendert im
    Medienordner und werden von keinem Browser angezeigt.
    """

    image_fields = ()

    def clean(self):
        cleaned = super().clean()
        for name in self.image_fields:
            datei = cleaned.get(name)
            # Nur Neuhochgeladenes anfassen; unveraenderte Felder tragen das
            # bereits gespeicherte FieldFile ohne content_type.
            if datei and hasattr(datei, "content_type"):
                try:
                    cleaned[name] = normalize_upload(datei)
                except forms.ValidationError as fehler:
                    self.add_error(name, fehler)
        return cleaned


class ProductForm(NormalizedImageMixin, forms.ModelForm):
    image_fields = ("image",)

    class Meta:
        model = Product
        fields = (
            "name",
            "label",
            "category",
            "audience",
            "price",
            "badge",
            "description",
            "image",
            "hair_length",
            "hair_size",
            "hair_structure",
            "hair_color",
            "hair_density",
            "cap_type",
            "content_amount",
            "usage_notes",
            "track_stock",
            "stock_mode",
            "stock_quantity",
            "is_active",
            "sort_order",
        )
        widgets = {
            "usage_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def save(self, commit=True):
        product = super().save(commit=False)
        product.ensure_slug()
        if commit:
            product.save()
        return product


class Product3DAssetForm(NormalizedImageMixin, forms.ModelForm):
    image_fields = (
        "source_image_1", "source_image_2", "source_image_3", "source_image_4",
    )

    class Meta:
        model = Product3DAsset
        fields = (
            "source_image_1",
            "source_image_2",
            "source_image_3",
            "source_image_4",
            "comp_offset_x",
            "comp_offset_y",
            "comp_scale",
        )
        widgets = {
            "comp_offset_x": forms.NumberInput(attrs={"step": "0.05"}),
            "comp_offset_y": forms.NumberInput(attrs={"step": "0.05"}),
            "comp_scale": forms.NumberInput(attrs={"step": "0.05"}),
        }

    # Feinjustierung ist optional — leere Felder fallen auf die Model-Defaults zurück
    COMP_DEFAULTS = {"comp_offset_x": 0.0, "comp_offset_y": 0.0, "comp_scale": 1.0}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.COMP_DEFAULTS:
            self.fields[name].required = False

    def clean(self):
        cleaned = super().clean()  # wandelt die Quellbilder um
        for name, default in self.COMP_DEFAULTS.items():
            if cleaned.get(name) is None:
                cleaned[name] = default
        return cleaned


class ConfiguratorGroupForm(forms.ModelForm):
    class Meta:
        model = ConfiguratorGroup
        fields = ("name", "sort_order", "is_active")


class ConfiguratorOptionForm(forms.ModelForm):
    class Meta:
        model = ConfiguratorOption
        fields = ("group", "name", "surcharge", "sort_order", "is_active")
