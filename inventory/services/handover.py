"""Uebergabe der Verkaufsdaten an den Kollegen, der die Rechnung schreibt.

Siehe WARENWIRTSCHAFT_PLAN.md Abschnitt 6. Aktuell per E-Mail; die Funktion
kapselt den Weg, damit er spaeter austauschbar bleibt.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_invoice_mail(order):
    """Rechnungsdaten versenden. Gibt True bei Erfolg zurueck.

    Wirft nicht: ein Mailfehler darf den bereits gebuchten Verkauf nicht
    zurueckrollen. Der Zustand landet in order.export_status.
    """
    body = render_to_string("tasty/mail/rechnung.txt", {"order": order})
    try:
        send_mail(
            f"Rechnungsdaten Verkauf {order.pk} ({order.customer_display})",
            body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.INVOICE_RECIPIENT_EMAIL],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Rechnungsmail für Verkauf %s fehlgeschlagen", order.pk)
        order.export_status = order.ExportStatus.FAILED
        order.save(update_fields=["export_status"])
        return False

    order.export_status = order.ExportStatus.SENT
    order.status = order.Status.UEBERGEBEN
    order.save(update_fields=["export_status", "status"])
    return True
