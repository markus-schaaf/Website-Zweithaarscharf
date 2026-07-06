import json
from functools import wraps

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from .models import MAX_QTY, Cart, CartItem, Product
from .templatetags.shop_extras import euro


def ajax_login_required(view_func):
    """Liefert 401 JSON statt Login-Redirect — fuer fetch-Aufrufe."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "auth_required"}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def _parse_json(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (ValueError, UnicodeDecodeError):
        return None


def _clamp_qty(value):
    try:
        return max(1, min(int(value), MAX_QTY))
    except (TypeError, ValueError):
        return 1


def _get_product(data, user):
    try:
        return Product.objects.visible_for(user).get(pk=int(data.get("product_id")))
    except (Product.DoesNotExist, TypeError, ValueError):
        return None


class WigsView(TemplateView):
    template_name = "tasty/menu.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.visible_for(self.request.user)
        context.update(
            {
                "active": "wigs",
                "damen_products": products.filter(category=Product.Category.DAMEN),
                "herren_products": products.filter(category=Product.Category.HERREN),
                "pflege_products": products.filter(category=Product.Category.PFLEGE),
                "rohling_products": products.filter(category=Product.Category.ROHLING),
            }
        )
        return context


class CartPageView(TemplateView):
    template_name = "tasty/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            cart = Cart.objects.filter(user=self.request.user).first()
            context["cart"] = cart
            context["cart_items"] = (
                cart.items.select_related("product") if cart else []
            )
        return context


@require_GET
def api_products(request):
    products = {
        str(p.id): {
            "id": p.id,
            "name": p.name,
            "label": p.label,
            "category": p.category,
            "audience": p.audience,
            "price": float(p.price),
            "price_display": p.price_display,
        }
        for p in Product.objects.visible_for(request.user)
    }
    return JsonResponse({"products": products})


def _cart_payload(cart):
    items = [
        {
            "product_id": item.product_id,
            "name": item.product.name,
            "quantity": item.quantity,
            "price_display": item.product.price_display,
            "line_total_display": euro(item.line_total),
        }
        for item in cart.items.select_related("product")
    ]
    return {
        "count": cart.total_quantity,
        "items": items,
        "total_display": euro(cart.total_price),
    }


@require_GET
@ajax_login_required
def api_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return JsonResponse(_cart_payload(cart))


@require_POST
@ajax_login_required
def api_add(request):
    data = _parse_json(request)
    if data is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    product = _get_product(data, request.user)
    if product is None:
        return JsonResponse({"error": "product_not_found"}, status=404)
    quantity = _clamp_qty(data.get("quantity", 1))

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"quantity": quantity}
    )
    if not created:
        item.quantity = min(item.quantity + quantity, MAX_QTY)
        item.save()
    return JsonResponse({"ok": True, "count": cart.total_quantity})


@require_POST
@ajax_login_required
def api_update(request):
    data = _parse_json(request)
    if data is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    product = _get_product(data, request.user)
    if product is None:
        return JsonResponse({"error": "product_not_found"}, status=404)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    try:
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_quantity"}, status=400)

    item = cart.items.filter(product=product).first()
    if quantity <= 0:
        if item:
            item.delete()
        quantity = 0
        line_total_display = euro(0)
    else:
        quantity = min(quantity, MAX_QTY)
        if item is None:
            item = CartItem(cart=cart, product=product)
        item.quantity = quantity
        item.save()
        line_total_display = euro(item.line_total)

    return JsonResponse(
        {
            "ok": True,
            "count": cart.total_quantity,
            "quantity": quantity,
            "line_total_display": line_total_display,
            "total_display": euro(cart.total_price),
        }
    )


@require_POST
@ajax_login_required
def api_remove(request):
    data = _parse_json(request)
    if data is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    try:
        product_id = int(data.get("product_id"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "product_not_found"}, status=404)
    cart.items.filter(product_id=product_id).delete()
    return JsonResponse(
        {
            "ok": True,
            "count": cart.total_quantity,
            "total_display": euro(cart.total_price),
        }
    )


@require_POST
@ajax_login_required
def api_merge(request):
    data = _parse_json(request)
    if data is None or not isinstance(data.get("items"), dict):
        return JsonResponse({"error": "invalid_json"}, status=400)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    with transaction.atomic():
        for product_id, quantity in data["items"].items():
            try:
                product = Product.objects.visible_for(request.user).get(pk=int(product_id))
            except (Product.DoesNotExist, TypeError, ValueError):
                continue
            quantity = _clamp_qty(quantity)
            item, created = CartItem.objects.get_or_create(
                cart=cart, product=product, defaults={"quantity": quantity}
            )
            if not created:
                item.quantity = min(item.quantity + quantity, MAX_QTY)
                item.save()
    return JsonResponse({"ok": True, "count": cart.total_quantity})
