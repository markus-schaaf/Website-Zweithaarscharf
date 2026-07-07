from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    ConfiguratorGroup,
    ConfiguratorOption,
    Product,
    Product3DAsset,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "audience", "price", "badge", "is_active", "sort_order")
    list_filter = ("category", "audience", "is_active", "badge")
    search_fields = ("name", "label")
    prepopulated_fields = {"slug": ("label",)}
    list_editable = ("is_active", "sort_order")


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
