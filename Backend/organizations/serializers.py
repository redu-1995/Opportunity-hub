from rest_framework import serializers

from .models import Organization, OrganizationMember


class OrganizationSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "organization_type",
            "description",
            "website",
            "email",
            "phone_number",
            "location",
            "logo",
            "verification_status",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Organization name cannot be empty."
            )
        return value

    def validate_slug(self, value):
        return value.strip().lower()


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    class Meta:
        model = OrganizationMember
        fields = [
            "id",
            "organization",
            "organization_name",
            "user",
            "user_email",
            "role",
            "status",
            "reviewed_by",
            "reviewed_at",
            "joined_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "role",
            "status",
            "reviewed_by",
            "reviewed_at",
            "joined_at",
            "created_at",
            "updated_at",
        ]


class OrganizationMembershipRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMember
        fields = ["organization"]

    def validate_organization(self, organization):
        if (
            organization.verification_status
            != Organization.VerificationStatus.VERIFIED
        ):
            raise serializers.ValidationError(
                "You can only request membership in verified organizations."
            )

        user = self.context["request"].user
        if OrganizationMember.objects.filter(
            organization=organization,
            user=user,
        ).exists():
            raise serializers.ValidationError(
                "You already have a membership record for this organization."
            )

        return organization

    def create(self, validated_data):
        return OrganizationMember.objects.create(
            organization=validated_data["organization"],
            user=self.context["request"].user,
            role=OrganizationMember.MemberRole.RECRUITER,
            status=OrganizationMember.MembershipStatus.PENDING,
        )


class OrganizationMembershipApprovalSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=OrganizationMember.MemberRole.choices,
        default=OrganizationMember.MemberRole.RECRUITER,
    )

    def validate_role(self, value):
        user = self.context["request"].user
        privileged_roles = [
            OrganizationMember.MemberRole.OWNER,
            OrganizationMember.MemberRole.ADMIN,
        ]

        if not user.is_superuser and value in privileged_roles:
            raise serializers.ValidationError(
                "Only platform administrators can assign OWNER or ADMIN roles."
            )

        return value
