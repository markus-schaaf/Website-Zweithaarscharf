from django.contrib import admin

from .models import Cart, CartItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "audience", "price", "badge", "is_active", "sort_order")
    list_filter = ("category", "audience", "is_active", "badge")
    search_fields = ("name", "label")
    prepopulated_fields = {"slug": ("label",)}
    list_editable = ("is_active", "sort_order")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "total_quantity", "updated_at")
    inlines = [CartItemInline]
