from django.urls import path

from .views import (
    OrganizationDetailView,
    OrganizationListCreateView,
    OrganizationMembershipApprovalView,
    OrganizationMembershipListView,
    OrganizationMembershipRequestView,
)


urlpatterns = [
    path(
        "",
        OrganizationListCreateView.as_view(),
        name="organization-list-create",
    ),
    path(
        "memberships/",
        OrganizationMembershipListView.as_view(),
        name="organization-membership-list",
    ),
    path(
        "memberships/<int:pk>/approve/",
        OrganizationMembershipApprovalView.as_view(),
        name="organization-membership-approve",
    ),
    path(
        "<int:pk>/request-membership/",
        OrganizationMembershipRequestView.as_view(),
        name="organization-request-membership",
    ),
    path(
        "<int:pk>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
]
