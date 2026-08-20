from django.urls import path

from . import manage_views

app_name = "inventory_manage"

urlpatterns = [
    path("", manage_views.HomeView.as_view(), name="home"),

    # Lieferanten
    path("lieferanten/", manage_views.SupplierListView.as_view(), name="supplier_list"),
    path("lieferanten/neu/", manage_views.SupplierCreateView.as_view(), name="supplier_create"),
    path("lieferanten/<int:pk>/bearbeiten/", manage_views.SupplierUpdateView.as_view(), name="supplier_edit"),

    # Auswahlwerte
    path("auswahlwerte/", manage_views.AttributeListView.as_view(), name="attribute_list"),
    path("auswahlwerte/neu/", manage_views.AttributeCreateView.as_view(), name="attribute_create"),
    path("auswahlwerte/<int:pk>/bearbeiten/", manage_views.AttributeUpdateView.as_view(), name="attribute_edit"),

    # Bestand
    path("bestand/", manage_views.StockItemListView.as_view(), name="stock_list"),
    path("bestand/neu/", manage_views.StockItemCreateView.as_view(), name="stock_create"),
    path("bestand/<int:pk>/bearbeiten/", manage_views.StockItemUpdateView.as_view(), name="stock_edit"),
    path("bestand/<int:pk>/onlinestellen/", manage_views.StockItemPublishView.as_view(), name="stock_publish"),
    path("bestand/<int:pk>/zurueckziehen/", manage_views.StockItemUnpublishView.as_view(), name="stock_unpublish"),
    path("bestand/<int:pk>/loeschen/", manage_views.StockItemDeleteView.as_view(), name="stock_delete"),
    path("bestand/<int:pk>/ausmustern/", manage_views.StockItemRetireView.as_view(), name="stock_retire"),
    path("bestand/<int:pk>/verkaufen/", manage_views.StockItemSellView.as_view(), name="stock_sell"),

    # Bestellware (Lieferantenkatalog)
    path("bestellware/", manage_views.CatalogItemListView.as_view(), name="catalog_list"),
    path("bestellware/neu/", manage_views.CatalogItemCreateView.as_view(), name="catalog_create"),
    path("bestellware/<int:pk>/bearbeiten/", manage_views.CatalogItemUpdateView.as_view(), name="catalog_edit"),
    path("bestellware/<int:pk>/onlinestellen/", manage_views.CatalogItemPublishView.as_view(), name="catalog_publish"),
    path("bestellware/<int:pk>/zurueckziehen/", manage_views.CatalogItemUnpublishView.as_view(), name="catalog_unpublish"),
    path("bestellware/<int:pk>/loeschen/", manage_views.CatalogItemDeleteView.as_view(), name="catalog_delete"),

    # Verkäufe
    path("verkaeufe/", manage_views.OrderListView.as_view(), name="order_list"),
    path("verkaeufe/<int:pk>/erneut-senden/", manage_views.OrderResendView.as_view(), name="order_resend"),

    # Projekte
    path("projekte/", manage_views.ProjectListView.as_view(), name="project_list"),
    path("projekte/neu/", manage_views.ProjectCreateView.as_view(), name="project_create"),
    path("projekte/<int:pk>/bearbeiten/", manage_views.ProjectUpdateView.as_view(), name="project_edit"),
    path("projekte/<int:pk>/plan-uebernehmen/", manage_views.ProjectApplyPlanView.as_view(), name="project_apply"),
    path("projekte/<int:pk>/erledigt/", manage_views.ProjectDoneView.as_view(), name="project_done"),
    path("projekte/archiv/", manage_views.ProjectArchiveView.as_view(), name="project_archive"),
    path("projekte/<int:pk>/wieder-oeffnen/", manage_views.ProjectReopenView.as_view(), name="project_reopen"),
    path("projekte/bestand-waehlen/", manage_views.ProjectPickStockView.as_view(), name="project_pick_stock"),
    path("kunden/suche/", manage_views.CustomerSearchView.as_view(), name="customer_search"),
]
