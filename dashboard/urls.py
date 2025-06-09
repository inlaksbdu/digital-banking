from django.urls import path
from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.staff_login, name="loginview"),
    path("verify-account/", views.verify_otp_view, name="verify-2fa-otp"),
    path("dashboard/", views.index, name="dashboard"),
    #  URLS FOR CUSTOMERS
    path("customers/", views.customers, name="customers"),
    path(
        "customers/<uuid:uuid>/detail/",
        views.customer_detail,
        name="customer-detail",
    ),
]
