from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class ProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="member@example.com",
            password="StrongPass-2026",
        )
        self.url = reverse("user-profile-me")
        self.access = str(RefreshToken.for_user(self.user).access_token)

    def test_unauthenticated_profile_access_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_view_and_update_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

        view = self.client.get(self.url)
        self.assertEqual(view.status_code, status.HTTP_200_OK)

        update = self.client.patch(self.url, {
            "phone_number": "+251911123456",
            "location": "Addis Ababa",
            "bio": "Building opportunity pathways.",
        }, format="json")

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data["location"], "Addis Ababa")
        self.assertEqual(update.data["phone_number"], "+251911123456")

    def test_profile_cannot_change_linked_user(self):
        other = User.objects.create_user(
            email="other@example.com",
            password="StrongPass-2026",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

        response = self.client.patch(self.url, {
            "user": str(other.id),
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["user"]), str(self.user.id))
