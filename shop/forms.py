from django import forms
from django.utils.text import slugify

from .models import ConfiguratorGroup, ConfiguratorOption, Product, Product3DAsset


class ProductForm(forms.ModelForm):
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
            "hair_color",
            "hair_structure",
            "cap_type",
            "hair_origin",
            "care_notes",
            "content_amount",
            "usage_notes",
            "is_active",
            "sort_order",
        )
        widgets = {
            "care_notes": forms.Textarea(attrs={"rows": 3}),
            "usage_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def save(self, commit=True):
        product = super().save(commit=False)
        if not product.slug:
            # Slug nur beim Anlegen erzeugen (Schema wie seed_products),
            # Kollisionen bekommen ein -2/-3-Suffix
            base = slugify(f"{product.category}-{product.label}")[:70]
            slug, i = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            product.slug = slug
        if commit:
            product.save()
        return product


class Product3DAssetForm(forms.ModelForm):
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
        cleaned = super().clean()
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
