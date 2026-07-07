from django.db import models


class ContactMessage(models.Model):
    name = models.CharField("Name", max_length=120)
    email = models.EmailField("E-Mail")
    phone = models.CharField("Telefon", max_length=50, blank=True)
    subject = models.CharField("Betreff", max_length=200, blank=True)
    message = models.TextField("Nachricht")
    created_at = models.DateTimeField("Eingegangen am", auto_now_add=True)
    is_processed = models.BooleanField("Bearbeitet", default=False)

    class Meta:
        verbose_name = "Kontaktanfrage"
        verbose_name_plural = "Kontaktanfragen"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} ({self.created_at:%d.%m.%Y %H:%M})"


class AppointmentRequest(models.Model):
    class Topic(models.TextChoices):
        MASSANFERTIGUNG = "massanfertigung", "Maßanfertigung (konfigurierbare Perücke)"
        BESTAND = "bestandsperuecke", "Perücke aus dem Bestand"
        TOUPET = "toupet", "Haarteil"
        PFLEGE = "pflege", "Pflegeberatung"
        SONSTIGES = "sonstiges", "Sonstiges"

    name = models.CharField("Name", max_length=120)
    email = models.EmailField("E-Mail")
    phone = models.CharField("Telefon", max_length=50, blank=True)
    topic = models.CharField("Art der Beratung", max_length=30, choices=Topic.choices)
    preferred_datetime = models.CharField("Wunschtermin", max_length=100)
    message = models.TextField("Nachricht", blank=True)
    consent = models.BooleanField("Datenschutz-Einwilligung", default=False)
    created_at = models.DateTimeField("Eingegangen am", auto_now_add=True)
    is_processed = models.BooleanField("Bearbeitet", default=False)

    class Meta:
        verbose_name = "Terminanfrage"
        verbose_name_plural = "Terminanfragen"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} – {self.preferred_datetime}"
