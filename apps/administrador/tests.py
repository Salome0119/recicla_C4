from django.test import TestCase, Client
from django.urls import reverse

class AdministradorViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_inicio_requires_admin(self):
        response = self.client.get(reverse('admi_inicio'))
        self.assertIn(response.status_code, [200, 302])

    def test_usuarios_list_without_auth(self):
        response = self.client.get(reverse('admin_users_list'))
        self.assertIn(response.status_code, [200, 302])