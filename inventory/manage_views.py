"""Warenwirtschaft-Verwaltung auf der Website (nur All Power / Admin).
Muster wie shop/manage_views.py (RoleRequiredMixin).
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from accounts.views import RoleRequiredMixin

from .forms import ProductionPhaseForm, StockItemForm, SupplierForm
from .models import ProductionPhase, StockItem, StockItemEvent, Supplier

User = get_user_model()
STAFF_ROLES = (User.Role.ALL_POWER, User.Role.ADMIN)


class StaffMixin(RoleRequiredMixin):
    allowed_roles = STAFF_ROLES


# --- Dashboard -------------------------------------------------------------

class HomeView(StaffMixin, TemplateView):
    template_name = "tasty/account/warenwirtschaft_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["anzahl_verfuegbar"] = StockItem.objects.filter(
            status=StockItem.Status.VERFUEGBAR
        ).count()
        ctx["anzahl_gesamt"] = StockItem.objects.count()
        ctx["anzahl_lieferanten"] = Supplier.objects.count()
        ctx["anzahl_phasen"] = ProductionPhase.objects.filter(is_active=True).count()
        return ctx


# --- Lieferanten -----------------------------------------------------------

class SupplierListView(StaffMixin, ListView):
    model = Supplier
    template_name = "tasty/account/supplier_list.html"
    context_object_name = "lieferanten"


class SupplierCreateView(StaffMixin, CreateView):
    form_class = SupplierForm
    template_name = "tasty/account/supplier_form.html"
    success_url = reverse_lazy("inventory_manage:supplier_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Lieferant „{form.instance.name}“ gespeichert.")
        return response


class SupplierUpdateView(StaffMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "tasty/account/supplier_form.html"
    success_url = reverse_lazy("inventory_manage:supplier_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Lieferant „{form.instance.name}“ gespeichert.")
        return response


# --- Fertigungsphasen ------------------------------------------------------

class PhaseListView(StaffMixin, ListView):
    model = ProductionPhase
    template_name = "tasty/account/phase_list.html"
    context_object_name = "phasen"


class PhaseCreateView(StaffMixin, CreateView):
    form_class = ProductionPhaseForm
    template_name = "tasty/account/phase_form.html"
    success_url = reverse_lazy("inventory_manage:phase_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Phase „{form.instance.name}“ gespeichert.")
        return response


class PhaseUpdateView(StaffMixin, UpdateView):
    model = ProductionPhase
    form_class = ProductionPhaseForm
    template_name = "tasty/account/phase_form.html"
    success_url = reverse_lazy("inventory_manage:phase_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Phase „{form.instance.name}“ gespeichert.")
        return response


# --- Bestand (StockItem) ---------------------------------------------------

class StockItemListView(StaffMixin, ListView):
    model = StockItem
    template_name = "tasty/account/stockitem_list.html"
    context_object_name = "stuecke"

    def get_queryset(self):
        return (
            StockItem.objects.select_related("product", "current_phase", "supplier", "reserved_for")
            .all()
        )


class StockItemCreateView(StaffMixin, CreateView):
    form_class = StockItemForm
    template_name = "tasty/account/stockitem_form.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f"Bestandsstück „{form.instance.inventory_no}“ angelegt."
        )
        return response


class StockItemUpdateView(StaffMixin, UpdateView):
    model = StockItem
    form_class = StockItemForm
    template_name = "tasty/account/stockitem_form.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["events"] = self.object.events.select_related("changed_by").all()
        return ctx

    def form_valid(self, form):
        # Status-/Phasenwechsel automatisch in die Historie schreiben (wer/wann)
        old = StockItem.objects.get(pk=form.instance.pk)
        old_status_display = old.get_status_display()
        old_status = old.status
        old_phase_id = old.current_phase_id
        old_phase = str(old.current_phase or "")
        response = super().form_valid(form)
        obj = form.instance
        if old_status != obj.status:
            obj.log_event(
                StockItemEvent.Kind.STATUS, old_status_display,
                obj.get_status_display(), by=self.request.user,
            )
        if old_phase_id != obj.current_phase_id:
            obj.log_event(
                StockItemEvent.Kind.PHASE, old_phase,
                str(obj.current_phase or ""), by=self.request.user,
            )
        messages.success(
            self.request, f"Bestandsstück „{obj.inventory_no}“ gespeichert."
        )
        return response
