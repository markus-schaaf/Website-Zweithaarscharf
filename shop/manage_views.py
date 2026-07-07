from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.views import RoleRequiredMixin

from .forms import ConfiguratorGroupForm, ConfiguratorOptionForm, ProductForm
from .models import ConfiguratorGroup, ConfiguratorOption, Product

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


class KonfiguratorListeView(RoleRequiredMixin, ListView):
    allowed_roles = STAFF_ROLES
    template_name = "tasty/account/configurator_list.html"
    context_object_name = "gruppen"

    def get_queryset(self):
        # Verwaltung sieht auch inaktive Gruppen/Optionen
        return ConfiguratorGroup.objects.prefetch_related("options")


class GruppeErstellenView(RoleRequiredMixin, CreateView):
    allowed_roles = STAFF_ROLES
    form_class = ConfiguratorGroupForm
    template_name = "tasty/account/configurator_group_form.html"
    success_url = reverse_lazy("shop_manage:configurator_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Gruppe „{form.instance.name}“ wurde angelegt.")
        return response


class GruppeBearbeitenView(RoleRequiredMixin, UpdateView):
    allowed_roles = STAFF_ROLES
    model = ConfiguratorGroup
    form_class = ConfiguratorGroupForm
    template_name = "tasty/account/configurator_group_form.html"
    success_url = reverse_lazy("shop_manage:configurator_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Gruppe „{form.instance.name}“ wurde gespeichert.")
        return response


class OptionErstellenView(RoleRequiredMixin, CreateView):
    allowed_roles = STAFF_ROLES
    form_class = ConfiguratorOptionForm
    template_name = "tasty/account/configurator_option_form.html"
    success_url = reverse_lazy("shop_manage:configurator_list")

    def get_initial(self):
        initial = super().get_initial()
        group_pk = self.request.GET.get("gruppe")
        if group_pk and group_pk.isdigit():
            initial["group"] = group_pk
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Option „{form.instance.name}“ wurde angelegt.")
        return response


class OptionBearbeitenView(RoleRequiredMixin, UpdateView):
    allowed_roles = STAFF_ROLES
    model = ConfiguratorOption
    form_class = ConfiguratorOptionForm
    template_name = "tasty/account/configurator_option_form.html"
    success_url = reverse_lazy("shop_manage:configurator_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Option „{form.instance.name}“ wurde gespeichert.")
        return response


class OptionLoeschenView(RoleRequiredMixin, DeleteView):
    allowed_roles = STAFF_ROLES
    model = ConfiguratorOption
    template_name = "tasty/account/configurator_option_confirm_delete.html"
    success_url = reverse_lazy("shop_manage:configurator_list")

    def form_valid(self, form):
        messages.success(self.request, f"Option „{self.object.name}“ wurde gelöscht.")
        return super().form_valid(form)
