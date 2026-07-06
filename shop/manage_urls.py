from django.urls import path

from . import manage_views

app_name = "shop_manage"

urlpatterns = [
    path("", manage_views.ProduktListeView.as_view(), name="product_list"),
    path("neu/", manage_views.ProduktErstellenView.as_view(), name="product_create"),
    path(
        "<int:pk>/bearbeiten/",
        manage_views.ProduktBearbeitenView.as_view(),
        name="product_edit",
    ),
]
