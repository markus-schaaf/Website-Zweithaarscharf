import io
import json
import os

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from shop.models import CartItem, Product, ProductImage

from .models import (
    AttributeOption,
    Order,
    OrderItem,
    Project,
    StockItem,
    StockItemEvent,
    StockItemImage,
    Supplier,
)
from .numbering import build_inventory_no, reserve_numbers

User = get_user_model()


def make_supplier(code="EW", name="EllenWille"):
    return Supplier.objects.create(code=code, name=name)


def make_image(name="foto.jpg"):
    """Kleines echtes JPEG - ImageField prueft den Dateiinhalt."""
    puffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(puffer, format="JPEG")
    return SimpleUploadedFile(name, puffer.getvalue(), content_type="image/jpeg")


def make_heic(name="IMG_4711.heic"):
    """Echte HEIC-Datei - so kommen Fotos von der iPhone-Kamera an."""
    puffer = io.BytesIO()
    Image.new("RGB", (12, 8), "white").save(puffer, format="HEIF")
    return SimpleUploadedFile(name, puffer.getvalue(), content_type="image/heic")


def make_product(slug, **overrides):
    daten = {
        "name": f"Produkt {slug}",
        "label": slug,
        "slug": slug,
        "category": Product.Category.ECHTHAAR_PERUECKE,
        "price": 890,
    }
    daten.update(overrides)
    return Product.objects.create(**daten)


