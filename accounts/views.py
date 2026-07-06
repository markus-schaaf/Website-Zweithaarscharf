from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import B2BRegistrationForm, LoginForm, RegistrationForm, UserManageForm

User = get_user_model()


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Erlaubt den Zugriff nur fuer die angegebenen Rollen (sonst 403)."""

    allowed_roles = ()
    raise_exception = True

    def test_func(self):
        return self.request.user.role in self.allowed_roles


class KontoLoginView(auth_views.LoginView):
    template_name = "tasty/account/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class RegistrierenView(CreateView):
    form_class = RegistrationForm
    template_name = "tasty/account/register.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Willkommen! Ihr Konto wurde erstellt."

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, self.success_message)
        return response


class RegistrierenFirmaView(RegistrierenView):
    form_class = B2BRegistrationForm
    template_name = "tasty/account/register_firma.html"
    success_message = "Willkommen! Ihr Geschäftskonto wurde erstellt."


class ProfilView(LoginRequiredMixin, TemplateView):
    template_name = "tasty/account/profile.html"


class BenutzerListeView(RoleRequiredMixin, ListView):
    allowed_roles = (User.Role.ALL_POWER, User.Role.ADMIN)
    model = User
    ordering = "date_joined"
    template_name = "tasty/account/user_list.html"
    context_object_name = "benutzer"


class BenutzerBearbeitenView(RoleRequiredMixin, UpdateView):
    allowed_roles = (User.Role.ADMIN,)
    model = User
    form_class = UserManageForm
    template_name = "tasty/account/user_edit.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        if form.instance.pk == self.request.user.pk:
            messages.error(
                self.request,
                "Sie können Ihr eigenes Konto nicht bearbeiten (Schutz vor Selbst-Aussperrung).",
            )
            return redirect("accounts:user_list")
        messages.success(self.request, f"Benutzer {form.instance.email} wurde gespeichert.")
        return super().form_valid(form)


class BenutzerLoeschenView(RoleRequiredMixin, DeleteView):
    allowed_roles = (User.Role.ADMIN,)
    model = User
    template_name = "tasty/account/user_confirm_delete.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        if self.object.pk == self.request.user.pk:
            messages.error(self.request, "Sie können Ihr eigenes Konto nicht löschen.")
            return redirect("accounts:user_list")
        messages.success(self.request, f"Benutzer {self.object.email} wurde gelöscht.")
        return super().form_valid(form)
