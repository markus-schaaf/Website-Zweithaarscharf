from django.contrib import admin

from .models import (
    Order,
    OrderItem,
    ProductionPhase,
    StockItem,
    StockItemEvent,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact", "email")
    search_fields = ("name", "contact", "email")


@admin.register(ProductionPhase)
class ProductionPhaseAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    ordering = ("sort_order", "name")


class StockItemEventInline(admin.TabularInline):
    """Historie schreibgeschuetzt anzeigen (wird automatisch gefuellt)."""

    model = StockItemEvent
    extra = 0
    can_delete = False
    fields = ("changed_at", "kind", "from_value", "to_value", "changed_by", "note")
    readonly_fields = ("changed_at", "kind", "from_value", "to_value", "changed_by", "note")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_no", "product", "status", "current_phase",
        "reserved_for", "supplier",
    )
    list_filter = ("status", "current_phase", "supplier", "product__stock_mode")
    search_fields = ("inventory_no", "product__name")
    autocomplete_fields = ("product", "reserved_for")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StockItemEventInline]

    def save_model(self, request, obj, form, change):
        """Status- und Phasenwechsel automatisch in die Historie schreiben."""
        pending = []
        if change:
            old = StockItem.objects.get(pk=obj.pk)
            if old.status != obj.status:
                pending.append((
                    StockItemEvent.Kind.STATUS,
                    old.get_status_display(), obj.get_status_display(),
                ))
            if old.current_phase_id != obj.current_phase_id:
                pending.append((
                    StockItemEvent.Kind.PHASE,
                    str(old.current_phase or ""), str(obj.current_phase or ""),
                ))
        super().save_model(request, obj, form, change)
        for kind, frm, to in pending:
            obj.log_event(kind, frm, to, by=request.user)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product", "stock_item")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "created_at", "status", "export_status", "total",
    )
    list_filter = ("status", "export_status")
    search_fields = ("id", "user__email")
    readonly_fields = ("created_at",)
    inlines = [OrderItemInline]
