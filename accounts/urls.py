from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views
from dj_rest_auth.views import LoginView

app_name = "accounts"

router = DefaultRouter()

router.register("pin/set-pin", views.UpdateUserViewset, basename="pin-set-pin")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # SignUP URLS
    path(
        "signup/new-customer/validate/",
        views.SignUpNewCustomerValidationView.as_view(),
        name="signup-new-customer-validate",
    ),
    path(
        "signup/new-customer/verify/",
        views.SignUpNewCustomerVerifyView.as_view(),
        name="signup-new-customer-verify",
    ),
    path(
        "signup/new-customer/",
        views.SignUpNewCustomerView.as_view(),
        name="signup-new-customer",
    ),
    path(
        "signup/existing-customer/validate/",
        views.SignUpExistingEmailAccountValidationView.as_view(),
        name="signup-existing-customer-validate",
    ),
    path(
        "signup/existing-customer/verify/",
        views.SignUpExistingVerifyView.as_view(),
        name="signup-existing-customer-verify",
    ),
    path(
        "signup/existing-customer/",
        views.SignUpExistingCustomerView.as_view(),
        name="signup-existing-customer",
    ),
    path(
        "password/change/",
        views.PasswordChangeView.as_view(),
        name="password-change",
    ),
    path(
        "password/forgot-password/",
        views.ResetPasswordOtpView.as_view(),
        name="password-reset-otp",
    ),
    path(
        "password/verify-reset-otp/",
        views.VerifyResetPasswordOTPView.as_view(),
        name="verify-password-reset-otp",
    ),
    path("password/reset/", views.ResetPasswordView.as_view(), name="password-reset"),
    path(
        "password/check-old-password/",
        views.VerifyOldPasswrodViewset.as_view(),
        name="verify-old-password",
    ),
    path("pin/forgot-pin/", views.ForgotPINView.as_view(), name="forgot-pin"),
    path("pin/verify/", views.VerifyOldPINViewset.as_view(), name="verify"),
]

urlpatterns += router.urls
