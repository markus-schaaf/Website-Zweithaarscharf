"""Warenwirtschaft-Verwaltung auf der Website (nur All Power / Admin).
Muster wie shop/manage_views.py (RoleRequiredMixin).
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from accounts.views import RoleRequiredMixin
from shop.models import Product, ProductImage
from shop.services.imaging import normalize_uploads

from .forms import (
    AttributeOptionForm,
    CatalogItemForm,
    GoodsReceiptForm,
    ProjectForm,
    StockItemForm,
    StockItemPublishForm,
    StockItemSellForm,
    SupplierForm,
)
from .models import (
    AttributeOption,
    CatalogItem,
    Order,
    OrderItem,
    Project,
    StockItem,
    StockItemEvent,
    StockItemImage,
    Supplier,
)
from .numbering import build_inventory_no, reserve_numbers
from .services.handover import send_invoice_mail

User = get_user_model()
STAFF_ROLES = (User.Role.ALL_POWER, User.Role.ADMIN)


class StaffMixin(RoleRequiredMixin):
    allowed_roles = STAFF_ROLES


# --- Bilder ----------------------------------------------------------------

def save_images(owner, dateien, kind, start=0):
    """Bereits umgewandelte Dateien als Bilder anhaengen.

    Funktioniert fuer Bestandsstuecke und fuer Bestellartikel: beide fuehren
    ihre Bilder unter related_name "images". Bestellartikel haben kein
    kind-Feld (sie kennen nur Verkaufsbilder), dort wird kind leer uebergeben.

    Das Umwandeln passiert bewusst eine Ebene hoeher (normalize_uploads), damit
    unlesbare Dateien als Formularfehler erscheinen und ein Wareneingang mit
    mehreren Stueck die Fotos nur einmal durch Pillow schickt.
    """
    modell = owner.images.model
    gemeinsam = {owner.images.field.name: owner}
    if kind:
        gemeinsam["kind"] = kind
    modell.objects.bulk_create([
        modell(image=f, sort_order=start + i, **gemeinsam)
        for i, f in enumerate(dateien)
    ])


def apply_image_changes(request, owner, gruppe, upload_field, kind=None):
    """Loeschen, Neusortieren und Hochladen fuer eine Bildergruppe.

    `gruppe` ist der Namensraum der Formularfelder (delete_images_<gruppe>,
    image_order_<gruppe>); `kind` der Wert fuers Modell und faellt auf die
    Gruppe zurueck. Bestellartikel uebergeben kind="" - sie haben das Feld nicht.

    Gibt die Meldungen unlesbarer Dateien zurueck; der Rest wird gespeichert,
    damit ein einzelnes kaputtes Foto nicht den ganzen Vorgang verwirft.
    """
    delete_ids = request.POST.getlist(f"delete_images_{gruppe}")
    if delete_ids:
        owner.images.filter(pk__in=delete_ids).delete()

    # Reihenfolge kommt als Liste von Bild-IDs in der neuen Sortierung
    order = [
        pk for pk in request.POST.getlist(f"image_order_{gruppe}")
        if pk not in delete_ids
    ]
    for position, pk in enumerate(order):
        owner.images.filter(pk=pk).update(sort_order=position)

    neue = request.FILES.getlist(upload_field)
    if not neue:
        return []
    try:
        umgewandelt = normalize_uploads(neue)
    except ValidationError as fehler:
        return fehler.messages
    save_images(
        owner, umgewandelt, gruppe if kind is None else kind, start=len(order)
    )
    return []


# --- Dashboard -------------------------------------------------------------

class HomeView(StaffMixin, TemplateView):
    template_name = "tasty/account/warenwirtschaft_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["anzahl_verfuegbar"] = StockItem.objects.filter(
            status=StockItem.Status.VERFUEGBAR
        ).count()
        ctx["anzahl_gesamt"] = StockItem.objects.count()
        ctx["anzahl_veroeffentlicht"] = StockItem.objects.filter(
            product__isnull=False
        ).count()
        ctx["anzahl_projekte"] = Project.objects.filter(
            status=Project.Status.OFFEN
        ).count()
        ctx["anzahl_bestellware"] = CatalogItem.objects.filter(is_active=True).count()
        ctx["anzahl_bestellware_online"] = CatalogItem.objects.filter(
            is_active=True, product__isnull=False
        ).count()
        ctx["anzahl_verkaeufe"] = Order.objects.count()
        ctx["anzahl_lieferanten"] = Supplier.objects.count()
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
            "product", "supplier", "reserved_for"
        ).prefetch_related("images", "projects")

        suche = self.request.GET.get("q", "").strip()
        if suche:
            qs = qs.filter(
                Q(inventory_no__icontains=suche)
                | Q(product_name__icontains=suche)
                | Q(supplier_article_no__icontains=suche)
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

        # Online = mit einem Shop-Produkt verknuepft
        shop = self.request.GET.get("shop", "")
        if shop == "ja":
            qs = qs.filter(product__isnull=False)
        elif shop == "nein":
            qs = qs.filter(product__isnull=True)

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

    # Feld am Bestellartikel -> Feld im Wareneingang. Der Listenpreis wird
    # bewusst nicht uebernommen: beim Wareneingang zaehlt der tatsaechlich
    # bezahlte Preis, und der steht auf der Rechnung.
    KATALOG_FELDER = (
        "supplier", "supplier_article_no", "product_name", "shop_category",
        "color", "length", "size", "structure", "density", "cap_type",
        "sale_price", "description",
    )

    def get_initial(self):
        initial = super().get_initial()
        supplier_id = self.request.GET.get("supplier")
        if supplier_id:
            initial["supplier"] = supplier_id

        artikel = self.katalog_artikel()
        if artikel:
            for name in self.KATALOG_FELDER:
                initial[name] = getattr(artikel, name)
        return initial

    def katalog_artikel(self):
        """Bestellartikel aus ?katalog=<pk>, falls die Ware daher kommt."""
        pk = self.request.GET.get("katalog")
        if not pk or not pk.isdigit():
            return None
        return CatalogItem.objects.filter(pk=int(pk)).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["katalog_artikel"] = self.katalog_artikel()
        return ctx

    def form_valid(self, form):
        bilder = self.request.FILES.getlist("eingang_images")
        if not bilder:
            form.add_error(
                None, "Bitte mindestens ein Foto der Ware hochladen."
            )
            return self.form_invalid(form)

        # Vor der Transaktion umwandeln: unlesbare Dateien sollen als
        # Formularfehler erscheinen, nicht als Serverfehler mitten im Anlegen.
        try:
            bilder = normalize_uploads(bilder)
        except ValidationError as fehler:
            for meldung in fehler.messages:
                form.add_error(None, meldung)
            return self.form_invalid(form)

        data = form.cleaned_data
        supplier = data["supplier"]
        menge = data["quantity"]
        # Bestandsart folgt der Kategorie: Haarware ergibt je Stueck einen
        # Datensatz, Zubehoer und Pflege einen mit der Anzahl.
        einzeln = (
            StockItem.mode_for_category(data["shop_category"])
            == StockItem.StockMode.EINZELSTUECK
        )
        counters = reserve_numbers(supplier, menge if einzeln else 1)

        def nummer(counter):
            return build_inventory_no(
                supplier, data["color"], data["length"], counter,
                data["product_name"],
            )

        # Gilt fuer alle Stuecke dieses Wareneingangs - auch die
        # Lieferanten-Artikelnummer, die je Artikel und nicht je Stueck gilt.
        felder = (
            "product_name", "supplier_article_no", "invoice_no", "purchase_price",
            "color", "length", "size", "structure", "density", "cap_type",
            "received_at", "shop_category", "sale_price", "description", "notes",
        )
        gemeinsam = {name: data[name] for name in felder}

        with transaction.atomic():
            for counter in counters:
                stueck = StockItem.objects.create(
                    inventory_no=nummer(counter),
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

        erste = nummer(counters[0])
        if einzeln and len(counters) > 1:
            letzte = nummer(counters[-1])
            messages.success(
                self.request, f"{len(counters)} Stück erfasst ({erste} bis {letzte})."
            )
        else:
            messages.success(
                self.request,
                f"Erfasst: {erste}" + ("" if einzeln else f" ({menge} Stück)"),
            )
        artikel = self.katalog_artikel()
        if artikel:
            offen = artikel.projects.filter(status=Project.Status.OFFEN)
            if offen.exists():
                titel = ", ".join(p.title for p in offen)
                messages.info(
                    self.request,
                    f"Auf „{artikel.product_name}“ warten noch offene Projekte "
                    f"({titel}). Dort jetzt das neue Bestandsstück zuordnen.",
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
        # Was der Wareneingang schon weiss, vorbelegen. Die Zielgruppe bewusst
        # nicht - sie soll hier bewusst entschieden werden.
        return {
            "product": self.stueck.product_id,
            "name": self.stueck.product_name,
            "label": self.stueck.product_name[:60],
            "category": (
                self.stueck.shop_category or Product.Category.ECHTHAAR_PERUECKE
            ),
            "price": self.stueck.sale_price,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stueck"] = self.stueck
        ctx["bilder"] = self.stueck.shop_images
        ctx["blocker"] = self.stueck.publish_blockers()
        return ctx

    def form_valid(self, form):
        daten = form.cleaned_data
        produkt = daten.get("product")

        # Kein halbfertiger Datensatz im Shop: erst muessen Name, Preis,
        # Beschreibung, Foto und die Eigenschaften stehen.
        blocker = self.stueck.publish_blockers()
        if blocker:
            form.add_error(
                None,
                "Vor dem Onlinestellen fehlt noch: " + ", ".join(blocker) + ".",
            )
            return self.form_invalid(form)

        with transaction.atomic():
            self.stueck.audience = daten["audience"]
            if produkt is None:
                produkt = Product(
                    name=daten["name"],
                    label=daten["label"],
                    category=daten["category"],
                    price=daten["price"],
                    stock_mode=self.stueck.stock_mode,
                )
                produkt.ensure_slug()
            produkt.track_stock = True
            produkt.save()
            self.stueck.product = produkt
            self.stueck.save(update_fields=["product", "audience", "updated_at"])
            # Eigenschaften, Zielgruppe und Galerie aus dem Bestand nachziehen
            self.stueck.sync_to_product()
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
                f"{settings.INVOICE_RECIPIENT_EMAIL}."
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
        ctx["eingang_bilder"] = self.object.images.filter(
            kind=StockItemImage.Kind.EINGANG
        )
        ctx["shop_bilder"] = self.object.images.filter(kind=StockItemImage.Kind.SHOP)
        ctx["projekte"] = self.object.projects.all()
        ctx["blocker"] = self.object.publish_blockers()
        return ctx

    def form_valid(self, form):
        # Statuswechsel automatisch in die Historie schreiben (wer/wann)
        old = StockItem.objects.get(pk=form.instance.pk)
        old_status_display = old.get_status_display()
        old_status = old.status
        response = super().form_valid(form)
        obj = form.instance

        bildfehler = apply_image_changes(
            self.request, obj, StockItemImage.Kind.EINGANG, "eingang_images"
        )
        bildfehler += apply_image_changes(
            self.request, obj, StockItemImage.Kind.SHOP, "shop_images"
        )
        for meldung in bildfehler:
            messages.warning(self.request, meldung)

        if old_status != obj.status:
            obj.log_event(
                StockItemEvent.Kind.STATUS, old_status_display,
                obj.get_status_display(), by=self.request.user,
            )
            self._handle_sale(obj)
        if obj.product_id:
            # Geaenderte Angaben und Bilder sofort in den Shop durchreichen
            obj.sync_to_product()

        messages.success(
            self.request, f"Bestandsstück „{obj.inventory_no}“ gespeichert."
        )
        return response


class StockItemDeleteView(StaffMixin, DeleteView):
    """Bestandsstueck endgueltig entfernen - nach Rueckfrage.

    Verkaufte Ware wird geschuetzt: an ihr haengen Bestellpositionen
    (on_delete=PROTECT), und die Rechnungshistorie soll nicht zerreissen.
    Dafuer gibt es das Ausmustern.
    """

    model = StockItem
    template_name = "tasty/account/stockitem_confirm_delete.html"
    success_url = reverse_lazy("inventory_manage:stock_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["verkauft"] = self._verkauft(self.object)
        ctx["anzahl_bilder"] = self.object.images.count()
        ctx["anzahl_projekte"] = self.object.projects.count()
        return ctx

    @staticmethod
    def _verkauft(stueck):
        return OrderItem.objects.filter(stock_item=stueck).exists()

    def form_valid(self, form):
        stueck = self.object
        if self._verkauft(stueck):
            messages.error(
                self.request,
                f"„{stueck.inventory_no}“ wurde verkauft und kann nicht gelöscht "
                "werden – daran hängt die Rechnungshistorie. Stattdessen ausmustern.",
            )
            return redirect("inventory_manage:stock_edit", pk=stueck.pk)

        nummer = stueck.inventory_no
        # Dateien mit entfernen: Djangos delete() raeumt den Medienordner nicht auf.
        # Verkaufsbilder eines online gestellten Stuecks liegen aber unter
        # demselben Pfad im Shop (sync_to_product kopiert nicht) - die muessen
        # liegen bleiben, sonst verliert das Produkt seine Bilder. Beide Seiten
        # pruefen: das erste Bild ist Product.image, der Rest ProductImage.
        for bild in stueck.images.all():
            name = bild.image.name
            if ProductImage.objects.filter(image=name).exists():
                continue
            if Product.objects.filter(image=name).exists():
                continue
            bild.image.delete(save=False)
        response = super().form_valid(form)
        messages.success(self.request, f"Bestandsstück „{nummer}“ wurde gelöscht.")
        return response


class StockItemRetireView(StaffMixin, View):
    """Ausmustern statt loeschen (POST-only) - der Weg fuer verkaufte Ware."""

    def post(self, request, pk):
        stueck = get_object_or_404(StockItem, pk=pk)
        alt = stueck.get_status_display()
        stueck.status = StockItem.Status.AUSGEMUSTERT
        stueck.save(update_fields=["status", "updated_at"])
        stueck.log_event(
            StockItemEvent.Kind.STATUS, alt, stueck.get_status_display(),
            by=request.user, note="Ausgemustert",
        )
        messages.success(request, f"„{stueck.inventory_no}“ ist ausgemustert.")
        return redirect("inventory_manage:stock_list")


class StockItemUnpublishView(StaffMixin, View):
    """Verknuepfung zum Shop-Produkt loesen (POST-only). Das Produkt selbst
    bleibt bestehen - es kann weitere Bestandsstuecke haben.
    """

    def post(self, request, pk):
        stueck = get_object_or_404(StockItem, pk=pk)
        if stueck.product_id:
            name = stueck.product.name
            stueck.product = None
            stueck.save(update_fields=["product", "updated_at"])
            stueck.log_event(
                StockItemEvent.Kind.STATUS, "", stueck.get_status_display(),
                by=request.user, note=f"Aus dem Shop genommen (war „{name}“)",
            )
            messages.success(request, "Aus dem Shop genommen.")
        return redirect("inventory_manage:stock_edit", pk=pk)


# --- Bestellware -----------------------------------------------------------

class CatalogItemListView(StaffMixin, ListView):
    model = CatalogItem
    template_name = "tasty/account/catalogitem_list.html"
    context_object_name = "artikel"

    def get_queryset(self):
        qs = CatalogItem.objects.select_related(
            "supplier", "product"
        ).prefetch_related("images", "projects")

        suche = self.request.GET.get("q", "").strip()
        if suche:
            qs = qs.filter(
                Q(product_name__icontains=suche)
                | Q(supplier_article_no__icontains=suche)
                | Q(supplier__name__icontains=suche)
                | Q(color__icontains=suche)
            )

        kategorie = self.request.GET.get("kategorie", "")
        if kategorie in dict(StockItem.SHOP_CATEGORIES):
            qs = qs.filter(shop_category=kategorie)

        hersteller = self.request.GET.get("hersteller", "")
        if hersteller.isdigit():
            qs = qs.filter(supplier_id=int(hersteller))

        lieferbar = self.request.GET.get("lieferbar", "")
        if lieferbar in CatalogItem.Availability.values:
            qs = qs.filter(availability=lieferbar)

        shop = self.request.GET.get("shop", "")
        if shop == "ja":
            qs = qs.filter(product__isnull=False)
        elif shop == "nein":
            qs = qs.filter(product__isnull=True)

        return qs.order_by("product_name", "id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = {
            "q": self.request.GET.get("q", ""),
            "kategorie": self.request.GET.get("kategorie", ""),
            "hersteller": self.request.GET.get("hersteller", ""),
            "lieferbar": self.request.GET.get("lieferbar", ""),
            "shop": self.request.GET.get("shop", ""),
        }
        ctx["kategorien"] = StockItem.SHOP_CATEGORIES
        ctx["lieferbarkeiten"] = CatalogItem.Availability.choices
        ctx["lieferanten"] = Supplier.objects.all()
        ctx["anzahl_gesamt"] = CatalogItem.objects.count()
        return ctx


class CatalogItemMixin:
    model = CatalogItem
    form_class = CatalogItemForm
    template_name = "tasty/account/catalogitem_form.html"
    success_url = reverse_lazy("inventory_manage:catalog_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object:
            ctx["shop_bilder"] = self.object.images.all()
            ctx["projekte"] = self.object.projects.all()
            ctx["blocker"] = self.object.publish_blockers()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        artikel = form.instance
        # kind leer: Bestellartikel kennen nur Verkaufsbilder.
        for meldung in apply_image_changes(
            self.request, artikel, "shop", "shop_images", kind=""
        ):
            messages.warning(self.request, meldung)
        if artikel.product_id:
            artikel.sync_to_product()
        messages.success(
            self.request, f"Bestellartikel „{artikel.product_name}“ gespeichert."
        )
        return response


class CatalogItemCreateView(CatalogItemMixin, StaffMixin, CreateView):
    def get_initial(self):
        initial = super().get_initial()
        supplier_id = self.request.GET.get("supplier")
        if supplier_id:
            initial["supplier"] = supplier_id
        return initial


class CatalogItemUpdateView(CatalogItemMixin, StaffMixin, UpdateView):
    pass


class CatalogItemPublishView(StaffMixin, FormView):
    """Bestellartikel einem Shop-Produkt zuordnen.

    Fast identisch zum Bestand, mit einem Unterschied: track_stock bleibt aus.
    Bestellware ist nie ausverkauft, sie hat eine Lieferzeit.
    """

    form_class = StockItemPublishForm
    template_name = "tasty/account/catalogitem_publish.html"
    success_url = reverse_lazy("inventory_manage:catalog_list")

    def dispatch(self, request, *args, **kwargs):
        self.artikel = get_object_or_404(CatalogItem, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            "product": self.artikel.product_id,
            "name": self.artikel.product_name,
            "label": self.artikel.product_name[:60],
            "category": (
                self.artikel.shop_category or Product.Category.KUNSTHAAR_PERUECKE
            ),
            "price": self.artikel.sale_price,
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["artikel"] = self.artikel
        ctx["bilder"] = self.artikel.shop_images
        ctx["blocker"] = self.artikel.publish_blockers()
        return ctx

    def form_valid(self, form):
        daten = form.cleaned_data
        produkt = daten.get("product")

        blocker = self.artikel.publish_blockers()
        if blocker:
            form.add_error(
                None,
                "Vor dem Onlinestellen fehlt noch: " + ", ".join(blocker) + ".",
            )
            return self.form_invalid(form)

        with transaction.atomic():
            self.artikel.audience = daten["audience"]
            if produkt is None:
                produkt = Product(
                    name=daten["name"],
                    label=daten["label"],
                    category=daten["category"],
                    price=daten["price"],
                )
                produkt.ensure_slug()
            # Bestellware richtet sich nicht nach dem Lager - sonst waere sie
            # sofort ausverkauft, weil es kein Bestandsstueck gibt.
            produkt.track_stock = False
            produkt.save()
            self.artikel.product = produkt
            self.artikel.save(update_fields=["product", "audience", "updated_at"])
            self.artikel.sync_to_product()

        messages.success(
            self.request,
            f"„{self.artikel.product_name}“ ist jetzt als Bestellware im Shop "
            f"(„{produkt.name}“).",
        )
        return HttpResponseRedirect(str(self.success_url))


class CatalogItemUnpublishView(StaffMixin, View):
    """Verknuepfung zum Shop-Produkt loesen (POST-only)."""

    def post(self, request, pk):
        artikel = get_object_or_404(CatalogItem, pk=pk)
        if artikel.product_id:
            artikel.product = None
            artikel.save(update_fields=["product", "updated_at"])
            messages.success(request, "Aus dem Shop genommen.")
        return redirect("inventory_manage:catalog_edit", pk=pk)


class CatalogItemDeleteView(StaffMixin, DeleteView):
    """Bestellartikel entfernen - nach Rueckfrage.

    Anders als beim Bestand haengt hier keine Rechnungshistorie dran; nur die
    Bilddateien muessen mit weg, wenn sie nicht im Shop weiterverwendet werden.
    """

    model = CatalogItem
    template_name = "tasty/account/catalogitem_confirm_delete.html"
    success_url = reverse_lazy("inventory_manage:catalog_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["anzahl_bilder"] = self.object.images.count()
        ctx["anzahl_projekte"] = self.object.projects.count()
        return ctx

    def form_valid(self, form):
        artikel = self.object
        name = artikel.product_name
        # Wie beim Bestand: Dateien, die im Shop weiterleben, bleiben liegen.
        for bild in artikel.images.all():
            dateiname = bild.image.name
            if ProductImage.objects.filter(image=dateiname).exists():
                continue
            if Product.objects.filter(image=dateiname).exists():
                continue
            bild.image.delete(save=False)
        response = super().form_valid(form)
        messages.success(self.request, f"Bestellartikel „{name}“ wurde gelöscht.")
        return response


# --- Projekte --------------------------------------------------------------

class ProjectListView(StaffMixin, ListView):
    """Die Arbeitsliste - abgeschlossene Projekte stehen im Archiv."""

    model = Project
    template_name = "tasty/account/project_list.html"
    context_object_name = "projekte"

    def get_queryset(self):
        return (
            Project.objects.select_related("stock_item", "customer")
            .exclude(status__in=Project.ARCHIV_STATUS)
            .order_by("due_date", "-created_at")
        )


class ProjectArchiveView(StaffMixin, ListView):
    """Erledigte und stornierte Projekte. Von hier aus wieder zu oeffnen."""

    model = Project
    template_name = "tasty/account/project_archive.html"
    context_object_name = "projekte"

    def get_queryset(self):
        return (
            Project.objects.select_related("stock_item", "customer")
            .filter(status__in=Project.ARCHIV_STATUS)
            .order_by("-updated_at")
        )


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


# Schluessel des Formular-Zwischenspeichers waehrend der Bestandsauswahl.
# Die Auswahl laeuft ueber eine eigene Seite, deshalb muessen die bereits
# eingegebenen Werte zwischengeparkt werden - sonst waeren sie nach der
# Rueckkehr weg.
PROJEKT_ENTWURF = "projekt_entwurf"


class ProjectCreateView(ProjectMixin, StaffMixin, CreateView):
    def get_initial(self):
        initial = super().get_initial()
        # Aus dem Zwischenspeicher zurueck (nach der Bestandsauswahl)
        entwurf = self.request.session.pop(PROJEKT_ENTWURF, None)
        if entwurf:
            initial.update(entwurf)
        stueck_id = self.request.GET.get("bestand")
        if stueck_id and stueck_id.isdigit():
            initial["stock_item"] = stueck_id
        artikel_id = self.request.GET.get("bestellware")
        if artikel_id and artikel_id.isdigit():
            initial["catalog_item"] = artikel_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(ProjectMixin, StaffMixin, UpdateView):
    model = Project


class ProjectPickStockView(StaffMixin, ListView):
    """Ware fuer ein Projekt aussuchen - mit Bildern statt Auswahlliste.

    Zwei Quellen: der eigene Bestand und die Bestellware. Beides sind
    Kacheln derselben Seite, umgeschaltet ueber ?quelle=.

    Wird per POST aus dem Projektformular aufgerufen; die bereits eingegebenen
    Werte wandern in die Session und kommen nach der Auswahl zurueck.
    """

    template_name = "tasty/account/project_pick_stock.html"
    context_object_name = "stuecke"

    # Nur diese Felder werden zwischengeparkt - Dateien und CSRF nicht.
    ENTWURF_FELDER = (
        "title", "customer", "customer_name", "status", "due_date",
        "target_color", "target_length", "target_structure",
        "target_cap_type", "target_density", "notes",
    )

    def post(self, request, *args, **kwargs):
        request.session[PROJEKT_ENTWURF] = {
            name: request.POST.get(name, "")
            for name in self.ENTWURF_FELDER
            if request.POST.get(name)
        }
        return redirect(request.get_full_path())

    @property
    def quelle(self):
        return (
            "bestellware"
            if self.request.GET.get("quelle") == "bestellware"
            else "bestand"
        )

    def get_queryset(self):
        suche = self.request.GET.get("q", "").strip()
        if self.quelle == "bestellware":
            qs = (
                CatalogItem.objects
                .filter(
                    shop_category__in=StockItem.PROJEKTFAEHIGE_KATEGORIEN,
                    is_active=True,
                )
                .select_related("supplier")
                .prefetch_related("images", "projects")
            )
            if suche:
                qs = qs.filter(
                    Q(product_name__icontains=suche)
                    | Q(supplier_article_no__icontains=suche)
                    | Q(color__icontains=suche)
                    | Q(supplier__name__icontains=suche)
                )
            return qs.order_by("product_name", "id")

        qs = (
            StockItem.objects
            .filter(shop_category__in=StockItem.PROJEKTFAEHIGE_KATEGORIEN)
            .exclude(status__in=(
                StockItem.Status.AUSGEMUSTERT, StockItem.Status.VERKAUFT,
            ))
            .select_related("supplier")
            .prefetch_related("images", "projects")
        )
        if suche:
            qs = qs.filter(
                Q(inventory_no__icontains=suche)
                | Q(product_name__icontains=suche)
                | Q(color__icontains=suche)
                | Q(length__icontains=suche)
                | Q(supplier__name__icontains=suche)
            )
        return qs.order_by("-created_at", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["suche"] = self.request.GET.get("q", "")
        # Zurueck ins Formular: bei bestehenden Projekten zur Bearbeitung
        ctx["projekt_pk"] = self.request.GET.get("projekt", "")
        ctx["quelle"] = self.quelle
        # Name des GET-Parameters, mit dem das Formular die Auswahl entgegennimmt
        ctx["auswahl_feld"] = (
            "bestellware" if self.quelle == "bestellware" else "bestand"
        )
        return ctx


class CustomerSearchView(StaffMixin, View):
    """Kundensuche als JSON fuer das Suchfeld im Projektformular."""

    LIMIT = 20

    def get(self, request):
        suche = request.GET.get("q", "").strip()
        if len(suche) < 2:
            return JsonResponse({"treffer": []})
        kunden = User.objects.filter(
            Q(first_name__icontains=suche)
            | Q(last_name__icontains=suche)
            | Q(email__icontains=suche)
            | Q(company_name__icontains=suche),
            role__in=(User.Role.B2C, User.Role.B2B),
        ).order_by("last_name", "email")[: self.LIMIT]
        return JsonResponse({
            "treffer": [
                {
                    "id": k.pk,
                    "name": (f"{k.first_name} {k.last_name}".strip()
                             or k.company_name or k.email),
                    "detail": k.email,
                    "b2b": k.role == User.Role.B2B,
                }
                for k in kunden
            ]
        })


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


class ProjectDoneView(StaffMixin, View):
    """Projekt als erledigt markieren (POST-only). Das ist der einzige
    Arbeitsstand, den es noch gibt - Fertigungsphasen sind entfallen.
    """

    def post(self, request, pk):
        projekt = get_object_or_404(Project, pk=pk)
        if projekt.status == Project.Status.ERLEDIGT:
            messages.info(request, "Das Projekt ist bereits erledigt.")
        else:
            projekt.status = Project.Status.ERLEDIGT
            projekt.save(update_fields=["status", "updated_at"])
            if projekt.stock_item:
                projekt.stock_item.log_event(
                    StockItemEvent.Kind.PROJEKT, "Offen", "Erledigt",
                    by=request.user, note=f"Projekt „{projekt.title}“",
                )
            messages.success(
                request,
                f"Projekt „{projekt.title}“ ist erledigt und liegt jetzt im Archiv.",
            )
        return redirect("inventory_manage:project_list")


class ProjectReopenView(StaffMixin, View):
    """Archiviertes Projekt zurueck in die Arbeitsliste holen (POST-only)."""

    def post(self, request, pk):
        projekt = get_object_or_404(Project, pk=pk)
        if projekt.status == Project.Status.OFFEN:
            messages.info(request, "Das Projekt ist bereits offen.")
        else:
            alt = projekt.get_status_display()
            projekt.status = Project.Status.OFFEN
            projekt.save(update_fields=["status", "updated_at"])
            if projekt.stock_item:
                projekt.stock_item.log_event(
                    StockItemEvent.Kind.PROJEKT, alt, "Offen",
                    by=request.user, note=f"Projekt „{projekt.title}“",
                )
            messages.success(
                request, f"Projekt „{projekt.title}“ ist wieder offen."
            )
        return redirect("inventory_manage:project_list")
