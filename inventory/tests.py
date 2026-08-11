import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from shop.models import Cart, CartItem, Product

from .models import Order, StockItem, StockItemEvent, Supplier
from .numbering import build_inventory_no, reserve_numbers

User = get_user_model()


def make_supplier(code="EW", name="EllenWille"):
    return Supplier.objects.create(code=code, name=name)


def make_product(slug, **overrides):
    daten = {
        "name": f"Produkt {slug}",
        "label": slug,
        "slug": slug,
        "category": Product.Category.BESTAND,
        "price": 890,
    }
    daten.update(overrides)
    return Product.objects.create(**daten)


def make_stock_item(supplier, product=None, **overrides):
    daten = {
        "inventory_no": f"EW-BLO-50-{StockItem.objects.count() + 1:04d}",
        "supplier": supplier,
        "product": product,
        "product_name": "Bob Klassik",
        "invoice_no": "RE-1",
        "purchase_price": 300,
        "color": "Blond",
        "length": "50 cm",
        "size": "54 cm",
    }
    daten.update(overrides)
    return StockItem.objects.create(**daten)


class NumberingTest(TestCase):
    def test_format(self):
        lieferant = make_supplier()
        self.assertEqual(
            build_inventory_no(lieferant, "Blond", "50 cm", 1), "EW-BLO-50-0001"
        )

    def test_umlaute_werden_umgeschrieben(self):
        lieferant = make_supplier()
        self.assertEqual(build_inventory_no(lieferant, "Öl", "40", 5), "EW-OEL-40-0005")

    def test_kurze_farbe_wird_aufgefuellt(self):
        lieferant = make_supplier()
        self.assertEqual(build_inventory_no(lieferant, "1B", "30", 2), "EW-BXX-30-0002")

    def test_fehlende_laenge(self):
        lieferant = make_supplier()
        self.assertEqual(
            build_inventory_no(lieferant, "Blond", "ohne Angabe", 3),
            "EW-BLO-XX-0003",
        )

    def test_zaehler_je_hersteller(self):
        ew = make_supplier()
        ch = make_supplier(code="CH", name="China")
        self.assertEqual(reserve_numbers(ew, 3), [1, 2, 3])
        self.assertEqual(reserve_numbers(ew, 1), [4])
        # Anderer Hersteller beginnt bei 1
        self.assertEqual(reserve_numbers(ch, 2), [1, 2])


class StaffViewMixin:
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="pass12345", role=User.Role.ADMIN
        )
        self.kunde = User.objects.create_user(
            email="kunde@example.com", password="pass12345"
        )
        self.lieferant = make_supplier()
        self.client.force_login(self.admin)


class GoodsReceiptViewTest(StaffViewMixin, TestCase):
    def _daten(self, **overrides):
        daten = {
            "supplier": self.lieferant.pk,
            "product_name": "Bob Klassik",
            "invoice_no": "RE-2026-001",
            "purchase_price": "320",
            "vat_rate": "19.00",
            "color": "Blond",
            "length": "50 cm",
            "size": "54 cm",
            "quantity": "3",
            "received_at": "2026-08-04",
        }
        daten.update(overrides)
        return daten

    def test_stueckzahl_legt_mehrere_datensaetze_an(self):
        response = self.client.post(
            reverse("inventory_manage:stock_create"), self._daten()
        )
        self.assertEqual(response.status_code, 302)
        nummern = list(
            StockItem.objects.order_by("id").values_list("inventory_no", flat=True)
        )
        self.assertEqual(
            nummern, ["EW-BLO-50-0001", "EW-BLO-50-0002", "EW-BLO-50-0003"]
        )

    def test_jedes_stueck_bekommt_einen_historieneintrag(self):
        self.client.post(reverse("inventory_manage:stock_create"), self._daten())
        for stueck in StockItem.objects.all():
            eintraege = stueck.events.all()
            self.assertEqual(len(eintraege), 1)
            self.assertEqual(eintraege[0].kind, StockItemEvent.Kind.EINGANG)
            self.assertEqual(eintraege[0].changed_by, self.admin)

    def test_pflichtfelder(self):
        response = self.client.post(reverse("inventory_manage:stock_create"), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].errors), 10)
        self.assertEqual(StockItem.objects.count(), 0)

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        response = self.client.get(reverse("inventory_manage:stock_create"))
        self.assertEqual(response.status_code, 403)


