from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "E-Mail-Adresse"
        self.fields["username"].widget.attrs.update(
            {"placeholder": "ihre@email.de", "autofocus": True}
        )
        self.fields["password"].label = "Passwort"
        self.fields["password"].widget.attrs.update({"placeholder": "Passwort"})


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
        labels = {
            "email": "E-Mail-Adresse",
            "first_name": "Vorname",
            "last_name": "Nachname",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["password1"].label = "Passwort"
        self.fields["password2"].label = "Passwort bestätigen"
        self.fields["email"].widget.attrs.update({"placeholder": "ihre@email.de"})


class B2BRegistrationForm(RegistrationForm):
    class Meta(RegistrationForm.Meta):
        fields = (
            "email",
            "first_name",
            "last_name",
            "company_name",
            "vat_id",
            "phone",
            "street",
            "zip_code",
            "city",
        )
        labels = {
            **RegistrationForm.Meta.labels,
            "company_name": "Firmenname",
            "vat_id": "USt-IdNr. (optional)",
            "phone": "Telefon",
            "street": "Straße und Hausnummer",
            "zip_code": "PLZ",
            "city": "Ort",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("company_name", "phone", "street", "zip_code", "city"):
            self.fields[field_name].required = True
        self.fields["company_name"].widget.attrs.update({"placeholder": "Muster GmbH"})
        self.fields["vat_id"].widget.attrs.update({"placeholder": "DE123456789"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.B2B
        if commit:
            user.save()
        return user


class UserManageForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("role", "is_active")
        labels = {"role": "Rolle", "is_active": "Aktiv"}
