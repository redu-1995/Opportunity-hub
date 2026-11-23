from django.db import transaction
from django.db.models import Q

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Organization, OrganizationMember
from .permissions import IsOrganizationManager
from .serializers import OrganizationSerializer


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

# Create your views here.
