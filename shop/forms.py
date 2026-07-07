from django import forms
from django.utils.text import slugify

from .models import ConfiguratorGroup, ConfiguratorOption, Product


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


class ConfiguratorGroupForm(forms.ModelForm):
    class Meta:
        model = ConfiguratorGroup
        fields = ("name", "sort_order", "is_active")


class ConfiguratorOptionForm(forms.ModelForm):
    class Meta:
        model = ConfiguratorOption
        fields = ("group", "name", "surcharge", "sort_order", "is_active")
