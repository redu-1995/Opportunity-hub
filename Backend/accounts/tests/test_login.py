from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User


class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user-login")
        self.user = User.objects.create_user(
            email="member@example.com",
            password="StrongPass-2026",
        )

    def test_login_normalizes_email_and_returns_tokens(self):
        response = self.client.post(self.url, {
            "email": " Member@Example.com ",
            "password": "StrongPass-2026",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_incorrect_password_is_rejected(self):
        response = self.client.post(self.url, {
            "email": "member@example.com",
            "password": "WrongPassword-2026",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
