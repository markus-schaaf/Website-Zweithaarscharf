"""
URL configuration for zweithaarschaaf project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from pages.views import ContactView, ReservationView
from shop.views import ProductDetailView, WigsView

from .sitemaps import SITEMAPS

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
    path("konto/produkte/", include("shop.manage_urls")),
    path("konto/", include("accounts.urls")),
    path("warenkorb/", include("shop.urls")),
    path(
        "",
        TemplateView.as_view(
            template_name="tasty/index.html", extra_context={"active": "home"}
        ),
        name="home",
    ),
    path("peruecken/", WigsView.as_view(), name="wigs"),
    path(
        "peruecken/<slug:slug>/",
        ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "leistungen/",
        TemplateView.as_view(
            template_name="tasty/services.html", extra_context={"active": "services"}
        ),
        name="services",
    ),
    path(
        "galerie/",
        TemplateView.as_view(
            template_name="tasty/gallery.html", extra_context={"active": "gallery"}
        ),
        name="gallery",
    ),
    path("beratungstermin/", ReservationView.as_view(), name="reservation"),
    path(
        "ueber-uns/",
        TemplateView.as_view(
            template_name="tasty/about.html", extra_context={"active": "about"}
        ),
        name="about",
    ),
    path("kontakt/", ContactView.as_view(), name="contact"),
    path("", include("pages.urls")),
    # path("trainings/", include("trainings.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
