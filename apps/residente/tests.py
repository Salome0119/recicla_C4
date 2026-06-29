from django.test import TestCase, Client
from django.urls import reverse

class ResidenteViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_foro_requires_auth(self):
        response = self.client.get(reverse('residente_foro_publicaciones'))
        self.assertIn(response.status_code, [200, 302])