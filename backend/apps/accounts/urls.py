"""Account and authentication routes (PRD 9.2)."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/otp/send/", views.OTPSendView.as_view(), name="otp-send"),
    path("auth/otp/verify/", views.OTPVerifyView.as_view(), name="otp-verify"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/switch-role/", views.SwitchRoleView.as_view(), name="switch-role"),
    path("me/add-profile/", views.AddProfileView.as_view(), name="add-profile"),
]
