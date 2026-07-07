import io
import shutil
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Product3DAsset
from .services.providers import JobResult, MeshyProvider, ProviderError
from .tests import make_product

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp(prefix="test-media-3d-")


def make_png(name="foto.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 90, 60)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_asset(product, **kwargs):
    return Product3DAsset.objects.create(
        product=product, source_image_1=make_png(), **kwargs
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class Access3DViewsTest(TestCase):
    """Nur All Power/Admin duerfen Upload, Generierung und Freigabe ausloesen."""

    @classmethod
    def setUpTestData(cls):
        cls.product = make_product("3d-produkt")
        cls.b2c = User.objects.create_user(email="b2c@example.com", password="pass12345")
        cls.b2b = User.objects.create_user(
            email="b2b@example.com", password="pass12345", role=User.Role.B2B
        )
        cls.all_power = User.objects.create_user(
            email="power@example.com", password="pass12345", role=User.Role.ALL_POWER
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com", password="pass12345", role=User.Role.ADMIN
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def all_3d_urls(self):
        pk = self.product.pk
        return [
            reverse("shop_manage:product_3d", args=[pk]),
            reverse("shop_manage:product_3d_generate", args=[pk]),
            reverse("shop_manage:product_3d_visibility", args=[pk]),
            reverse("shop_manage:product_3d_status", args=[pk]),
        ]

    def test_anonymous_and_customers_denied(self):
        for user in (None, self.b2c, self.b2b):
            if user is None:
                self.client.logout()
            else:
                self.client.force_login(user)
            for url in self.all_3d_urls():
                self.assertEqual(self.client.get(url).status_code, 403, url)
                self.assertEqual(self.client.post(url).status_code, 403, url)

    def test_staff_can_open_page_and_status(self):
        for user in (self.all_power, self.admin):
            self.client.force_login(user)
            url = reverse("shop_manage:product_3d", args=[self.product.pk])
            self.assertEqual(self.client.get(url).status_code, 200)
            status_url = reverse("shop_manage:product_3d_status", args=[self.product.pk])
            self.assertEqual(self.client.get(status_url).json()["status"], "none")

    @patch("shop.manage_views.generate_3d_model")
    def test_staff_upload_creates_asset_and_dispatches_task(self, mock_task):
        self.client.force_login(self.all_power)
        url = reverse("shop_manage:product_3d", args=[self.product.pk])
        response = self.client.post(url, {"source_image_1": make_png()})
        self.assertRedirects(response, url)
        asset = self.product.assets_3d.first()
        self.assertIsNotNone(asset)
        self.assertEqual(asset.generated_by, self.all_power)
        mock_task.delay.assert_called_once_with(asset.pk)

    @patch("shop.manage_views.generate_3d_model")
    def test_regenerate_resets_status(self, mock_task):
        asset = make_asset(
            self.product,
            status=Product3DAsset.Status.FAILED,
            error_message="kaputt",
        )
        self.client.force_login(self.admin)
        url = reverse("shop_manage:product_3d_generate", args=[self.product.pk])
        self.client.post(url)
        asset.refresh_from_db()
        self.assertEqual(asset.status, Product3DAsset.Status.PENDING)
        self.assertEqual(asset.error_message, "")
        mock_task.delay.assert_called_once_with(asset.pk)

    def test_visibility_toggle_requires_done_asset(self):
        self.client.force_login(self.all_power)
        url = reverse("shop_manage:product_3d_visibility", args=[self.product.pk])

        self.client.post(url)  # kein fertiges Asset: darf nichts freigeben
        self.assertFalse(
            Product3DAsset.objects.filter(product=self.product, is_public=True).exists()
        )

        asset = make_asset(self.product, status=Product3DAsset.Status.DONE)
        self.client.post(url)
        asset.refresh_from_db()
        self.assertTrue(asset.is_public)
        self.client.post(url)
        asset.refresh_from_db()
        self.assertFalse(asset.is_public)


class MeshyProviderTest(TestCase):
    """Adapter-Verhalten gegen gemockte Meshy-API-Antworten."""

    def response(self, status_code=200, payload=None, text=""):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = payload or {}
        mock.text = text
        return mock

    @override_settings(MESHY_API_KEY="testkey")
    @patch("shop.services.providers.requests.request")
    def test_create_job_returns_task_id(self, mock_request):
        mock_request.return_value = self.response(payload={"result": "task-123"})
        job_id = MeshyProvider().create_job([b"png-bytes"])
        self.assertEqual(job_id, "task-123")
        payload = mock_request.call_args.kwargs["json"]
        self.assertEqual(len(payload["image_urls"]), 1)
        self.assertTrue(payload["image_urls"][0].startswith("data:image/png;base64,"))

    @override_settings(MESHY_API_KEY="testkey")
    @patch("shop.services.providers.requests.request")
    def test_poll_job_maps_states(self, mock_request):
        provider = MeshyProvider()

        mock_request.return_value = self.response(
            payload={
                "status": "SUCCEEDED",
                "model_urls": {"glb": "https://assets.example/m.glb"},
                "thumbnail_url": "https://assets.example/t.png",
            }
        )
        result = provider.poll_job("task-123")
        self.assertEqual(
            (result.status, result.glb_url, result.thumbnail_url),
            ("done", "https://assets.example/m.glb", "https://assets.example/t.png"),
        )

        mock_request.return_value = self.response(
            payload={"status": "FAILED", "task_error": {"message": "bad input"}}
        )
        result = provider.poll_job("task-123")
        self.assertEqual(result.status, "failed")
        self.assertIn("bad input", result.error)

        mock_request.return_value = self.response(payload={"status": "IN_PROGRESS"})
        self.assertEqual(provider.poll_job("task-123").status, "processing")

    def test_missing_api_key_raises(self):
        with self.assertRaises(ProviderError):
            MeshyProvider().create_job([b"png-bytes"])

    @override_settings(MESHY_API_KEY="testkey")
    @patch("shop.services.providers.time.sleep")
    @patch("shop.services.providers.requests.request")
    def test_server_errors_are_retried_then_raise(self, mock_request, mock_sleep):
        mock_request.return_value = self.response(status_code=500, text="kaputt")
        with self.assertRaises(ProviderError):
            MeshyProvider().create_job([b"png-bytes"])
        self.assertEqual(mock_request.call_count, MeshyProvider.MAX_RETRIES)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class GenerateTaskTest(TestCase):
    """Task-Pipeline mit gemocktem Provider und Preprocessing."""

    @classmethod
    def setUpTestData(cls):
        cls.product = make_product("task-produkt")

    def run_task(self, asset, provider):
        from .tasks import generate_3d_model

        with patch(
            "shop.services.preprocessing.prepare_source_image", return_value=b"composite"
        ), patch("shop.services.providers.get_provider", return_value=provider):
            generate_3d_model(asset.pk)
        asset.refresh_from_db()
        return asset

    def test_success_sets_done_and_saves_files(self):
        provider = MagicMock()
        provider.name = "meshy"
        provider.create_job.return_value = "task-123"
        provider.poll_job.return_value = JobResult(
            status="done",
            glb_url="https://assets.example/m.glb",
            thumbnail_url="https://assets.example/t.png",
        )
        provider.download.return_value = b"glb-bytes"

        asset = self.run_task(make_asset(self.product), provider)
        self.assertEqual(asset.status, Product3DAsset.Status.DONE)
        self.assertEqual(asset.provider, "meshy")
        self.assertEqual(asset.provider_job_id, "task-123")
        self.assertTrue(asset.model_file.name.endswith(".glb"))
        self.assertTrue(asset.preview_thumbnail)

    def test_provider_error_sets_failed_without_raising(self):
        provider = MagicMock()
        provider.name = "meshy"
        provider.create_job.side_effect = ProviderError("MESHY_API_KEY ist nicht gesetzt")

        asset = self.run_task(make_asset(self.product), provider)
        self.assertEqual(asset.status, Product3DAsset.Status.FAILED)
        self.assertIn("MESHY_API_KEY", asset.error_message)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class DetailPage3DTest(TestCase):
    """Kunden sehen den 3D-Viewer nur bei fertigem, freigegebenem Modell."""

    @classmethod
    def setUpTestData(cls):
        cls.product = make_product("viewer-produkt")

    def make_done_asset(self, is_public):
        asset = make_asset(
            self.product, status=Product3DAsset.Status.DONE, is_public=is_public
        )
        asset.model_file.save(
            "m.glb", SimpleUploadedFile("m.glb", b"glb"), save=True
        )
        return asset

    def test_public_done_asset_renders_model_viewer(self):
        self.make_done_asset(is_public=True)
        response = self.client.get(reverse("product_detail", args=[self.product.slug]))
        self.assertContains(response, "<model-viewer")
        self.assertContains(response, "model-viewer.min.js")

    def test_unpublished_asset_falls_back_to_image(self):
        self.make_done_asset(is_public=False)
        response = self.client.get(reverse("product_detail", args=[self.product.slug]))
        self.assertNotContains(response, "<model-viewer")
