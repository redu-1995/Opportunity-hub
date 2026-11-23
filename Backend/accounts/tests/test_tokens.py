from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class TokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="member@example.com",
            password="StrongPass-2026",
        )

    def test_refresh_rotates_and_blacklists_previous_token(self):
        original = str(RefreshToken.for_user(self.user))
        response = self.client.post(
            reverse("token-refresh"),
            {"refresh": original},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        reused = self.client.post(
            reverse("token-refresh"),
            {"refresh": original},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        refresh = str(RefreshToken.for_user(self.user))
        response = self.client.post(
            reverse("user-logout"),
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        reused = self.client.post(
            reverse("token-refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)
