from django.contrib import admin

from .models import (
    AttributeOption,
    Order,
    OrderItem,
    Project,
    StockItem,
    StockItemEvent,
    StockItemImage,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "next_number", "contact", "email")
    search_fields = ("name", "code", "contact", "email")


@admin.register(AttributeOption)
class AttributeOptionAdmin(admin.ModelAdmin):
    list_display = ("group", "name", "sort_order", "is_active")
    list_filter = ("group", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "stock_item", "customer_display", "status", "due_date")
    list_filter = ("status",)
    search_fields = ("title", "customer_name", "customer__email")
    autocomplete_fields = ("stock_item", "customer")


class StockItemEventInline(admin.TabularInline):
    """Historie schreibgeschuetzt anzeigen (wird automatisch gefuellt)."""

    model = StockItemEvent
    extra = 0
    can_delete = False
    fields = ("changed_at", "kind", "from_value", "to_value", "changed_by", "note")
    readonly_fields = ("changed_at", "kind", "from_value", "to_value", "changed_by", "note")

    def has_add_permission(self, request, obj=None):
        return False


class StockItemImageInline(admin.TabularInline):
    model = StockItemImage
    extra = 0
    fields = ("image", "kind", "sort_order")


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_no", "product_name", "supplier", "invoice_no",
        "status", "product", "reserved_for",
    )
    list_filter = ("status", "stock_mode", "shop_category", "supplier")
    search_fields = ("inventory_no", "product_name", "invoice_no", "product__name")
    autocomplete_fields = ("product", "reserved_for")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StockItemImageInline, StockItemEventInline]

    def get_readonly_fields(self, request, obj=None):
        """Eine einmal vergebene Produktnummer bleibt unveraendert."""
        if obj:
            return self.readonly_fields + ("inventory_no",)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """Statuswechsel automatisch in die Historie schreiben."""
        alt = None
        if change:
            vorher = StockItem.objects.get(pk=obj.pk)
            if vorher.status != obj.status:
                alt = vorher.get_status_display()
        super().save_model(request, obj, form, change)
        if alt is not None:
            obj.log_event(
                StockItemEvent.Kind.STATUS, alt, obj.get_status_display(),
                by=request.user,
            )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product", "stock_item")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "customer_display", "sold_on", "channel", "status",
        "export_status", "total",
    )
    list_filter = ("status", "export_status", "channel")
    search_fields = ("id", "user__email", "customer_name")
    readonly_fields = ("created_at",)
    inlines = [OrderItemInline]
