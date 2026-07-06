from .models import Cart


def cart(request):
    if request.user.is_authenticated:
        user_cart = Cart.objects.filter(user=request.user).first()
        return {"cart_item_count": user_cart.total_quantity if user_cart else 0}
    return {"cart_item_count": 0}
