
from django.urls import path

from .views import EmailLoginView, UserRegistrationView


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
]
