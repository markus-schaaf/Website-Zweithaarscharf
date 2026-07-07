from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("impressum/", views.ImpressumView.as_view(), name="impressum"),
    path("datenschutz/", views.DatenschutzView.as_view(), name="datenschutz"),
]
