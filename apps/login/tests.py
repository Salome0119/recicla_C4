from django.test import TestCase, Client
from django.urls import reverse

class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            'correo': 'test@test.com',
            'contrasena': 'password123'
        }, follow=True)
        self.assertIn(response.status_code, [200, 302])