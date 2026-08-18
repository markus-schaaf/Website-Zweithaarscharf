from django import forms
from django.contrib import admin

from .forms import NormalizedImageMixin
from .models import (
    Cart,
    CartItem,
    ConfiguratorGroup,
    ConfiguratorOption,
    Product,
    Product3DAsset,
    ProductImage,
)


# Der Admin baut sich seine Formulare selbst und wuerde die Umwandlung sonst
# umgehen - ein HEIC vom iPhone laege danach unanzeigbar im Medienordner.
class ProductAdminForm(NormalizedImageMixin, forms.ModelForm):
    image_fields = ("image",)

    class Meta:
        model = Product
        fields = "__all__"


class ProductImageAdminForm(NormalizedImageMixin, forms.ModelForm):
    image_fields = ("image",)

    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageAdminForm
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "audience", "price", "stock_mode", "stock_quantity", "is_active", "sort_order")
    list_filter = ("category", "audience", "stock_mode", "is_active", "badge")
    search_fields = ("name", "label")
    prepopulated_fields = {"slug": ("label",)}
    list_editable = ("is_active", "sort_order")
    form = ProductAdminForm
    inlines = [ProductImageInline]


# Nur zur Fehlersuche — gepflegt wird das 3D-Modell in der eigenen
# Produktverwaltung (konto/produkte/<pk>/3d/), die auch All-Power-Nutzern offensteht.
@admin.register(Product3DAsset)
class Product3DAssetAdmin(admin.ModelAdmin):
    list_display = ("product", "status", "is_public", "provider", "updated_at")
    list_filter = ("status", "is_public", "provider")
    readonly_fields = (
        "status",
        "error_message",
        "provider",
        "provider_job_id",
        "generated_by",
        "created_at",
        "updated_at",
    )


class ConfiguratorOptionInline(admin.TabularInline):
    model = ConfiguratorOption
    extra = 0


@admin.register(ConfiguratorGroup)
class ConfiguratorGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    inlines = [ConfiguratorOptionInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "total_quantity", "updated_at")
    inlines = [CartItemInline]
