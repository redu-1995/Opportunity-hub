from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user-register")

    def test_valid_registration(self):
        response = self.client.post(self.url, {
            "email": "Member@Example.com",
            "password": "StrongPass-2026",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = User.objects.get(email="member@example.com")
        self.assertTrue(user.check_password("StrongPass-2026"))

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="member@example.com",
            password="StrongPass-2026",
        )
        response = self.client.post(self.url, {
            "email": "member@example.com",
            "password": "AnotherPass-2026",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_is_rejected(self):
        response = self.client.post(self.url, {
            "email": "member@example.com",
            "password": "password",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
