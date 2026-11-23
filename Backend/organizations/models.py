from django.conf import settings
from django.db import models


class Organization(models.Model):
    class OrganizationType(models.TextChoices):
        COMPANY = "COMPANY", "Company"
        UNIVERSITY = "UNIVERSITY", "University"
        NGO = "NGO", "NGO"
        GOVERNMENT = "GOVERNMENT", "Government"
        OTHER = "OTHER", "Other"

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    organization_type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
        default=OrganizationType.OTHER,
    )
    description = models.TextField(blank=True)
    website = models.URLField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=255, blank=True)
    logo = models.URLField(max_length=500, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["verification_status"]),
            models.Index(fields=["organization_type"]),
        ]

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    class MemberRole(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        RECRUITER = "RECRUITER", "Recruiter"
        EDITOR = "EDITOR", "Editor"

    class MembershipStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=MemberRole.choices,
        default=MemberRole.RECRUITER,
    )
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_organization_memberships",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_member",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name}"
