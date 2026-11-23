
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

from .models import User, UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "email_verified",
        ]
        read_only_fields = [
            "id",
            "role",
            "email_verified",
        ]

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        candidate_user = User(
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )

        try:
            validate_password(
                attrs["password"],
                user=candidate_user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "password": error.messages
            })

        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=User.Role.MEMBER,
        )

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Authenticate users using email and password.
    Return JWT access and refresh tokens.
    """

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        attrs[self.username_field] = (
            attrs[self.username_field].strip().lower()
        )

        return super().validate(attrs)


class EmailTokenRefreshSerializer(TokenRefreshSerializer):
    pass


class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "phone_number",
            "date_of_birth",
            "location",
            "bio",
            "profile_picture",
        ]
        read_only_fields = ["user"]

    def validate_date_of_birth(self, value):
        if value and value >= timezone.now().date():
            raise serializers.ValidationError(
                "Date of birth must be in the past."
            )
        return value
