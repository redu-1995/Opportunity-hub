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


class OrganizationMembershipListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = User.objects.create_user(
            email="member@example.com",
            password="StrongPass-2026",
        )
        self.colleague = User.objects.create_user(
            email="colleague@example.com",
            password="StrongPass-2026",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="StrongPass-2026",
        )
        self.organization = Organization.objects.create(
            name="Organization One",
            slug="organization-one",
            created_by=self.member,
        )
        self.other_organization = Organization.objects.create(
            name="Organization Two",
            slug="organization-two",
            created_by=self.outsider,
        )
        self.url = reverse("organization-membership-list")

    def create_membership(
        self,
        organization,
        user,
        role=OrganizationMember.MemberRole.RECRUITER,
        membership_status=OrganizationMember.MembershipStatus.PENDING,
    ):
        return OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role=role,
            status=membership_status,
        )

    def test_unauthenticated_user_cannot_list_memberships(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ordinary_member_sees_only_own_memberships(self):
        own_membership = self.create_membership(
            self.organization,
            self.member,
            role=OrganizationMember.MemberRole.OWNER,
        )
        self.create_membership(self.organization, self.colleague)
        self.create_membership(self.other_organization, self.outsider)
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {own_membership.pk},
        )

    def test_approved_admin_sees_memberships_for_managed_organization(self):
        manager_membership = self.create_membership(
            self.organization,
            self.member,
            role=OrganizationMember.MemberRole.ADMIN,
            membership_status=OrganizationMember.MembershipStatus.APPROVED,
        )
        coworker_membership = self.create_membership(
            self.organization,
            self.colleague,
        )
        private_membership = self.create_membership(
            self.other_organization,
            self.outsider,
        )
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {manager_membership.pk, coworker_membership.pk},
        )
        self.assertNotIn(
            private_membership.pk,
            {item["id"] for item in response.data["results"]},
        )

    def test_superuser_sees_all_memberships(self):
        first = self.create_membership(self.organization, self.member)
        second = self.create_membership(
            self.other_organization,
            self.outsider,
        )
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass-2026",
        )
        self.client.force_authenticate(user=superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {first.pk, second.pk},
        )


class OrganizationMembershipApprovalAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="StrongPass-2026",
        )
        self.requester = User.objects.create_user(
            email="requester@example.com",
            password="StrongPass-2026",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass-2026",
        )
        self.organization = Organization.objects.create(
            name="Organization One",
            slug="organization-one",
            created_by=self.manager,
        )
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.manager,
            role=OrganizationMember.MemberRole.OWNER,
            status=OrganizationMember.MembershipStatus.APPROVED,
        )
        self.membership = OrganizationMember.objects.create(
            organization=self.organization,
            user=self.requester,
        )
        self.url = reverse(
            "organization-membership-approve",
            args=[self.membership.pk],
        )

    def test_approved_manager_can_approve_and_is_recorded(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.EDITOR},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "EDITOR")
        self.assertEqual(response.data["status"], "APPROVED")
        self.assertEqual(response.data["user_email"], self.requester.email)
        self.assertEqual(
            str(response.data["reviewed_by"]),
            str(self.manager.pk),
        )
        self.assertEqual(
            response.data["organization_name"],
            self.organization.name,
        )

        self.membership.refresh_from_db()
        self.assertEqual(self.membership.reviewed_by, self.manager)
        self.assertIsNotNone(self.membership.reviewed_at)
        self.assertIsNotNone(self.membership.joined_at)
        self.assertEqual(
            self.membership.reviewed_at,
            self.membership.joined_at,
        )

    def test_non_manager_cannot_approve(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.RECRUITER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.membership.refresh_from_db()
        self.assertEqual(
            self.membership.status,
            OrganizationMember.MembershipStatus.PENDING,
        )

    def test_user_cannot_approve_own_membership(self):
        self.client.force_authenticate(user=self.requester)

        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.RECRUITER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_assign_privileged_role(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.membership.refresh_from_db()
        self.assertEqual(
            self.membership.status,
            OrganizationMember.MembershipStatus.PENDING,
        )

    def test_superuser_can_assign_privileged_role(self):
        superuser = User.objects.create_superuser(
            email="platform-admin@example.com",
            password="StrongPass-2026",
        )
        self.client.force_authenticate(user=superuser)

        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "ADMIN")
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.reviewed_by, superuser)

    def test_approval_requires_pending_membership(self):
        self.membership.status = OrganizationMember.MembershipStatus.REJECTED
        self.membership.save(update_fields=["status"])
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.RECRUITER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_membership_returns_not_found(self):
        self.client.force_authenticate(user=self.manager)
        url = reverse("organization-membership-approve", args=[9999])

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_approval_requires_authentication(self):
        response = self.client.post(
            self.url,
            {"role": OrganizationMember.MemberRole.RECRUITER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrganizationMembershipRejectionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="StrongPass-2026",
        )
        self.requester = User.objects.create_user(
            email="requester@example.com",
            password="StrongPass-2026",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass-2026",
        )
        self.organization = Organization.objects.create(
            name="Organization One",
            slug="organization-one",
            created_by=self.manager,
        )
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.manager,
            role=OrganizationMember.MemberRole.ADMIN,
            status=OrganizationMember.MembershipStatus.APPROVED,
        )
        self.membership = OrganizationMember.objects.create(
            organization=self.organization,
            user=self.requester,
        )
        self.url = reverse(
            "organization-membership-reject",
            args=[self.membership.pk],
        )

    def test_approved_manager_can_reject_and_is_recorded(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "REJECTED")
        self.assertEqual(response.data["role"], "RECRUITER")
        self.assertEqual(response.data["user_email"], self.requester.email)
        self.assertEqual(
            str(response.data["reviewed_by"]),
            str(self.manager.pk),
        )

        self.membership.refresh_from_db()
        self.assertEqual(
            self.membership.status,
            OrganizationMember.MembershipStatus.REJECTED,
        )
        self.assertEqual(self.membership.reviewed_by, self.manager)
        self.assertIsNotNone(self.membership.reviewed_at)
        self.assertIsNone(self.membership.joined_at)

    def test_non_manager_cannot_reject(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.membership.refresh_from_db()
        self.assertEqual(
            self.membership.status,
            OrganizationMember.MembershipStatus.PENDING,
        )

    def test_user_cannot_reject_own_membership(self):
        self.client.force_authenticate(user=self.requester)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_pending_memberships_can_be_rejected(self):
        self.client.force_authenticate(user=self.manager)

        for reviewed_status in (
            OrganizationMember.MembershipStatus.APPROVED,
            OrganizationMember.MembershipStatus.REJECTED,
        ):
            with self.subTest(status=reviewed_status):
                self.membership.status = reviewed_status
                self.membership.save(update_fields=["status"])

                response = self.client.post(self.url, {}, format="json")

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_superuser_can_reject(self):
        superuser = User.objects.create_superuser(
            email="platform-admin@example.com",
            password="StrongPass-2026",
        )
        self.client.force_authenticate(user=superuser)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.reviewed_by, superuser)

    def test_missing_membership_returns_not_found(self):
        self.client.force_authenticate(user=self.manager)
        url = reverse("organization-membership-reject", args=[9999])

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rejection_requires_authentication(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
