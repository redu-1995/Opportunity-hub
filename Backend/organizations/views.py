from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, OrganizationMember
from .permissions import IsOrganizationManager
from .serializers import (
    OrganizationMemberSerializer,
    OrganizationMembershipApprovalSerializer,
    OrganizationMembershipRequestSerializer,
    OrganizationSerializer,
)


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        return Organization.objects.filter(
            verification_status=Organization.VerificationStatus.VERIFIED
        ).select_related("created_by")

    @transaction.atomic
    def perform_create(self, serializer):
        organization = serializer.save(created_by=self.request.user)
        OrganizationMember.objects.create(
            organization=organization,
            user=self.request.user,
            role=OrganizationMember.MemberRole.OWNER,
            status=OrganizationMember.MembershipStatus.PENDING,
        )


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [IsOrganizationManager]

    def get_queryset(self):
        queryset = Organization.objects.filter(
            verification_status=Organization.VerificationStatus.VERIFIED
        )

        if self.request.user.is_authenticated:
            queryset = queryset | Organization.objects.filter(
                created_by=self.request.user
            )

        return queryset.select_related("created_by")


class OrganizationMembershipRequestView(generics.CreateAPIView):
    serializer_class = OrganizationMembershipRequestSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        if organization.pk != int(self.kwargs["pk"]):
            raise ValidationError({
                "organization": ["Organization does not match the URL."]
            })

        serializer.save()


class OrganizationMembershipListView(generics.ListAPIView):
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return OrganizationMember.objects.select_related(
                "organization",
                "user",
                "reviewed_by",
            )

        managed_organizations = OrganizationMember.objects.filter(
            user=user,
            status=OrganizationMember.MembershipStatus.APPROVED,
            role__in=[
                OrganizationMember.MemberRole.OWNER,
                OrganizationMember.MemberRole.ADMIN,
            ],
        ).values_list("organization_id", flat=True)

        return OrganizationMember.objects.filter(
            Q(user=user) | Q(organization_id__in=managed_organizations)
        ).select_related(
            "organization",
            "user",
            "reviewed_by",
        ).distinct()


class OrganizationMembershipApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            membership = (
                OrganizationMember.objects
                .select_for_update()
                .select_related("organization", "user")
                .get(pk=pk)
            )
        except OrganizationMember.DoesNotExist:
            return Response(
                {"detail": "Membership request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if membership.user_id == request.user.id:
            return Response(
                {"detail": "You cannot approve your own membership request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not request.user.is_superuser:
            can_approve = OrganizationMember.objects.filter(
                organization=membership.organization,
                user=request.user,
                status=OrganizationMember.MembershipStatus.APPROVED,
                role__in=[
                    OrganizationMember.MemberRole.OWNER,
                    OrganizationMember.MemberRole.ADMIN,
                ],
            ).exists()

            if not can_approve:
                return Response(
                    {
                        "detail": (
                            "You are not authorized to approve this request."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        if membership.status != OrganizationMember.MembershipStatus.PENDING:
            return Response(
                {
                    "detail": (
                        "Only pending membership requests can be approved."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrganizationMembershipApprovalSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        reviewed_at = timezone.now()
        membership.role = serializer.validated_data["role"]
        membership.status = OrganizationMember.MembershipStatus.APPROVED
        membership.reviewed_by = request.user
        membership.reviewed_at = reviewed_at
        membership.joined_at = reviewed_at
        membership.save(
            update_fields=[
                "role",
                "status",
                "reviewed_by",
                "reviewed_at",
                "joined_at",
                "updated_at",
            ]
        )

        response_serializer = OrganizationMemberSerializer(membership)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