def make_stock_item(supplier, product=None, **overrides):
    """Vollstaendig gepflegte Peruecke - so, dass sie online gestellt werden
    darf. Tests, die einen Blocker brauchen, leeren gezielt ein Feld.
    """
    daten = {
        "inventory_no": f"EW-BLO-50-{StockItem.objects.count() + 1:04d}",
        "supplier": supplier,
        "product": product,
        "product_name": "Bob Klassik",
        "invoice_no": "RE-1",
        "purchase_price": 300,
        "shop_category": Product.Category.ECHTHAAR_PERUECKE,
        "sale_price": 890,
        "description": "Schulterlanges Modell, glatt.",
        "color": "Blond",
        "length": "50 cm",
        "size": "54 cm",
        "structure": "Glatt",
        "cap_type": "Tresse",
        "density": "Mittel",
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
    def setUp(self):
        super().setUp()
        # Die Erfassung arbeitet mit Auswahlwerten aus dem Katalog.
        for gruppe, wert in (
            (AttributeOption.Group.FARBE, "Blond"),
            (AttributeOption.Group.LAENGE, "50 cm"),
            (AttributeOption.Group.GROESSE, "54 cm"),
        ):
            AttributeOption.objects.create(group=gruppe, name=wert)

    def _daten(self, **overrides):
        daten = {
            "shop_category": Product.Category.ECHTHAAR_PERUECKE,
            "supplier": self.lieferant.pk,
            "product_name": "Bob Klassik",
            "invoice_no": "RE-2026-001",
            "purchase_price": "320",
            "color": "Blond",
            "length": "50 cm",
            "size": "54 cm",
            "quantity": "3",
            "received_at": "2026-08-04",
            "eingang_images": make_image(),
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

    def test_jedes_stueck_bekommt_das_eingangsbild(self):
        self.client.post(reverse("inventory_manage:stock_create"), self._daten())
        for stueck in StockItem.objects.all():
            bilder = stueck.images.all()
            self.assertEqual(len(bilder), 1)
            self.assertEqual(bilder[0].kind, StockItemImage.Kind.EINGANG)

    def test_iphone_foto_wird_umgewandelt(self):
        """HEIC ist das Standardformat der iPhone-Kamera. Unveraendert
        gespeichert waere es in keinem Browser sichtbar.
        """
        response = self.client.post(
            reverse("inventory_manage:stock_create"),
            self._daten(quantity="1", eingang_images=make_heic()),
        )
        self.assertEqual(response.status_code, 302)
        bild = StockItem.objects.get().images.get()
        self.assertTrue(bild.image.name.endswith(".jpg"))
        self.assertNotIn(".heic", bild.image.name.lower())

    def test_unlesbare_datei_wird_als_formularfehler_gemeldet(self):
        daten = self._daten(
            eingang_images=SimpleUploadedFile("notiz.txt", b"kein Bild")
        )
        response = self.client.post(reverse("inventory_manage:stock_create"), daten)
        self.assertEqual(response.status_code, 200)
        self.assertIn("notiz.txt", " ".join(response.context["form"].non_field_errors()))
        # Nichts angelegt - auch keine Produktnummern verbraucht
        self.assertEqual(StockItem.objects.count(), 0)

    def test_ohne_foto_wird_abgelehnt(self):
        daten = self._daten()
        daten.pop("eingang_images")
        response = self.client.post(reverse("inventory_manage:stock_create"), daten)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Foto", " ".join(response.context["form"].non_field_errors()))
        self.assertEqual(StockItem.objects.count(), 0)

    def test_pflege_ergibt_einen_datensatz_mit_menge(self):
        """Bestandsart wird nicht gefragt, sondern aus der Kategorie abgeleitet."""
        self.client.post(reverse("inventory_manage:stock_create"), self._daten(
            quantity="12", shop_category=Product.Category.PFLEGE,
        ))
        stueck = StockItem.objects.get()
        self.assertEqual(stueck.stock_mode, StockItem.StockMode.MENGE)
        self.assertEqual(stueck.quantity, 12)

    def test_peruecke_ergibt_einen_datensatz_je_stueck(self):
        self.client.post(reverse("inventory_manage:stock_create"), self._daten(
            quantity="3", shop_category=Product.Category.ECHTHAAR_PERUECKE,
        ))
        self.assertEqual(StockItem.objects.count(), 3)
        for stueck in StockItem.objects.all():
            self.assertEqual(stueck.stock_mode, StockItem.StockMode.EINZELSTUECK)
            self.assertEqual(stueck.quantity, 1)

    def test_artikelnummer_gilt_fuer_alle_stuecke(self):
        """Die Nummer des Lieferanten gehoert zum Artikel, nicht zum Stueck."""
        self.client.post(reverse("inventory_manage:stock_create"), self._daten(
            quantity="3", supplier_article_no="EW-4711",
        ))
        nummern = set(StockItem.objects.values_list("supplier_article_no", flat=True))
        self.assertEqual(StockItem.objects.count(), 3)
        self.assertEqual(nummern, {"EW-4711"})

    def test_artikelnummer_ist_optional(self):
        response = self.client.post(reverse("inventory_manage:stock_create"), self._daten(
            quantity="1",
        ))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StockItem.objects.get().supplier_article_no, "")

    def test_topper_ergibt_einen_datensatz_je_stueck(self):
        self.client.post(reverse("inventory_manage:stock_create"), self._daten(
            quantity="2", shop_category=Product.Category.KUNSTHAAR_TOPPER,
        ))
        self.assertEqual(StockItem.objects.count(), 2)
        for stueck in StockItem.objects.all():
            self.assertEqual(stueck.stock_mode, StockItem.StockMode.EINZELSTUECK)

    def test_zubehoer_braucht_keine_haarangaben(self):
        """Farbe, Laenge und Groesse gibt es an einem Perueckenstaender nicht."""
        daten = self._daten(
            quantity="5", shop_category=Product.Category.ZUBEHOER,
            product_name="Perückenständer Holz", color="", length="", size="",
        )
        response = self.client.post(reverse("inventory_manage:stock_create"), daten)
        self.assertEqual(response.status_code, 302)
        stueck = StockItem.objects.get()
        self.assertEqual(stueck.stock_mode, StockItem.StockMode.MENGE)
        self.assertEqual(stueck.quantity, 5)
        # Ohne Farbe und Laenge steht der Produktname in der Nummer.
        self.assertEqual(stueck.inventory_no, "EW-PER-0001")

    def test_haarware_braucht_farbe_laenge_groesse(self):
        response = self.client.post(
            reverse("inventory_manage:stock_create"),
            self._daten(shop_category=Product.Category.ECHTHAAR_TOPPER,
                        color="", length="", size=""),
        )
        self.assertEqual(response.status_code, 200)
        fehlend = set(response.context["form"].errors)
        self.assertEqual(fehlend, {"color", "length", "size"})

    def test_lieferdatum_ist_vorbelegt(self):
        """Leeres Datumsfeld sah auf dem iPhone wie ein Fehler aus."""
        response = self.client.get(reverse("inventory_manage:stock_create"))
        self.assertEqual(
            response.context["form"].fields["received_at"].initial,
            timezone.localdate(),
        )

    def test_pflichtfelder(self):
        response = self.client.post(reverse("inventory_manage:stock_create"), {})
        self.assertEqual(response.status_code, 200)
        fehlend = set(response.context["form"].errors)
        # Bestandsart und Zielgruppe werden hier bewusst nicht mehr gefragt
        self.assertNotIn("stock_mode", fehlend)
        self.assertNotIn("audience", fehlend)
        self.assertIn("shop_category", fehlend)
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
        StockItemImage.objects.create(
            stock_item=self.stueck, image=make_image("shop.jpg"),
            kind=StockItemImage.Kind.SHOP,
        )

    def _daten(self, **overrides):
        daten = {
            "product": "",
            "name": "Bob Klassik Blond",
            "label": "Bob Klassik",
            "category": Product.Category.ECHTHAAR_PERUECKE,
            "price": "890",
            "audience": StockItem.Audience.ALLE,
        }
        daten.update(overrides)
        return daten

    def test_zielgruppe_ist_pflicht(self):
        """Erst hier gefragt, dafuer verbindlich."""
        daten = self._daten()
        daten.pop("audience")
        response = self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]), daten
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("audience", response.context["form"].errors)
        self.stueck.refresh_from_db()
        self.assertIsNone(self.stueck.product)

    def test_zielgruppe_landet_am_stueck_und_am_produkt(self):
        self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            self._daten(audience=StockItem.Audience.B2B),
        )
        self.stueck.refresh_from_db()
        self.assertEqual(self.stueck.audience, StockItem.Audience.B2B)
        self.assertEqual(self.stueck.product.audience, StockItem.Audience.B2B)

    def test_unvollstaendiges_stueck_geht_nicht_online(self):
        self.stueck.sale_price = None
        self.stueck.description = ""
        self.stueck.save()
        response = self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            self._daten(),
        )
        self.assertEqual(response.status_code, 200)
        meldung = " ".join(response.context["form"].non_field_errors())
        self.assertIn("Verkaufspreis", meldung)
        self.assertIn("Beschreibung", meldung)
        self.stueck.refresh_from_db()
        self.assertIsNone(self.stueck.product)

    def test_neues_produkt_uebernimmt_die_warendaten(self):
        response = self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            self._daten(),
        )
        self.assertEqual(response.status_code, 302)
        produkt = Product.objects.get(name="Bob Klassik Blond")
        self.assertTrue(produkt.track_stock)
        self.assertEqual(produkt.hair_color, "Blond")
        self.assertEqual(produkt.hair_length, "50 cm")
        self.assertTrue(produkt.slug)

        self.stueck.refresh_from_db()
        self.assertEqual(self.stueck.product, produkt)

    def test_galerie_kommt_aus_dem_bestand(self):
        """Bei einem einzigen Verkaufsbild bleibt die Galerie leer - das Bild
        ist das Hauptbild und wuerde sonst doppelt erscheinen.
        """
        self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            self._daten(),
        )
        produkt = Product.objects.get(name="Bob Klassik Blond")
        bestandsbild = self.stueck.images.get()
        self.assertEqual(produkt.image.name, bestandsbild.image.name)
        self.assertEqual(list(produkt.images.all()), [])

    def test_ohne_foto_kein_onlinestellen(self):
        self.stueck.images.all().delete()
        response = self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            self._daten(),
        )
        self.assertEqual(response.status_code, 200)
        self.stueck.refresh_from_db()
        self.assertIsNone(self.stueck.product)

    def test_zurueckziehen_loest_die_verknuepfung(self):
        self.client.post(
            reverse("inventory_manage:stock_publish", args=[self.stueck.pk]),
            self._daten(),
        )
        self.client.post(
            reverse("inventory_manage:stock_unpublish", args=[self.stueck.pk])
        )
        self.stueck.refresh_from_db()
        self.assertIsNone(self.stueck.product)
        # Das Produkt bleibt bestehen - es haengt Bestellhistorie daran
        self.assertTrue(Product.objects.filter(name="Bob Klassik Blond").exists())

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        url = reverse("inventory_manage:stock_publish", args=[self.stueck.pk])
        self.assertEqual(self.client.get(url).status_code, 403)


