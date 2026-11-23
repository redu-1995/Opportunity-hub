
from django.urls import path

from .views import (
    EmailLoginView,
    EmailTokenRefreshView,
    UserLogoutView,
    UserRegistrationView,
)


urlpatterns = [
    path(
        "register/",
        UserRegistrationView.as_view(),
        name="user-register",
    ),
    path(
        "login/",
        EmailLoginView.as_view(),
        name="user-login",
    ),
    path(
        "refresh/",
        EmailTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "logout/",
        UserLogoutView.as_view(),
        name="user-logout",
    ),
]
