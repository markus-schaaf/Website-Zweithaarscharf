import io
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Cart, CartItem, Product, ProductImage

User = get_user_model()


def make_image(name="foto.jpg"):
    """Kleines echtes JPEG - ImageField prueft den Dateiinhalt."""
    puffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(puffer, format="JPEG")
    return SimpleUploadedFile(name, puffer.getvalue(), content_type="image/jpeg")


def make_product(slug, category=Product.Category.BESTAND, audience=Product.Audience.B2C):
    return Product.objects.create(
        name=f"Produkt {slug}",
        label=slug.upper(),
        slug=slug,
        category=category,
        audience=audience,
        price=Decimal("100.00"),
    )


class ProductVisibilityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.b2c_product = make_product("b2c-produkt")
        cls.b2b_product = make_product("b2b-produkt", audience=Product.Audience.B2B)
        cls.b2c_user = User.objects.create_user(email="b2c@example.com", password="pass12345")
        cls.b2b_user = User.objects.create_user(
            email="b2b@example.com", password="pass12345", role=User.Role.B2B
        )

    def test_anonymous_sees_only_b2c(self):
        response = self.client.get(reverse("product_detail", args=["b2b-produkt"]))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse("product_detail", args=["b2c-produkt"]))
        self.assertEqual(response.status_code, 200)

    def test_b2b_user_sees_b2b_product(self):
        self.client.force_login(self.b2b_user)
        response = self.client.get(reverse("product_detail", args=["b2b-produkt"]))
        self.assertEqual(response.status_code, 200)

    def test_b2c_products_not_in_sitemap_for_b2b_only(self):
        response = self.client.get(reverse("sitemap"))
        content = response.content.decode()
        self.assertIn("b2c-produkt", content)
        self.assertNotIn("b2b-produkt", content)


class CartApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = make_product("warenkorb-produkt")
        cls.konfig = make_product("konfig-produkt", category=Product.Category.KONFIG)
        cls.user = User.objects.create_user(email="kunde@example.com", password="pass12345")

    def _post(self, name, payload):
        return self.client.post(
            reverse(name), json.dumps(payload), content_type="application/json"
        )

    def test_api_requires_login(self):
        response = self._post("shop:api_add", {"product_id": self.product.id})
        self.assertEqual(response.status_code, 401)

    def test_add_update_remove(self):
        self.client.force_login(self.user)

        response = self._post("shop:api_add", {"product_id": self.product.id, "quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

        response = self._post(
            "shop:api_update", {"product_id": self.product.id, "quantity": 5}
        )
        self.assertEqual(response.json()["quantity"], 5)

        response = self._post("shop:api_remove", {"product_id": self.product.id})
        self.assertEqual(response.json()["count"], 0)

    def test_configurable_product_not_orderable(self):
        self.client.force_login(self.user)
        response = self._post("shop:api_add", {"product_id": self.konfig.id})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_quantity_clamped_to_max(self):
        self.client.force_login(self.user)
        self._post("shop:api_add", {"product_id": self.product.id, "quantity": 500})
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 99)

    def test_merge_combines_anonymous_cart(self):
        self.client.force_login(self.user)
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        response = self._post(
            "shop:api_merge",
            {"items": {str(self.product.id): 3, str(self.konfig.id): 2, "unsinn": 1}},
        )
        self.assertEqual(response.status_code, 200)
        item = CartItem.objects.get(cart=cart, product=self.product)
        # 1 (vorhanden) + 3 (gemergt); konfigurierbares Produkt wird ignoriert
        self.assertEqual(item.quantity, 4)
        self.assertEqual(CartItem.objects.count(), 1)


class GalerieReihenfolgeTest(TestCase):
    """Die Reihenfolge der Galeriebilder wird im Produktformular gepflegt."""

    def setUp(self):
        self.staff = User.objects.create_user(
            email="staff@example.com", password="pass12345",
            role=User.Role.ALL_POWER,
        )
        self.client.force_login(self.staff)
        self.produkt = make_product("galerie-produkt")
        self.bilder = [
            ProductImage.objects.create(
                product=self.produkt, image=make_image(f"g{i}.jpg"), sort_order=i
            )
            for i in range(3)
        ]

    def _daten(self, **overrides):
        daten = {
            "name": self.produkt.name,
            "label": self.produkt.label,
            "category": self.produkt.category,
            "audience": self.produkt.audience,
            "price": "100.00",
            "stock_mode": self.produkt.stock_mode,
            "stock_quantity": self.produkt.stock_quantity,
            "sort_order": self.produkt.sort_order,
            "is_active": "on",
        }
        daten.update(overrides)
        return daten

    def _url(self):
        return reverse("shop_manage:product_edit", args=[self.produkt.pk])

    def test_reihenfolge_wird_gespeichert(self):
        umgedreht = [str(b.pk) for b in reversed(self.bilder)]
        response = self.client.post(
            self._url(), self._daten(image_order_galerie=umgedreht)
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            [str(b.pk) for b in self.produkt.images.all()], umgedreht
        )

    def test_geloeschtes_bild_verschiebt_die_uebrigen_nicht(self):
        response = self.client.post(self._url(), self._daten(
            delete_images_galerie=[str(self.bilder[0].pk)],
            image_order_galerie=[str(b.pk) for b in self.bilder],
        ))
        self.assertEqual(response.status_code, 302)
        uebrig = list(self.produkt.images.all())
        self.assertEqual([b.pk for b in uebrig],
                         [self.bilder[1].pk, self.bilder[2].pk])
        self.assertEqual([b.sort_order for b in uebrig], [0, 1])

    def test_neues_bild_haengt_sich_hinten_an(self):
        response = self.client.post(self._url(), self._daten(
            image_order_galerie=[str(b.pk) for b in self.bilder],
            extra_images=make_image("neu.jpg"),
        ))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.produkt.images.count(), 4)
        self.assertEqual(self.produkt.images.last().sort_order, 3)