class ProjectViewTest(StaffViewMixin, TestCase):
    def _daten(self, **overrides):
        daten = {
            "title": "Umbau Frau M.",
            "stock_item": "",
            "customer": "",
            "customer_name": "Frau M.",
            "status": Project.Status.OFFEN,
            "due_date": "",
            "target_color": "Grau meliert",
            "target_length": "",
            "target_structure": "",
            "target_cap_type": "",
            "target_density": "",
            "notes": "Kundin moechte kuerzer.",
        }
        daten.update(overrides)
        return daten

    def setUp(self):
        super().setUp()
        AttributeOption.objects.create(
            group=AttributeOption.Group.FARBE, name="Grau meliert"
        )

    def test_projekt_ohne_bestandsstueck(self):
        response = self.client.post(
            reverse("inventory_manage:project_create"), self._daten()
        )
        self.assertEqual(response.status_code, 302)
        projekt = Project.objects.get()
        self.assertIsNone(projekt.stock_item)
        self.assertEqual(projekt.created_by, self.admin)

    def test_zuordnung_reserviert_das_stueck(self):
        stueck = make_stock_item(self.lieferant)
        self.client.post(
            reverse("inventory_manage:project_create"),
            self._daten(stock_item=stueck.pk, customer=self.kunde.pk),
        )
        stueck.refresh_from_db()
        self.assertEqual(stueck.status, StockItem.Status.RESERVIERT)
        self.assertEqual(stueck.reserved_for, self.kunde)

    def test_plan_uebernehmen_schreibt_auf_das_stueck(self):
        stueck = make_stock_item(self.lieferant)
        self.client.post(
            reverse("inventory_manage:project_create"),
            self._daten(stock_item=stueck.pk),
        )
        projekt = Project.objects.get()
        self.client.post(
            reverse("inventory_manage:project_apply", args=[projekt.pk])
        )
        stueck.refresh_from_db()
        self.assertEqual(stueck.color, "Grau meliert")
        self.assertTrue(stueck.events.filter(kind=StockItemEvent.Kind.PROJEKT).exists())

    def test_erledigt_markieren(self):
        stueck = make_stock_item(self.lieferant)
        self.client.post(
            reverse("inventory_manage:project_create"),
            self._daten(stock_item=stueck.pk),
        )
        projekt = Project.objects.get()
        self.client.post(reverse("inventory_manage:project_done", args=[projekt.pk]))
        projekt.refresh_from_db()
        self.assertEqual(projekt.status, Project.Status.ERLEDIGT)
        self.assertTrue(stueck.events.filter(kind=StockItemEvent.Kind.PROJEKT).exists())

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        url = reverse("inventory_manage:project_list")
        self.assertEqual(self.client.get(url).status_code, 403)