class AvailabilityTest(TestCase):
    def setUp(self):
        self.lieferant = make_supplier()

    def test_ohne_track_stock_verhaelt_es_sich_wie_bisher(self):
        """Regressionsschutz fuer den Live-Shop: Produkte ohne Bestandsfuehrung
        bleiben bestellbar, egal was im Lager liegt.
        """
        produkt = make_product("ohne-bestand")
        self.assertFalse(produkt.is_sold_out)
        self.assertTrue(produkt.is_orderable)

    def test_zwei_stuecke_eines_verkauft(self):
        produkt = make_product("mit-bestand", track_stock=True)
        erstes = make_stock_item(self.lieferant, produkt)
        make_stock_item(self.lieferant, produkt)
        self.assertEqual(produkt.available_count, 2)

        erstes.status = StockItem.Status.VERKAUFT
        erstes.save()
        self.assertEqual(produkt.available_count, 1)
        self.assertFalse(produkt.is_sold_out)

    def test_alle_verkauft_ist_ausverkauft(self):
        produkt = make_product("ausverkauft", track_stock=True)
        stueck = make_stock_item(self.lieferant, produkt)
        stueck.status = StockItem.Status.VERKAUFT
        stueck.save()
        self.assertTrue(produkt.is_sold_out)
        self.assertFalse(produkt.is_orderable)

    def test_konfigurierbares_produkt_bleibt_unberuehrt(self):
        produkt = make_product("konfig", category=Product.Category.KONFIG)
        self.assertFalse(produkt.is_orderable)
        self.assertFalse(produkt.is_sold_out)


