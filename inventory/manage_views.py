"""Warenwirtschaft-Verwaltung auf der Website (nur All Power / Admin).
Muster wie shop/manage_views.py (RoleRequiredMixin).
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import (
    CreateView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from accounts.views import RoleRequiredMixin
from shop.models import Product

from .forms import (
    GoodsReceiptForm,
    InvoiceRecipientForm,
    ProductionPhaseForm,
    StockItemForm,
    StockItemPublishForm,
    StockItemSellForm,
    SupplierForm,
)
from .models import (
    InvoiceRecipient,
    Order,
    OrderItem,
    ProductionPhase,
    StockItem,
    StockItemEvent,
    Supplier,
)
from .numbering import build_inventory_no, reserve_numbers
from .services.handover import invoice_recipients, send_invoice_mail

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


# --- Rechnungsempfänger ----------------------------------------------------

class RecipientListView(StaffMixin, ListView):
    model = InvoiceRecipient
    template_name = "tasty/account/recipient_list.html"
    context_object_name = "empfaenger"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Ohne aktive Empfänger greift der Rückfall aus den Einstellungen.
        ctx["fallback"] = (
            settings.INVOICE_RECIPIENT_EMAIL
            if not InvoiceRecipient.active_addresses() else ""
        )
        return ctx


class RecipientCreateView(StaffMixin, CreateView):
    form_class = InvoiceRecipientForm
    template_name = "tasty/account/recipient_form.html"
    success_url = reverse_lazy("inventory_manage:recipient_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Empfänger „{form.instance.email}“ gespeichert.")
        return response


class RecipientUpdateView(StaffMixin, UpdateView):
    model = InvoiceRecipient
    form_class = InvoiceRecipientForm
    template_name = "tasty/account/recipient_form.html"
    success_url = reverse_lazy("inventory_manage:recipient_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Empfänger „{form.instance.email}“ gespeichert.")
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
        return StockItem.objects.select_related(
            "product", "current_phase", "supplier", "reserved_for"
        ).order_by("-created_at", "-id")


class StockItemCreateView(StaffMixin, CreateView):
    """Wareneingang: legt je erfasstem Stueck einen eigenen Datensatz mit
    automatisch vergebener Produktnummer an.
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
        data = form.cleaned_data
        supplier = data["supplier"]
        counters = reserve_numbers(supplier, data["quantity"])

        with transaction.atomic():
            for counter in counters:
                stueck = StockItem.objects.create(
                    inventory_no=build_inventory_no(
                        supplier, data["color"], data["length"], counter
                    ),
                    supplier=supplier,
                    product_name=data["product_name"],
                    invoice_no=data["invoice_no"],
                    purchase_price=data["purchase_price"],
                    vat_rate=data["vat_rate"],
                    color=data["color"],
                    length=data["length"],
                    size=data["size"],
                    received_at=data["received_at"],
                )
                stueck.log_event(
                    StockItemEvent.Kind.EINGANG, "", stueck.get_status_display(),
                    by=self.request.user,
                    note=f"Wareneingang, Rechnung {stueck.invoice_no}",
                )

        messages.success(
            self.request,
            f"{len(counters)} Stück erfasst "
            f"({build_inventory_no(supplier, data['color'], data['length'], counters[0])}"
            f" bis {build_inventory_no(supplier, data['color'], data['length'], counters[-1])})."
        )
        # Nicht get_success_url(): es gibt kein einzelnes self.object.
        return HttpResponseRedirect(str(self.success_url))