class WorkStateTest(TestCase):
    """Der Arbeitsstand ersetzt die frueheren Fertigungsphasen und wird
    ausschliesslich aus den Projekten abgeleitet.
    """

    def setUp(self):
        self.stueck = make_stock_item(make_supplier())

    def _projekt(self, status):
        return Project.objects.create(
            title="Umbau", stock_item=self.stueck, status=status
        )

    def test_ohne_projekt_kein_arbeitsstand(self):
        self.assertIsNone(self.stueck.work_state)

    def test_offenes_projekt_meldet_in_arbeit(self):
        self._projekt(Project.Status.OFFEN)
        self.assertEqual(self.stueck.work_state, ("offen", "In Arbeit"))

    def test_erledigtes_projekt_meldet_fertig(self):
        self._projekt(Project.Status.ERLEDIGT)
        self.assertEqual(self.stueck.work_state, ("erledigt", "Fertig"))

    def test_offen_schlaegt_erledigt(self):
        self._projekt(Project.Status.ERLEDIGT)
        self._projekt(Project.Status.OFFEN)
        self.assertEqual(self.stueck.work_state, ("offen", "In Arbeit"))

    def test_storniertes_projekt_zaehlt_nicht(self):
        self._projekt(Project.Status.STORNIERT)
        self.assertIsNone(self.stueck.work_state)


