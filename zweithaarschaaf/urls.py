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

from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "",
        TemplateView.as_view(
            template_name="tasty/index.html", extra_context={"active": "home"}
        ),
        name="home",
    ),
    path(
        "peruecken/",
        TemplateView.as_view(
            template_name="tasty/menu.html", extra_context={"active": "wigs"}
        ),
        name="wigs",
    ),
    path(
        "galerie/",
        TemplateView.as_view(
            template_name="tasty/gallery.html", extra_context={"active": "gallery"}
        ),
        name="gallery",
    ),
    path(
        "beratungstermin/",
        TemplateView.as_view(
            template_name="tasty/reservation.html",
            extra_context={"active": "reservation"},
        ),
        name="reservation",
    ),
    path(
        "ueber-uns/",
        TemplateView.as_view(
            template_name="tasty/about.html", extra_context={"active": "about"}
        ),
        name="about",
    ),
    path(
        "kontakt/",
        TemplateView.as_view(
            template_name="tasty/contact.html", extra_context={"active": "contact"}
        ),
        name="contact",
    ),
    # path("pages/", include("pages.urls")),
    # path("trainings/", include("trainings.urls")),
]
