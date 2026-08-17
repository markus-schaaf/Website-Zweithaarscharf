"""Warenwirtschaft-Verwaltung auf der Website (nur All Power / Admin).
Muster wie shop/manage_views.py (RoleRequiredMixin).
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from accounts.views import RoleRequiredMixin

from .forms import (
    AttributeOptionForm,
    GoodsReceiptForm,
    ProductionPhaseForm,
    ProjectForm,
    StockItemForm,
    SupplierForm,
)
from .models import (
    AttributeOption,
    ProductionPhase,
    Project,
    StockItem,
    StockItemEvent,
    StockItemImage,
    Supplier,
)
from .numbering import build_inventory_no, reserve_numbers

User = get_user_model()
STAFF_ROLES = (User.Role.ALL_POWER, User.Role.ADMIN)


class StaffMixin(RoleRequiredMixin):
    allowed_roles = STAFF_ROLES


# --- Bilder ----------------------------------------------------------------

def save_images(stock_item, dateien, kind, start=0):
    """Hochgeladene Dateien als Bilder anhaengen."""
    StockItemImage.objects.bulk_create([
        StockItemImage(stock_item=stock_item, image=f, kind=kind, sort_order=start + i)
        for i, f in enumerate(dateien)
    ])


def apply_image_changes(request, stock_item, kind, upload_field):
    """Loeschen, Neusortieren und Hochladen fuer eine Bildergruppe."""
    delete_ids = request.POST.getlist(f"delete_images_{kind}")
    if delete_ids:
        stock_item.images.filter(pk__in=delete_ids).delete()

    # Reihenfolge kommt als Liste von Bild-IDs in der neuen Sortierung
    order = [
        pk for pk in request.POST.getlist(f"image_order_{kind}")
        if pk not in delete_ids
    ]
    for position, pk in enumerate(order):
        stock_item.images.filter(pk=pk).update(sort_order=position)

    neue = request.FILES.getlist(upload_field)
    if neue:
        save_images(stock_item, neue, kind, start=len(order))


# --- Dashboard -------------------------------------------------------------

class HomeView(StaffMixin, TemplateView):
    template_name = "tasty/account/warenwirtschaft_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["anzahl_verfuegbar"] = StockItem.objects.filter(
            status=StockItem.Status.VERFUEGBAR
        ).count()
        ctx["anzahl_gesamt"] = StockItem.objects.count()
        ctx["anzahl_veroeffentlicht"] = StockItem.objects.filter(is_published=True).count()
        ctx["anzahl_projekte"] = Project.objects.exclude(
            status__in=(Project.Status.ABGEHOLT, Project.Status.STORNIERT)
        ).count()
        ctx["anzahl_lieferanten"] = Supplier.objects.count()
        ctx["anzahl_phasen"] = ProductionPhase.objects.filter(is_active=True).count()
        ctx["anzahl_werte"] = AttributeOption.objects.filter(is_active=True).count()
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

    def _safe_next(self):
        target = self.request.POST.get("next") or self.request.GET.get("next", "")
        if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return target
        return ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = self._safe_next()
        return ctx

    def get_success_url(self):
        target = self._safe_next()
        if target:
            trenner = "&" if "?" in target else "?"
            return f"{target}{trenner}supplier={self.object.pk}"
        return str(self.success_url)

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


# --- Auswahlwerte ----------------------------------------------------------

class AttributeListView(StaffMixin, ListView):
    model = AttributeOption
    template_name = "tasty/account/attribute_list.html"
    context_object_name = "werte"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Nach Merkmal gruppiert ausgeben, Reihenfolge wie im Modell definiert
        gruppen = []
        for value, label in AttributeOption.Group.choices:
            gruppen.append({
                "label": label,
                "value": value,
                "werte": [w for w in ctx["werte"] if w.group == value],
            })
        ctx["gruppen"] = gruppen
        return ctx


class AttributeCreateView(StaffMixin, CreateView):
    form_class = AttributeOptionForm
    template_name = "tasty/account/attribute_form.html"
    success_url = reverse_lazy("inventory_manage:attribute_list")

    def get_initial(self):
        initial = super().get_initial()
        group = self.request.GET.get("merkmal")
        if group in AttributeOption.Group.values:
            initial["group"] = group
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Wert „{form.instance.name}“ gespeichert.")
        return response


class AttributeUpdateView(StaffMixin, UpdateView):
    model = AttributeOption
    form_class = AttributeOptionForm
    template_name = "tasty/account/attribute_form.html"
    success_url = reverse_lazy("inventory_manage:attribute_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Wert „{form.instance.name}“ gespeichert.")
        return response


# --- Bestand (StockItem) ---------------------------------------------------

class StockItemListView(StaffMixin, ListView):
    model = StockItem
    template_name = "tasty/account/stockitem_list.html"
    context_object_name = "stuecke"

    def get_queryset(self):
        qs = StockItem.objects.select_related(
            "product", "current_phase", "supplier", "reserved_for"
        ).prefetch_related("images")

        suche = self.request.GET.get("q", "").strip()
        if suche:
            qs = qs.filter(
                Q(inventory_no__icontains=suche)
                | Q(product_name__icontains=suche)
                | Q(invoice_no__icontains=suche)
                | Q(supplier__name__icontains=suche)
                | Q(color__icontains=suche)
            )

        status = self.request.GET.get("status", "")
        if status in StockItem.Status.values:
            qs = qs.filter(status=status)

        kategorie = self.request.GET.get("kategorie", "")
        if kategorie in dict(StockItem.SHOP_CATEGORIES):
            qs = qs.filter(shop_category=kategorie)

        hersteller = self.request.GET.get("hersteller", "")
        if hersteller.isdigit():
            qs = qs.filter(supplier_id=int(hersteller))

        shop = self.request.GET.get("shop", "")
        if shop == "ja":
            qs = qs.filter(is_published=True)
        elif shop == "nein":
            qs = qs.filter(is_published=False)

        return qs.order_by("-created_at", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # order_by() leeren: die Meta-Sortierung wuerde sonst in das GROUP BY wandern
        zaehler = {
            row["status"]: row["n"]
            for row in StockItem.objects.values("status").order_by().annotate(n=Count("id"))
        }
        ctx["filter"] = {
            "q": self.request.GET.get("q", ""),
            "status": self.request.GET.get("status", ""),
            "kategorie": self.request.GET.get("kategorie", ""),
            "hersteller": self.request.GET.get("hersteller", ""),
            "shop": self.request.GET.get("shop", ""),
        }
        ctx["status_chips"] = [
            {"value": value, "label": label, "count": zaehler.get(value, 0)}
            for value, label in StockItem.Status.choices
        ]
        # Basis fuer die Status-Links: alle uebrigen Filter beibehalten
        basis = self.request.GET.copy()
        basis.pop("status", None)
        basis.pop("page", None)
        ctx["basis_query"] = basis.urlencode()
        ctx["anzahl_gesamt"] = StockItem.objects.count()
        ctx["kategorien"] = StockItem.SHOP_CATEGORIES
        ctx["lieferanten"] = Supplier.objects.all()
        return ctx


class StockItemCreateView(StaffMixin, CreateView):
    """Wareneingang: legt je erfasstem Stueck einen eigenen Datensatz mit
    automatisch vergebener Produktnummer an. Mengenartikel bekommen einen
    Datensatz mit Stueckzahl. Mindestens ein Eingangsbild ist Pflicht.
    """

    form_class = GoodsReceiptForm
    template_name = "tasty/account/goodsreceipt_form.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def get_initial(self):
        initial = super().get_initial()
        supplier_id = self.request.GET.get("supplier")
        if supplier_id:
            initial["supplier"] = supplier_id
        return initial

    def form_valid(self, form):
        bilder = self.request.FILES.getlist("eingang_images")
        if not bilder:
            form.add_error(
                None, "Bitte mindestens ein Foto der Ware hochladen."
            )
            return self.form_invalid(form)

        data = form.cleaned_data
        supplier = data["supplier"]
        menge = data["quantity"]
        einzeln = data["stock_mode"] == StockItem.StockMode.EINZELSTUECK
        counters = reserve_numbers(supplier, menge if einzeln else 1)

        felder = (
            "product_name", "invoice_no", "purchase_price", "vat_rate",
            "color", "length", "size", "structure", "density", "cap_type",
            "received_at", "stock_mode", "shop_category", "audience",
            "sale_price", "notes",
        )
        gemeinsam = {name: data[name] for name in felder}

        with transaction.atomic():
            for counter in counters:
                stueck = StockItem.objects.create(
                    inventory_no=build_inventory_no(
                        supplier, data["color"], data["length"], counter
                    ),
                    supplier=supplier,
                    quantity=1 if einzeln else menge,
                    **gemeinsam,
                )
                save_images(stueck, bilder, StockItemImage.Kind.EINGANG)
                stueck.log_event(
                    StockItemEvent.Kind.EINGANG, "", stueck.get_status_display(),
                    by=self.request.user,
                    note=f"Wareneingang, Rechnung {stueck.invoice_no}",
                )

        erste = build_inventory_no(supplier, data["color"], data["length"], counters[0])
        if einzeln and len(counters) > 1:
            letzte = build_inventory_no(
                supplier, data["color"], data["length"], counters[-1]
            )
            messages.success(
                self.request, f"{len(counters)} Stück erfasst ({erste} bis {letzte})."
            )
        else:
            messages.success(
                self.request,
                f"Erfasst: {erste}" + ("" if einzeln else f" ({menge} Stück)"),
            )
        # Nicht get_success_url(): es gibt kein einzelnes self.object.
        return HttpResponseRedirect(str(self.success_url))


class StockItemUpdateView(StaffMixin, UpdateView):
    model = StockItem
    form_class = StockItemForm
    template_name = "tasty/account/stockitem_form.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["events"] = self.object.events.select_related("changed_by").all()
        ctx["eingang_bilder"] = self.object.images.filter(
            kind=StockItemImage.Kind.EINGANG
        )
        ctx["shop_bilder"] = self.object.images.filter(kind=StockItemImage.Kind.SHOP)
        ctx["projekte"] = self.object.projects.all()
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

        apply_image_changes(
            self.request, obj, StockItemImage.Kind.EINGANG, "eingang_images"
        )
        apply_image_changes(
            self.request, obj, StockItemImage.Kind.SHOP, "shop_images"
        )

        if old_status != obj.status:
            obj.log_event(
                StockItemEvent.Kind.STATUS, old_status_display,
                obj.get_status_display(), by=self.request.user,
            )
            self._handle_sale(obj)
        if old_phase_id != obj.current_phase_id:
            obj.log_event(
                StockItemEvent.Kind.PHASE, old_phase,
                str(obj.current_phase or ""), by=self.request.user,
            )
        if obj.is_published:
            # Geaenderte Angaben sofort in den Shop durchreichen
            try:
                obj.publish(by=self.request.user)
            except ValidationError as fehler:
                obj.unpublish(by=self.request.user)
                messages.warning(
                    self.request,
                    "Aus dem Shop genommen: " + " ".join(fehler.messages),
                )

        messages.success(
            self.request, f"Bestandsstück „{obj.inventory_no}“ gespeichert."
        )
        return response

    def _handle_sale(self, obj):
        """Verkauf schlaegt sofort auf den Shop durch (geteilter Bestand)."""
        if obj.status != StockItem.Status.VERKAUFT:
            return
        if obj.sold_at is None:
            obj.sold_at = timezone.now()
            obj.save(update_fields=["sold_at", "updated_at"])
        if obj.is_published:
            obj.unpublish(by=self.request.user)


class StockItemPublishView(StaffMixin, View):
    """Bestandsstueck im Shop veroeffentlichen (POST-only)."""

    def post(self, request, pk):
        stueck = get_object_or_404(StockItem, pk=pk)
        try:
            produkt = stueck.publish(by=request.user)
        except ValidationError as fehler:
            for meldung in fehler.messages:
                messages.error(request, meldung)
        else:
            messages.success(
                request, f"„{produkt.name}“ ist jetzt im Shop sichtbar."
            )
        return redirect("inventory_manage:stock_edit", pk=pk)


class StockItemUnpublishView(StaffMixin, View):
    """Bestandsstueck aus dem Shop nehmen (POST-only)."""

    def post(self, request, pk):
        stueck = get_object_or_404(StockItem, pk=pk)
        stueck.unpublish(by=request.user)
        messages.success(request, "Aus dem Shop genommen.")
        return redirect("inventory_manage:stock_edit", pk=pk)


# --- Projekte --------------------------------------------------------------

class ProjectListView(StaffMixin, ListView):
    model = Project
    template_name = "tasty/account/project_list.html"
    context_object_name = "projekte"

    def get_queryset(self):
        return Project.objects.select_related("stock_item", "customer")


class ProjectMixin:
    form_class = ProjectForm
    template_name = "tasty/account/project_form.html"
    success_url = reverse_lazy("inventory_manage:project_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        projekt = form.instance
        stueck = projekt.stock_item
        # Ein geplantes Stueck ist nicht mehr frei verkaeuflich
        if stueck and stueck.status == StockItem.Status.VERFUEGBAR:
            alt = stueck.get_status_display()
            stueck.status = StockItem.Status.RESERVIERT
            stueck.reserved_for = projekt.customer
            stueck.save(update_fields=["status", "reserved_for", "updated_at"])
            stueck.log_event(
                StockItemEvent.Kind.STATUS, alt, stueck.get_status_display(),
                by=self.request.user, note=f"Projekt „{projekt.title}“",
            )
        messages.success(self.request, f"Projekt „{projekt.title}“ gespeichert.")
        return response


class ProjectCreateView(ProjectMixin, StaffMixin, CreateView):
    def get_initial(self):
        initial = super().get_initial()
        stueck_id = self.request.GET.get("bestand")
        if stueck_id and stueck_id.isdigit():
            initial["stock_item"] = stueck_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(ProjectMixin, StaffMixin, UpdateView):
    model = Project


class ProjectApplyPlanView(StaffMixin, View):
    """Plandaten auf das verknuepfte Bestandsstueck uebernehmen (POST-only)."""

    def post(self, request, pk):
        projekt = get_object_or_404(Project, pk=pk)
        if projekt.stock_item is None:
            messages.error(request, "Dem Projekt ist kein Bestandsstück zugeordnet.")
        elif projekt.apply_plan(by=request.user):
            messages.success(
                request,
                f"Plandaten auf {projekt.stock_item.inventory_no} übernommen.",
            )
        else:
            messages.info(request, "Das Bestandsstück entspricht bereits dem Plan.")
        return redirect("inventory_manage:project_edit", pk=pk)