class StockItemPublishView(StaffMixin, FormView):
    """Bestandsstueck einem Shop-Produkt zuordnen und damit online stellen."""

    form_class = StockItemPublishForm
    template_name = "tasty/account/stockitem_publish.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def dispatch(self, request, *args, **kwargs):
        self.stueck = get_object_or_404(StockItem, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        # Was der Wareneingang schon weiss, vorbelegen.
        return {
            "product": self.stueck.product_id,
            "name": self.stueck.product_name,
            "label": self.stueck.product_name[:60],
            "category": Product.Category.BESTAND,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stueck"] = self.stueck
        return ctx

    def form_valid(self, form):
        daten = form.cleaned_data
        produkt = daten.get("product")

        with transaction.atomic():
            if produkt is None:
                produkt = Product(
                    name=daten["name"],
                    label=daten["label"],
                    category=daten["category"],
                    price=daten["price"],
                    hair_color=self.stueck.color,
                    hair_length=self.stueck.length,
                    hair_size=self.stueck.size,
                    stock_mode=Product.StockMode.EINZELSTUECK,
                )
                produkt.ensure_slug()
            produkt.track_stock = True
            produkt.save()
            self.stueck.product = produkt
            self.stueck.save(update_fields=["product"])
            self.stueck.log_event(
                StockItemEvent.Kind.STATUS, "", self.stueck.get_status_display(),
                by=self.request.user,
                note=f"Online gestellt als „{produkt.name}“",
            )

        messages.success(
            self.request,
            f"„{self.stueck.inventory_no}“ ist jetzt mit dem Shop-Produkt "
            f"„{produkt.name}“ verknüpft."
        )
        return HttpResponseRedirect(str(self.success_url))


class StockItemSellView(StaffMixin, FormView):
    """Verkauf buchen: Bestellung anlegen, Stueck als verkauft markieren und
    die Rechnungsdaten an den Kollegen schicken.
    """

    form_class = StockItemSellForm
    template_name = "tasty/account/stockitem_sell.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def dispatch(self, request, *args, **kwargs):
        self.stueck = get_object_or_404(StockItem, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            "price": self.stueck.product.price if self.stueck.product else None,
            "sold_on": timezone.localdate(),
            "channel": StockItem.Channel.STUDIO,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stueck"] = self.stueck
        return ctx

    def form_valid(self, form):
        daten = form.cleaned_data
        bezeichnung = (
            self.stueck.product.name if self.stueck.product
            else self.stueck.product_name
        )

        with transaction.atomic():
            bestellung = Order.objects.create(
                user=daten.get("user"),
                customer_name=daten["customer_name"],
                customer_street=daten["customer_street"],
                customer_zip=daten["customer_zip"],
                customer_city=daten["customer_city"],
                customer_email=daten["customer_email"],
                channel=daten["channel"],
                note=daten["note"],
                sold_on=daten["sold_on"],
                total=daten["price"],
            )
            OrderItem.objects.create(
                order=bestellung,
                product=self.stueck.product,
                stock_item=self.stueck,
                description=bezeichnung,
                quantity=1,
                price=daten["price"],
            )
            alt = self.stueck.get_status_display()
            self.stueck.status = StockItem.Status.VERKAUFT
            self.stueck.sold_at = timezone.now()
            self.stueck.sold_channel = daten["channel"]
            self.stueck.save(
                update_fields=["status", "sold_at", "sold_channel", "updated_at"]
            )
            self.stueck.log_event(
                StockItemEvent.Kind.STATUS, alt, self.stueck.get_status_display(),
                by=self.request.user,
                note=f"Verkauf gebucht (Bestellung {bestellung.pk})",
            )

        # Nach dem Commit: ein Mailfehler darf den Verkauf nicht zurueckrollen.
        if send_invoice_mail(bestellung):
            messages.success(
                self.request,
                f"Verkauf gebucht. Die Rechnungsdaten gingen an "
                f"{', '.join(invoice_recipients())}."
            )
        else:
            messages.warning(
                self.request,
                "Verkauf gebucht, aber die Rechnungsmail konnte nicht versendet "
                "werden. Unter „Verkäufe“ lässt sie sich erneut senden."
            )
        return HttpResponseRedirect(str(self.success_url))


class OrderListView(StaffMixin, ListView):
    """Schlanke Übersicht: zeigt vor allem, ob die Rechnungsmail rausging."""

    model = Order
    template_name = "tasty/account/order_list.html"
    context_object_name = "verkaeufe"

    def get_queryset(self):
        return Order.objects.select_related("user").prefetch_related("items")


class OrderResendView(StaffMixin, View):
    def post(self, request, pk):
        bestellung = get_object_or_404(Order, pk=pk)
        if send_invoice_mail(bestellung):
            messages.success(request, f"Rechnungsmail zu Verkauf {pk} erneut gesendet.")
        else:
            messages.error(request, f"Versand zu Verkauf {pk} erneut fehlgeschlagen.")
        return HttpResponseRedirect(reverse("inventory_manage:order_list"))


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
