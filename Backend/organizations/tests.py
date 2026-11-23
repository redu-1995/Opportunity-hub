from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Organization, OrganizationMember


class OrganizationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="creator@example.com",
            password="StrongPass-2026",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass-2026",
        )
        self.list_url = reverse("organization-list-create")

    def test_authenticated_create_starts_pending_and_creates_owner_request(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.list_url,
            {
                "name": "Example Technology PLC",
                "slug": "example-technology-plc",
                "organization_type": "COMPANY",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["verification_status"], "PENDING")
        self.assertEqual(str(response.data["created_by"]), str(self.user.id))

        organization = Organization.objects.get(
            slug="example-technology-plc",
        )
        membership = OrganizationMember.objects.get(
            organization=organization,
            user=self.user,
        )
        self.assertEqual(membership.role, OrganizationMember.MemberRole.OWNER)
        self.assertEqual(
            membership.status,
            OrganizationMember.MembershipStatus.PENDING,
        )

    def test_unauthenticated_user_cannot_create_organization(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Example Technology PLC",
                "slug": "example-technology-plc",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_list_contains_only_verified_organizations(self):
        Organization.objects.create(
            name="Verified Organization",
            slug="verified-organization",
            verification_status=Organization.VerificationStatus.VERIFIED,
            created_by=self.user,
        )
        Organization.objects.create(
            name="Pending Organization",
            slug="pending-organization",
            created_by=self.user,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["slug"],
            "verified-organization",
        )

    def test_creator_can_retrieve_own_pending_organization(self):
        organization = Organization.objects.create(
            name="Pending Organization",
            slug="pending-organization",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("organization-detail", args=[organization.pk]),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["verification_status"], "PENDING")

    def test_other_users_cannot_retrieve_pending_organization(self):
        organization = Organization.objects.create(
            name="Pending Organization",
            slug="pending-organization",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(
            reverse("organization-detail", args=[organization.pk]),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_approved_owner_or_admin_can_update(self):
        organization = Organization.objects.create(
            name="Verified Organization",
            slug="verified-organization",
            verification_status=Organization.VerificationStatus.VERIFIED,
            created_by=self.user,
        )
        detail_url = reverse(
            "organization-detail",
            args=[organization.pk],
        )

        self.client.force_authenticate(user=self.other_user)
        denied = self.client.patch(
            detail_url,
            {"description": "Unauthorized change"},
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        OrganizationMember.objects.create(
            organization=organization,
            user=self.other_user,
            role=OrganizationMember.MemberRole.ADMIN,
            status=OrganizationMember.MembershipStatus.APPROVED,
        )
        allowed = self.client.patch(
            detail_url,
            {"description": "Approved change"},
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        organization.refresh_from_db()
        self.assertEqual(organization.description, "Approved change")

    def create_verified_organization(self, slug="verified-organization"):
        return Organization.objects.create(
            name="Verified Organization",
            slug=slug,
            verification_status=Organization.VerificationStatus.VERIFIED,
            created_by=self.user,
        )

    def test_authenticated_user_can_request_membership(self):
        organization = self.create_verified_organization()
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "organization-request-membership",
                args=[organization.pk],
            ),
            {"organization": organization.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data,
            {"organization": organization.pk},
        )
        membership = OrganizationMember.objects.get(
            organization=organization,
            user=self.other_user,
        )
        self.assertEqual(
            membership.role,
            OrganizationMember.MemberRole.RECRUITER,
        )
        self.assertEqual(
            membership.status,
            OrganizationMember.MembershipStatus.PENDING,
        )
        self.assertIsNone(membership.reviewed_by)
        self.assertIsNone(membership.reviewed_at)

    def test_membership_request_requires_authentication(self):
        organization = self.create_verified_organization()

        response = self.client.post(
            reverse(
                "organization-request-membership",
                args=[organization.pk],
            ),
            {"organization": organization.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_membership_request_rejects_unverified_organization(self):
        organization = Organization.objects.create(
            name="Pending Organization",
            slug="pending-organization",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "organization-request-membership",
                args=[organization.pk],
            ),
            {"organization": organization.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            OrganizationMember.objects.filter(
                organization=organization,
                user=self.other_user,
            ).exists()
        )

    def test_duplicate_membership_request_is_rejected(self):
        organization = self.create_verified_organization()
        OrganizationMember.objects.create(
            organization=organization,
            user=self.other_user,
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "organization-request-membership",
                args=[organization.pk],
            ),
            {"organization": organization.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requester_cannot_assign_role_or_status(self):
        organization = self.create_verified_organization()
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "organization-request-membership",
                args=[organization.pk],
            ),
            {
                "organization": organization.pk,
                "role": OrganizationMember.MemberRole.ADMIN,
                "status": OrganizationMember.MembershipStatus.APPROVED,
                "user": str(self.user.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        membership = OrganizationMember.objects.get(
            organization=organization,
            user=self.other_user,
        )
        self.assertEqual(
            membership.role,
            OrganizationMember.MemberRole.RECRUITER,
        )
        self.assertEqual(
            membership.status,
            OrganizationMember.MembershipStatus.PENDING,
        )

    def test_request_organization_must_match_url(self):
        url_organization = self.create_verified_organization(
            slug="url-organization",
        )
        body_organization = self.create_verified_organization(
            slug="body-organization",
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            reverse(
                "organization-request-membership",
                args=[url_organization.pk],
            ),
            {"organization": body_organization.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            OrganizationMember.objects.filter(
                organization=body_organization,
                user=self.other_user,
            ).exists()
        )