class StatusMigrationTest(TestCase):
    """Die Umstellung von fuenf auf drei Projektzustaende darf keinen
    Altwert liegen lassen - sonst steht auf dem Server ein Status, den es
    im Modell nicht mehr gibt.
    """

    ALTE_WERTE = {"geplant", "in_arbeit", "fertig", "abgeholt", "storniert"}

    def test_zuordnung_ist_vollstaendig_und_gueltig(self):
        from importlib import import_module

        migration = import_module("inventory.migrations.0007_phasen_entfernen")
        abgedeckt = set(migration.VORWAERTS) | {"storniert"}
        self.assertEqual(abgedeckt, self.ALTE_WERTE)
        gueltig = set(Project.Status.values)
        self.assertTrue(set(migration.VORWAERTS.values()) <= gueltig)
        self.assertTrue(set(migration.RUECKWAERTS) <= gueltig)


class PublishBlockersTest(TestCase):
    """Halbfertige Datensaetze duerfen nicht in den Shop."""

    def setUp(self):
        self.lieferant = make_supplier()

    def _mit_bild(self, **overrides):
        stueck = make_stock_item(self.lieferant, **overrides)
        StockItemImage.objects.create(
            stock_item=stueck, image=make_image(), kind=StockItemImage.Kind.SHOP
        )
        return stueck

    def test_vollstaendige_peruecke_ist_bereit(self):
        self.assertEqual(self._mit_bild().publish_blockers(), [])

    def test_ohne_foto_nicht_bereit(self):
        stueck = make_stock_item(self.lieferant)
        self.assertIn("mindestens ein Verkaufsbild", stueck.publish_blockers())

    def test_eingangsbild_reicht_nicht(self):
        """Eingangsbilder zeigen den Anlieferungszustand und duerfen nicht
        stellvertretend in den Shop.
        """
        stueck = make_stock_item(self.lieferant)
        StockItemImage.objects.create(
            stock_item=stueck, image=make_image(), kind=StockItemImage.Kind.EINGANG
        )
        self.assertEqual(stueck.shop_images, [])
        self.assertIn("mindestens ein Verkaufsbild", stueck.publish_blockers())

    def test_fehlende_haarangaben_werden_gemeldet(self):
        stueck = self._mit_bild(structure="", density="")
        blocker = stueck.publish_blockers()
        self.assertIn("Schnitt", blocker)
        self.assertIn("Dichte", blocker)

    def test_pflegeprodukt_braucht_keine_haarangaben(self):
        stueck = self._mit_bild(
            shop_category=Product.Category.PFLEGE,
            structure="", density="", cap_type="", quantity=5,
        )
        self.assertEqual(stueck.publish_blockers(), [])

    def test_verkauftes_stueck_ist_nicht_bereit(self):
        stueck = self._mit_bild(status=StockItem.Status.VERKAUFT)
        self.assertIn("verkaufsfähiger Status", " ".join(stueck.publish_blockers()))


