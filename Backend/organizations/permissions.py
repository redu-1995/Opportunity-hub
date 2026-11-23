from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import OrganizationMember


class IsOrganizationManager(BasePermission):
    """Allow changes by approved organization owners, admins, or superusers."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if request.user.is_superuser:
            return True

        if not request.user.is_authenticated:
            return False

        return OrganizationMember.objects.filter(
            organization=obj,
            user=request.user,
            status=OrganizationMember.MembershipStatus.APPROVED,
            role__in=[
                OrganizationMember.MemberRole.OWNER,
                OrganizationMember.MemberRole.ADMIN,
            ],
        ).exists()
