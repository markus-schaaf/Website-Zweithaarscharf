from django import forms
from django.utils.text import slugify

from .models import Product


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
            "is_active",
            "sort_order",
        )

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
