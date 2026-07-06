from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.ProfilView.as_view(), name="profile"),
    path("login/", views.KontoLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("registrieren/", views.RegistrierenView.as_view(), name="register"),
    path("registrieren/firma/", views.RegistrierenFirmaView.as_view(), name="register_b2b"),
    path("benutzer/", views.BenutzerListeView.as_view(), name="user_list"),
    path(
        "benutzer/<int:pk>/bearbeiten/",
        views.BenutzerBearbeitenView.as_view(),
        name="user_edit",
    ),
    path(
        "benutzer/<int:pk>/loeschen/",
        views.BenutzerLoeschenView.as_view(),
        name="user_delete",
    ),
]
