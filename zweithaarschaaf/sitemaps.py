from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from shop.models import Product


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return [
            "home",
            "wigs",
            "services",
            "gallery",
            "reservation",
            "about",
            "contact",
            "pages:impressum",
            "pages:datenschutz",
        ]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Nur öffentliche (B2C) aktive Produkte — B2B bleibt unsichtbar
        return Product.objects.filter(is_active=True, audience=Product.Audience.B2C)

    def location(self, obj):
        return reverse("product_detail", args=[obj.slug])


SITEMAPS = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
}
