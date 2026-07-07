from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import AppointmentRequest, ContactMessage


class PublicPagesSmokeTest(TestCase):
    """Alle öffentlichen Seiten liefern Status 200."""

    def test_public_pages_render(self):
        names = [
            "home",
            "wigs",
            "services",
            "gallery",
            "reservation",
            "about",
            "contact",
            "pages:impressum",
            "pages:datenschutz",
            "robots",
            "sitemap",
        ]
        for name in names:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)


class ContactFormTest(TestCase):
    def test_valid_post_saves_and_sends_mail(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Test Person",
                "email": "test@example.com",
                "message": "Eine Testnachricht.",
                "website": "",
            },
        )
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Test Person", mail.outbox[0].subject)

    def test_invalid_post_shows_errors(self):
        response = self.client.post(
            reverse("contact"),
            {"name": "", "email": "keine-mail", "message": "", "website": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)

    def test_honeypot_blocks_spam(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Bot",
                "email": "bot@example.com",
                "message": "Spam",
                "website": "http://spam.example",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)


class AppointmentFormTest(TestCase):
    def _data(self, **overrides):
        data = {
            "name": "Erika Musterfrau",
            "email": "erika@example.com",
            "phone": "",
            "topic": "bestandsperuecke",
            "preferred_datetime": "15.07.2026, 14:00",
            "message": "",
            "consent": "on",
            "website": "",
        }
        data.update(overrides)
        return data

    def test_valid_post_saves_and_sends_mail(self):
        response = self.client.post(reverse("reservation"), self._data())
        self.assertRedirects(response, reverse("reservation"))
        self.assertEqual(AppointmentRequest.objects.count(), 1)
        request_obj = AppointmentRequest.objects.get()
        self.assertTrue(request_obj.consent)
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_consent_is_rejected(self):
        data = self._data()
        del data["consent"]
        response = self.client.post(reverse("reservation"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AppointmentRequest.objects.count(), 0)
        self.assertIn("consent", response.context["form"].errors)
