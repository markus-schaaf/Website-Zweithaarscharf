from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.views import RoleRequiredMixin

from .forms import (
    ConfiguratorGroupForm,
    ConfiguratorOptionForm,
    Product3DAssetForm,
    ProductForm,
)
from .models import ConfiguratorGroup, ConfiguratorOption, Product, Product3DAsset
from .tasks import generate_3d_model

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


class Produkt3DView(RoleRequiredMixin, CreateView):
    """Quellbilder hochladen und die 3D-Generierung starten (neuestes Asset zählt)."""

    allowed_roles = STAFF_ROLES
    form_class = Product3DAssetForm
    template_name = "tasty/account/product_3d.html"

    def get_produkt(self):
        return get_object_or_404(Product, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["produkt"] = self.get_produkt()
        context["asset"] = context["produkt"].assets_3d.first()
        return context

    def form_valid(self, form):
        form.instance.product = self.get_produkt()
        form.instance.generated_by = self.request.user
        response = super().form_valid(form)
        generate_3d_model.delay(self.object.pk)
        messages.success(
            self.request,
            "Bilder gespeichert — die 3D-Generierung läuft im Hintergrund.",
        )
        return response

    def get_success_url(self):
        return reverse("shop_manage:product_3d", kwargs={"pk": self.kwargs["pk"]})


class Produkt3DGenerierenView(RoleRequiredMixin, View):
    """Startet die Generierung für das neueste Asset erneut (POST-only)."""

    allowed_roles = STAFF_ROLES

    def post(self, request, pk):
        produkt = get_object_or_404(Product, pk=pk)
        asset = produkt.assets_3d.first()
        if asset is None:
            messages.error(request, "Bitte zuerst Quellbilder hochladen.")
        else:
            asset.status = Product3DAsset.Status.PENDING
            asset.error_message = ""
            asset.save(update_fields=["status", "error_message", "updated_at"])
            generate_3d_model.delay(asset.pk)
            messages.success(request, "Neu-Generierung gestartet.")
        return redirect("shop_manage:product_3d", pk=pk)


class Produkt3DSichtbarkeitView(RoleRequiredMixin, View):
    """Schaltet die Kunden-Sichtbarkeit des neuesten fertigen Assets um (POST-only)."""

    allowed_roles = STAFF_ROLES

    def post(self, request, pk):
        produkt = get_object_or_404(Product, pk=pk)
        asset = produkt.assets_3d.filter(status=Product3DAsset.Status.DONE).first()
        if asset is None:
            messages.error(request, "Es gibt noch kein fertiges 3D-Modell zum Freigeben.")
        else:
            asset.is_public = not asset.is_public
            asset.save(update_fields=["is_public", "updated_at"])
            messages.success(
                request,
                "3D-Modell ist jetzt für Kunden sichtbar."
                if asset.is_public
                else "3D-Modell ist für Kunden verborgen.",
            )
        return redirect("shop_manage:product_3d", pk=pk)


class Produkt3DStatusView(RoleRequiredMixin, View):
    """Status-JSON für das Auto-Refresh der Verwaltungsseite."""

    allowed_roles = STAFF_ROLES

    def get(self, request, pk):
        asset = (
            Product3DAsset.objects.filter(product_id=pk).first()
        )
        if asset is None:
            return JsonResponse({"status": "none"})
        return JsonResponse(
            {
                "status": asset.status,
                "error_message": asset.error_message,
                "model_url": asset.model_file.url if asset.model_file else "",
                "thumbnail_url": (
                    asset.preview_thumbnail.url if asset.preview_thumbnail else ""
                ),
            }
        )


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