class StockItemDeleteTest(StaffViewMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.stueck = make_stock_item(self.lieferant)
        StockItemImage.objects.create(
            stock_item=self.stueck, image=make_image(), kind=StockItemImage.Kind.SHOP
        )

    def _url(self):
        return reverse("inventory_manage:stock_delete", args=[self.stueck.pk])

    def test_bestaetigungsseite_zeigt_umfang(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["anzahl_bilder"], 1)
        self.assertFalse(response.context["verkauft"])

    def test_loeschen_entfernt_datensatz_und_datei(self):
        pfad = self.stueck.images.get().image.path
        self.assertTrue(os.path.exists(pfad))
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StockItem.objects.count(), 0)
        self.assertEqual(StockItemImage.objects.count(), 0)
        self.assertFalse(os.path.exists(pfad), "Bilddatei blieb im Medienordner liegen")

    def test_shopbilder_bleiben_beim_loeschen_liegen(self):
        """Online gestellte Stuecke teilen sich die Datei mit der Shop-Galerie
        (sync_to_product kopiert nicht). Loeschen darf sie nicht mitnehmen.
        """
        bild = self.stueck.images.get()
        pfad = bild.image.path
        produkt = make_product("bob-klassik", image=bild.image.name)
        ProductImage.objects.create(product=produkt, image=bild.image.name)
        self.stueck.product = produkt
        self.stueck.save(update_fields=["product"])

        self.client.post(self._url())

        self.assertEqual(StockItem.objects.count(), 0)
        self.assertTrue(os.path.exists(pfad), "Shop-Galerie verlor ihre Bilddatei")

    def test_verkauftes_stueck_wird_geschuetzt(self):
        bestellung = Order.objects.create(customer_name="Frau M.", total=890)
        OrderItem.objects.create(
            order=bestellung, stock_item=self.stueck,
            description="Bob Klassik", quantity=1, price=890,
        )
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StockItem.objects.filter(pk=self.stueck.pk).exists())

    def test_ausmustern_als_ausweg(self):
        self.client.post(
            reverse("inventory_manage:stock_retire", args=[self.stueck.pk])
        )
        self.stueck.refresh_from_db()
        self.assertEqual(self.stueck.status, StockItem.Status.AUSGEMUSTERT)

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        self.assertEqual(self.client.get(self._url()).status_code, 403)


