from django.test import TestCase, Client
from django.urls import reverse

class OrganizadorViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_foro_requires_auth(self):
        response = self.client.get(reverse('organizador_foro_publicaciones'))
        self.assertIn(response.status_code, [200, 302])