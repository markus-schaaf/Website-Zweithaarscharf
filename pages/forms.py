from django import forms

from .models import AppointmentRequest, ContactMessage


class HoneypotMixin(forms.Form):
    """Unsichtbares Feld gegen Spam-Bots: Menschen lassen es leer."""

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}),
    )

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Ungültige Eingabe.")
        return ""


class ContactForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "message")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "message": forms.Textarea(attrs={"rows": 6}),
        }


class AppointmentForm(HoneypotMixin, forms.ModelForm):
    consent = forms.BooleanField(
        required=True,
        error_messages={"required": "Bitte bestätigen Sie die Datenschutzhinweise."},
    )

    class Meta:
        model = AppointmentRequest
        fields = ("name", "email", "phone", "topic", "preferred_datetime", "message", "consent")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "preferred_datetime": forms.TextInput(
                attrs={"placeholder": "TT.MM.JJJJ, HH:MM", "autocomplete": "off"}
            ),
            "message": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "z. B. Wunschfarbe, Wunschlänge, Anlass oder Fragen an uns",
                }
            ),
        }


class DigitalAppointmentForm(AppointmentForm):
    class Meta(AppointmentForm.Meta):
        fields = ("name", "email", "phone", "topic", "channel", "preferred_datetime", "message", "consent")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["channel"].required = True