class CartStockGuardTest(TestCase):
    def setUp(self):
        self.lieferant = make_supplier()
        self.kunde = User.objects.create_user(
            email="kunde@example.com", password="pass12345"
        )
        self.client.force_login(self.kunde)

    def _post(self, name, payload):
        return self.client.post(
            reverse(name), json.dumps(payload), content_type="application/json"
        )

    def test_ausverkauftes_produkt_kann_nicht_gelegt_werden(self):
        produkt = make_product("verkauft", track_stock=True)
        stueck = make_stock_item(self.lieferant, produkt)
        stueck.status = StockItem.Status.VERKAUFT
        stueck.save()

        response = self._post("shop:api_add", {"product_id": produkt.pk})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "sold_out")
        self.assertEqual(CartItem.objects.count(), 0)

    def test_entfernen_bleibt_erlaubt(self):
        """Wird ein Stueck verkauft, waehrend es im Warenkorb liegt, muss es
        sich weiterhin entfernen lassen.
        """
        produkt = make_product("spaeter-verkauft", track_stock=True)
        stueck = make_stock_item(self.lieferant, produkt)
        self._post("shop:api_add", {"product_id": produkt.pk})
        self.assertEqual(CartItem.objects.count(), 1)

        stueck.status = StockItem.Status.VERKAUFT
        stueck.save()
        response = self._post(
            "shop:api_update", {"product_id": produkt.pk, "quantity": 0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_mengenartikel_wird_gedeckelt(self):
        produkt = make_product(
            "shampoo", track_stock=True,
            stock_mode=Product.StockMode.MENGE, stock_quantity=2,
        )
        self._post("shop:api_add", {"product_id": produkt.pk, "quantity": 5})
        self.assertEqual(CartItem.objects.get().quantity, 2)


class SellViewTest(StaffViewMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.produkt = make_product("zu-verkaufen", track_stock=True)
        self.stueck = make_stock_item(self.lieferant, self.produkt)

    def _url(self):
        return reverse("inventory_manage:stock_sell", args=[self.stueck.pk])

    def _daten(self, **overrides):
        daten = {
            "user": "",
            "customer_name": "Erika Musterfrau",
            "customer_street": "Hauptstr. 1",
            "customer_zip": "56766",
            "customer_city": "Ulmen",
            "customer_email": "erika@example.com",
            "price": "890",
            "sold_on": "2026-08-11",
            "channel": StockItem.Channel.STUDIO,
            "note": "Zahlung auf Rechnung",
        }
        daten.update(overrides)
        return daten

    def test_verkauf_bucht_bestand_und_bestellung(self):
        response = self.client.post(self._url(), self._daten())
        self.assertEqual(response.status_code, 302)

        self.stueck.refresh_from_db()
        self.assertEqual(self.stueck.status, StockItem.Status.VERKAUFT)
        self.assertIsNotNone(self.stueck.sold_at)

        bestellung = Order.objects.get()
        self.assertEqual(bestellung.customer_display, "Erika Musterfrau")
        position = bestellung.items.get()
        self.assertEqual(position.stock_item, self.stueck)
        self.assertEqual(position.description, self.produkt.name)

    def test_stueck_verschwindet_aus_dem_shop(self):
        self.client.post(self._url(), self._daten())
        self.produkt.refresh_from_db()
        self.assertTrue(self.produkt.is_sold_out)
        self.assertFalse(self.produkt.is_orderable)

    def test_rechnungsmail_geht_raus(self):
        self.client.post(self._url(), self._daten())
        self.assertEqual(len(mail.outbox), 1)
        nachricht = mail.outbox[0]
        self.assertIn("Erika Musterfrau", nachricht.body)
        self.assertIn(self.stueck.inventory_no, nachricht.body)
        self.assertIn("890", nachricht.body)
        self.assertIn("Zahlung auf Rechnung", nachricht.body)

        bestellung = Order.objects.get()
        self.assertEqual(bestellung.export_status, Order.ExportStatus.SENT)

    def test_kundenkonto_liefert_die_anschrift(self):
        self.kunde.first_name = "Erika"
        self.kunde.last_name = "Musterfrau"
        self.kunde.street = "Hauptstr. 1"
        self.kunde.zip_code = "56766"
        self.kunde.city = "Ulmen"
        self.kunde.save()

        self.client.post(
            self._url(), self._daten(user=self.kunde.pk, customer_name="")
        )
        bestellung = Order.objects.get()
        self.assertEqual(bestellung.customer_display, "Erika Musterfrau")
        self.assertIn("Hauptstr. 1", bestellung.billing_lines)

    def test_ohne_konto_ist_der_name_pflicht(self):
        response = self.client.post(self._url(), self._daten(customer_name=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("customer_name", response.context["form"].errors)
        self.stueck.refresh_from_db()
        self.assertEqual(self.stueck.status, StockItem.Status.VERFUEGBAR)

    def test_historie_haelt_den_verkauf_fest(self):
        self.client.post(self._url(), self._daten())
        eintrag = self.stueck.events.filter(kind=StockItemEvent.Kind.STATUS).get()
        self.assertEqual(eintrag.to_value, "Verkauft")
        self.assertEqual(eintrag.changed_by, self.admin)

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        self.assertEqual(self.client.get(self._url()).status_code, 403)


class PublishViewTest(StaffViewMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.stueck = make_stock_item(self.lieferant)

    def test_neues_produkt_uebernimmt_die_warendaten(self):
        response = self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            {
                "product": "",
                "name": "Bob Klassik Blond",
                "label": "Bob Klassik",
                "category": Product.Category.BESTAND,
                "price": "890",
            },
        )
        self.assertEqual(response.status_code, 302)
        produkt = Product.objects.get(name="Bob Klassik Blond")
        self.assertTrue(produkt.track_stock)
        self.assertEqual(produkt.hair_color, "Blond")
        self.assertEqual(produkt.hair_length, "50 cm")
        self.assertTrue(produkt.slug)

        self.stueck.refresh_from_db()
        self.assertEqual(self.stueck.product, produkt)

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        url = reverse("inventory_manage:stock_publish", args=[self.stueck.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
