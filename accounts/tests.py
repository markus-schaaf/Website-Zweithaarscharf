from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RoleFlagsTest(TestCase):
    def test_role_drives_staff_and_superuser(self):
        admin = User.objects.create_user(
            email="admin@example.com", password="pass12345", role=User.Role.ADMIN
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

        kunde = User.objects.create_user(email="kunde@example.com", password="pass12345")
        self.assertFalse(kunde.is_staff)
        self.assertFalse(kunde.is_superuser)

        # Manuelle Flag-Änderungen werden beim Speichern von der Rolle überschrieben
        kunde.is_staff = True
        kunde.save()
        kunde.refresh_from_db()
        self.assertFalse(kunde.is_staff)


class StaffAreaAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.b2c = User.objects.create_user(email="b2c@example.com", password="pass12345")
        cls.allpower = User.objects.create_user(
            email="power@example.com", password="pass12345", role=User.Role.ALL_POWER
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com", password="pass12345", role=User.Role.ADMIN
        )

    def test_anonymous_gets_no_access(self):
        response = self.client.get(reverse("shop_manage:product_list"))
        self.assertIn(response.status_code, (302, 403))

    def test_b2c_user_gets_no_access(self):
        self.client.force_login(self.b2c)
        response = self.client.get(reverse("shop_manage:product_list"))
        self.assertIn(response.status_code, (302, 403))

    def test_allpower_can_manage_products(self):
        self.client.force_login(self.allpower)
        response = self.client.get(reverse("shop_manage:product_list"))
        self.assertEqual(response.status_code, 200)

    def test_only_admin_manages_users(self):
        self.client.force_login(self.allpower)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.b2c)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertIn(response.status_code, (302, 403))
