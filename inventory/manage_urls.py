from django.urls import path

from . import manage_views

app_name = "inventory_manage"

urlpatterns = [
    path("", manage_views.HomeView.as_view(), name="home"),

    # Lieferanten
    path("lieferanten/", manage_views.SupplierListView.as_view(), name="supplier_list"),
    path("lieferanten/neu/", manage_views.SupplierCreateView.as_view(), name="supplier_create"),
    path("lieferanten/<int:pk>/bearbeiten/", manage_views.SupplierUpdateView.as_view(), name="supplier_edit"),

    # Fertigungsphasen
    path("phasen/", manage_views.PhaseListView.as_view(), name="phase_list"),
    path("phasen/neu/", manage_views.PhaseCreateView.as_view(), name="phase_create"),
    path("phasen/<int:pk>/bearbeiten/", manage_views.PhaseUpdateView.as_view(), name="phase_edit"),

    # Bestand
    path("bestand/", manage_views.StockItemListView.as_view(), name="stock_list"),
    path("bestand/neu/", manage_views.StockItemCreateView.as_view(), name="stock_create"),
    path("bestand/<int:pk>/bearbeiten/", manage_views.StockItemUpdateView.as_view(), name="stock_edit"),
]
