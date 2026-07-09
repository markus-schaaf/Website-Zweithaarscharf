import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import AppointmentForm, ContactForm, DigitalAppointmentForm
from .models import AppointmentRequest

logger = logging.getLogger(__name__)


class ImpressumView(TemplateView):
    template_name = "tasty/legal/impressum.html"


class DatenschutzView(TemplateView):
    template_name = "tasty/legal/datenschutz.html"


class RetoureView(TemplateView):
    template_name = "tasty/retoure.html"


def _notify(subject, body):
    """E-Mail an die Geschäftsadresse; Fehler dürfen die Anfrage nicht verwerfen."""
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONTACT_RECIPIENT_EMAIL],
            fail_silently=False,
        )
    except Exception:
        logger.exception("E-Mail-Benachrichtigung fehlgeschlagen (%s)", subject)


class ContactView(FormView):
    template_name = "tasty/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")
    extra_context = {"active": "contact"}

    def form_valid(self, form):
        obj = form.save()
        _notify(
            f"Neue Kontaktanfrage von {obj.name}",
            f"Name: {obj.name}\nE-Mail: {obj.email}\n\nNachricht:\n{obj.message}",
        )
        messages.success(
            self.request,
            "Vielen Dank für Ihre Nachricht! Wir melden uns so schnell wie möglich bei Ihnen.",
        )
        return super().form_valid(form)


class ReservationView(TemplateView):
    template_name = "tasty/reservation.html"
    extra_context = {"active": "reservation"}


class PraesenzReservationView(FormView):
    template_name = "tasty/reservation_praesenz.html"
    form_class = AppointmentForm
    success_url = reverse_lazy("reservation_praesenz")
    extra_context = {"active": "reservation"}

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.mode = AppointmentRequest.Mode.PRAESENZ
        obj.save()
        _notify(
            f"Neue Terminanfrage (Präsenz) von {obj.name}",
            (
                f"Beratungsform: {obj.get_mode_display()}\n"
                f"Name: {obj.name}\nE-Mail: {obj.email}\nTelefon: {obj.phone or '–'}\n"
                f"Art der Beratung: {obj.get_topic_display()}\nWunschtermin: {obj.preferred_datetime}\n\n"
                f"Nachricht:\n{obj.message or '–'}"
            ),
        )
        messages.success(
            self.request,
            "Vielen Dank für Ihre Terminanfrage! Wir melden uns zeitnah bei Ihnen, um den Termin zu bestätigen.",
        )
        return super().form_valid(form)


class DigitalReservationView(FormView):
    template_name = "tasty/reservation_digital.html"
    form_class = DigitalAppointmentForm
    success_url = reverse_lazy("reservation_digital")
    extra_context = {"active": "reservation"}

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.mode = AppointmentRequest.Mode.DIGITAL
        obj.save()
        _notify(
            f"Neue Terminanfrage (Digital) von {obj.name}",
            (
                f"Beratungsform: {obj.get_mode_display()}\n"
                f"Name: {obj.name}\nE-Mail: {obj.email}\nTelefon: {obj.phone or '–'}\n"
                f"Art der Beratung: {obj.get_topic_display()}\nVideo-Kanal: {obj.get_channel_display()}\n"
                f"Wunschtermin: {obj.preferred_datetime}\n\n"
                f"Nachricht:\n{obj.message or '–'}"
            ),
        )
        messages.success(
            self.request,
            "Vielen Dank für Ihre Terminanfrage! Wir melden uns zeitnah bei Ihnen, um den Termin und den Video-Link zu bestätigen.",
        )
        return super().form_valid(form)
