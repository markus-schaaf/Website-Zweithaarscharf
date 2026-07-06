# Datenmigration: bestehende Konten mit alter Rolle "USER" werden zu "B2C".

from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="USER").update(role="B2C")


def backwards(apps, schema_editor):
    # Verlustbehaftet: auch nach der Umstellung registrierte B2C-Konten
    # wuerden beim Zuruecksetzen zu "USER".
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="B2C").update(role="USER")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_city_user_company_name_user_phone_user_street_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
