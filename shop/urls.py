from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.CartPageView.as_view(), name="cart"),
    path("api/produkte/", views.api_products, name="api_products"),
    path("api/", views.api_cart, name="api_cart"),
    path("api/add/", views.api_add, name="api_add"),
    path("api/update/", views.api_update, name="api_update"),
    path("api/remove/", views.api_remove, name="api_remove"),
    path("api/merge/", views.api_merge, name="api_merge"),
]
