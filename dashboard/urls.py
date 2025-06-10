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
    path(
        "password/<uuid:uuid>/reset-password/",
        views.customer_password_reest,
        name="customer-reset-password",
    ),
    path(
        "password/<uuid:uuid>/send-temporary/",
        views.send_temporary_password,
        name="send-temporary-password",
    ),
    path(
        "password-reset/<uuid:uuid>/",
        views.send_password_reset_link,
        name="send-password-reset-link",
    ),
    path(
        "customers/<uuid:uuid>/deactivate-account/",
        views.deactivate_customer_account,
        name="customer-account-deactivation",
    ),
    path(
        "pin-reset/<uuid:uuid>/",
        views.customer_pin_reest,
        name="customer-reset-pin",
    ),
    path(
        "pin-reset/<uuid:uuid>/send-link/",
        views.send_pin_reset_link,
        name="send-pin-reset-link",
    ),
    path(
        "customers/<uuid:uuid>/activate-account/",
        views.activate_customer_account,
        name="customer-account-activation",
    ),
    # CUSTOMER REQUESTS
    path("customer-requests/", views.customer_requests, name="customer-requests"),
    path(
        "customer-requests/bank-statements/",
        views.bank_statement,
        name="bank-statements",
    ),
    path(
        "customer-requests/bank-statements/hisotry/",
        views.bank_statement_hisotry,
        name="bank-statements-history",
    ),
    path(
        "customer-requests/bank-statements/<uuid:uuid>/detail/",
        views.bank_statement_detail,
        name="bank-statements-detail",
    ),
    # TRANSFERS
    path(
        "transactions/transfers/",
        views.transfers,
        name="transfers",
    ),
    path(
        "customer-requests/transfers/<uuid:uuid>/detail/",
        views.transfer_requests_detail,
        name="transfer-requests-detail",
    ),
    path(
        "customer-requests/transfers/history/",
        views.transfer_requests_history,
        name="transfer-requests-hisotry",
    ),
    # CHEQUE REQUESTS
    path(
        "customer-requests/cheque/",
        views.cheque_requests,
        name="cheque-requests",
    ),
    path(
        "customer-requests/cheque/<uuid:uuid>/detail/",
        views.cheque_request_detail,
        name="cheque-requests-detail",
    ),
    path(
        "customer-requests/cheque/history/",
        views.cheque_request_history,
        name="cheque-requests-history",
    ),
    # CHEQUE REQUESTS
    path(
        "customer-requests/card-services/",
        views.card_request,
        name="card-requests",
    ),
    path(
        "customer-requests/card-services/<uuid:uuid>/detail/",
        views.card_request_detail,
        name="card-requests-detail",
    ),
    path(
        "customer-requests/card-services/history/",
        views.card_request_history,
        name="card-requests-history",
    ),
    # LOAN REQUESTS
    path(
        "customer-requests/loan-requests/",
        views.loan_requests,
        name="loan-requests",
    ),
    path(
        "customer-requests/loan-requests/history/",
        views.loan_requests_history,
        name="loan-requests-history",
    ),
    path(
        "customer-requests/loan-requests/<uuid:uuid>/detail/",
        views.loan_request_detail,
        name="loan-requests-detail",
    ),
    # PAYMENT
    path("payments/", views.payments, name="payments"),
    path(
        "payments/<uuid:uuid>/detail/",
        views.payments_detail,
        name="payment-detail",
    ),
    # ONBOARDING URLS
    path(
        "onboarding/new-customer/",
        views.verify_phone_number,
        name="onboarding-verify-phone",
    ),
    path(
        "onboarding/existing-customer/",
        views.verify_email,
        name="onboarding-verify-email",
    ),
]
