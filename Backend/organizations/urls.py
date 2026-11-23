from django.urls import path

from .views import (
    OrganizationDetailView,
    OrganizationListCreateView,
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
