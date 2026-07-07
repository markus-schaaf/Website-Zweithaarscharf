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
    path(
        "<int:pk>/3d/",
        manage_views.Produkt3DView.as_view(),
        name="product_3d",
    ),
    path(
        "<int:pk>/3d/generieren/",
        manage_views.Produkt3DGenerierenView.as_view(),
        name="product_3d_generate",
    ),
    path(
        "<int:pk>/3d/sichtbarkeit/",
        manage_views.Produkt3DSichtbarkeitView.as_view(),
        name="product_3d_visibility",
    ),
    path(
        "<int:pk>/3d/status/",
        manage_views.Produkt3DStatusView.as_view(),
        name="product_3d_status",
    ),
    path(
        "konfigurator/",
        manage_views.KonfiguratorListeView.as_view(),
        name="configurator_list",
    ),
    path(
        "konfigurator/gruppe/neu/",
        manage_views.GruppeErstellenView.as_view(),
        name="group_create",
    ),
    path(
        "konfigurator/gruppe/<int:pk>/bearbeiten/",
        manage_views.GruppeBearbeitenView.as_view(),
        name="group_edit",
    ),
    path(
        "konfigurator/option/neu/",
        manage_views.OptionErstellenView.as_view(),
        name="option_create",
    ),
    path(
        "konfigurator/option/<int:pk>/bearbeiten/",
        manage_views.OptionBearbeitenView.as_view(),
        name="option_edit",
    ),
    path(
        "konfigurator/option/<int:pk>/loeschen/",
        manage_views.OptionLoeschenView.as_view(),
        name="option_delete",
    ),
]
