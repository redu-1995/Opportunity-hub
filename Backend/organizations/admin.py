from django.contrib import admin

from .models import Organization, OrganizationMember


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization_type",
        "email",
        "location",
        "verification_status",
        "created_by",
        "created_at",
    )

    list_filter = (
        "organization_type",
        "verification_status",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "location",
        "created_by__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = ("-created_at",)


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "role",
        "status",
        "reviewed_by",
        "created_at",
    )

    list_filter = (
        "role",
        "status",
        "created_at",
    )

    search_fields = (
        "user__email",
        "organization__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)