class ShopGalerieTest(StaffViewMixin, TestCase):
    """Was aus dem Bestand in die Shop-Galerie wandert - und in welcher Reihenfolge."""

    def setUp(self):
        super().setUp()
        self.stueck = make_stock_item(self.lieferant)
        self.bilder = [
            StockItemImage.objects.create(
                stock_item=self.stueck, image=make_image(f"shop-{i}.jpg"),
                kind=StockItemImage.Kind.SHOP, sort_order=i,
            )
            for i in range(3)
        ]
        self.produkt = make_product("bob-klassik")
        self.stueck.product = self.produkt
        self.stueck.save(update_fields=["product"])

    def test_erstes_bild_ist_nur_hauptbild(self):
        """Drei Fotos ergeben ein Hauptbild und zwei Galeriebilder - sonst
        zeigt die Produktseite das erste doppelt.
        """
        self.stueck.sync_to_product()
        self.produkt.refresh_from_db()
        self.assertEqual(self.produkt.image.name, self.bilder[0].image.name)
        galerie = [b.image.name for b in self.produkt.images.all()]
        self.assertEqual(galerie, [self.bilder[1].image.name, self.bilder[2].image.name])
        self.assertNotIn(self.produkt.image.name, galerie)

    def test_reihenfolge_aus_dem_bestand_wird_uebernommen(self):
        self.bilder[2].sort_order = 0
        self.bilder[2].save(update_fields=["sort_order"])
        self.bilder[0].sort_order = 2
        self.bilder[0].save(update_fields=["sort_order"])

        self.stueck.sync_to_product()
        self.produkt.refresh_from_db()
        self.assertEqual(self.produkt.image.name, self.bilder[2].image.name)
        self.assertEqual(
            [b.image.name for b in self.produkt.images.all()],
            [self.bilder[1].image.name, self.bilder[0].image.name],
        )

    def test_hauptbilddatei_ueberlebt_das_loeschen_des_stuecks(self):
        """Das Hauptbild steht nur noch in Product.image, nicht mehr in der
        Galerie - die Loeschsperre muss beide Seiten pruefen.
        """
        self.stueck.sync_to_product()
        pfad = self.bilder[0].image.path
        self.client.post(
            reverse("inventory_manage:stock_delete", args=[self.stueck.pk])
        )
        self.assertEqual(StockItem.objects.count(), 0)
        self.assertTrue(os.path.exists(pfad), "Hauptbild des Produkts wurde gelöscht")


