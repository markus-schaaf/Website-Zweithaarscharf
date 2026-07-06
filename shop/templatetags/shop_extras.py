from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def euro(value):
    """Formatiert einen Betrag deutsch: 1190 -> '1.190,00 €'."""
    value = Decimal(value or 0)
    formatted = f"{value:,.2f}"  # 1,190.00
    formatted = formatted.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{formatted} €"
