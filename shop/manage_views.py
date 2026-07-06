from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from accounts.views import RoleRequiredMixin

from .forms import ProductForm
from .models import Product

User = get_user_model()

STAFF_ROLES = (User.Role.ALL_POWER, User.Role.ADMIN)


class ProduktListeView(RoleRequiredMixin, ListView):
    allowed_roles = STAFF_ROLES
    model = Product  # bewusst ungefiltert: Verwaltung sieht auch inaktive Produkte
    template_name = "tasty/account/product_list.html"
    context_object_name = "produkte"


class ProduktErstellenView(RoleRequiredMixin, CreateView):
    allowed_roles = STAFF_ROLES
    form_class = ProductForm
    template_name = "tasty/account/product_form.html"
    success_url = reverse_lazy("shop_manage:product_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Produkt „{form.instance.name}“ wurde angelegt.")
        return response


class ProduktBearbeitenView(RoleRequiredMixin, UpdateView):
    allowed_roles = STAFF_ROLES
    model = Product
    form_class = ProductForm
    template_name = "tasty/account/product_form.html"
    success_url = reverse_lazy("shop_manage:product_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Produkt „{form.instance.name}“ wurde gespeichert.")
        return response