class ProjectArchiveTest(StaffViewMixin, TestCase):
    """Abgeschlossene Projekte verlassen die Arbeitsliste und sind im Archiv
    wiederzufinden - und von dort zurueckzuholen.
    """

    def setUp(self):
        super().setUp()
        self.stueck = make_stock_item(self.lieferant)
        self.projekt = Project.objects.create(
            title="Umbau Frau M.", stock_item=self.stueck,
            status=Project.Status.ERLEDIGT,
        )
        self.offen = Project.objects.create(
            title="Neuanfertigung", status=Project.Status.OFFEN
        )

    def test_arbeitsliste_zeigt_nur_offene(self):
        response = self.client.get(reverse("inventory_manage:project_list"))
        projekte = list(response.context["projekte"])
        self.assertIn(self.offen, projekte)
        self.assertNotIn(self.projekt, projekte)

    def test_archiv_zeigt_abgeschlossene(self):
        storniert = Project.objects.create(
            title="Abgesagt", status=Project.Status.STORNIERT
        )
        response = self.client.get(reverse("inventory_manage:project_archive"))
        projekte = list(response.context["projekte"])
        self.assertIn(self.projekt, projekte)
        self.assertIn(storniert, projekte)
        self.assertNotIn(self.offen, projekte)

    def test_wieder_oeffnen_setzt_status_und_schreibt_historie(self):
        response = self.client.post(
            reverse("inventory_manage:project_reopen", args=[self.projekt.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.projekt.refresh_from_db()
        self.assertEqual(self.projekt.status, Project.Status.OFFEN)
        ereignis = self.stueck.events.filter(
            kind=StockItemEvent.Kind.PROJEKT
        ).latest("changed_at")
        self.assertEqual(ereignis.from_value, "Erledigt")
        self.assertEqual(ereignis.to_value, "Offen")

    def test_offenes_projekt_bleibt_unveraendert(self):
        self.client.post(
            reverse("inventory_manage:project_reopen", args=[self.offen.pk])
        )
        self.offen.refresh_from_db()
        self.assertEqual(self.offen.status, Project.Status.OFFEN)

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        self.assertEqual(
            self.client.get(reverse("inventory_manage:project_archive")).status_code,
            403,
        )

    def test_formular_zeigt_groesse_als_festwert(self):
        """Die Kopfgroesse steht als Text da, nicht als Auswahlfeld."""
        response = self.client.get(
            reverse("inventory_manage:project_edit", args=[self.projekt.pk])
        )
        inhalt = response.content.decode()
        self.assertContains(response, "wws-festwert")
        self.assertIn(self.stueck.size, inhalt)
        self.assertNotIn("target_size", inhalt)

    def test_formular_ohne_stueck_meldet_offene_groesse(self):
        response = self.client.get(
            reverse("inventory_manage:project_edit", args=[self.offen.pk])
        )
        self.assertContains(response, "wws-festwert--leer")


class StockItemListSucheTest(StaffViewMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.stueck = make_stock_item(
            self.lieferant, product_name="Bob", supplier_article_no="EW-4711"
        )
        self.anderes = make_stock_item(self.lieferant, product_name="Long Layers")

    def test_suche_findet_ueber_die_lieferanten_artikelnummer(self):
        response = self.client.get(
            reverse("inventory_manage:stock_list"), {"q": "4711"}
        )
        self.assertEqual(list(response.context["stuecke"]), [self.stueck])


class ProjectPickStockTest(StaffViewMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.peruecke = make_stock_item(self.lieferant, product_name="Bob")
        self.pflege = make_stock_item(
            self.lieferant, product_name="Shampoo",
            shop_category=Product.Category.PFLEGE,
        )

    def test_nur_haarware_steht_zur_wahl(self):
        response = self.client.get(reverse("inventory_manage:project_pick_stock"))
        gezeigt = list(response.context["stuecke"])
        self.assertIn(self.peruecke, gezeigt)
        self.assertNotIn(self.pflege, gezeigt)

    def test_suche_filtert(self):
        response = self.client.get(
            reverse("inventory_manage:project_pick_stock"), {"q": "Bob"}
        )
        self.assertEqual(list(response.context["stuecke"]), [self.peruecke])

    def test_eingaben_ueberleben_den_seitenwechsel(self):
        """Der Umweg ueber die Auswahlseite darf das Formular nicht leeren."""
        self.client.post(
            reverse("inventory_manage:project_pick_stock"),
            {"title": "Umbau Frau M.", "notes": "Kundin möchte kürzer."},
        )
        response = self.client.get(reverse("inventory_manage:project_create"))
        initial = response.context["form"].initial
        self.assertEqual(initial["title"], "Umbau Frau M.")
        self.assertEqual(initial["notes"], "Kundin möchte kürzer.")

    def test_pflegeprodukt_ist_im_formular_nicht_waehlbar(self):
        response = self.client.get(reverse("inventory_manage:project_create"))
        auswahl = response.context["form"].fields["stock_item"].queryset
        self.assertNotIn(self.pflege, auswahl)


class CustomerSearchTest(StaffViewMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user(
            email="anna.meier@example.com", password="pass12345",
            first_name="Anna", last_name="Meier",
        )
        User.objects.create_user(
            email="firma@example.com", password="pass12345",
            role=User.Role.B2B, company_name="Salon Nord",
        )

    def _suche(self, q):
        response = self.client.get(
            reverse("inventory_manage:customer_search"), {"q": q}
        )
        return json.loads(response.content)["treffer"]

    def test_suche_nach_nachname(self):
        treffer = self._suche("meier")
        self.assertEqual(len(treffer), 1)
        self.assertEqual(treffer[0]["name"], "Anna Meier")

    def test_suche_nach_firma_markiert_b2b(self):
        treffer = self._suche("Salon")
        self.assertEqual(len(treffer), 1)
        self.assertTrue(treffer[0]["b2b"])

    def test_zu_kurze_eingabe_liefert_nichts(self):
        self.assertEqual(self._suche("a"), [])

    def test_verwaltungskonten_tauchen_nicht_auf(self):
        self.assertEqual(self._suche("admin@example.com"), [])

    def test_b2c_bekommt_403(self):
        self.client.force_login(self.kunde)
        response = self.client.get(reverse("inventory_manage:customer_search"))
        self.assertEqual(response.status_code, 403)
